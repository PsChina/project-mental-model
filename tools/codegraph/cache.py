"""Per-file tag cache, keyed on (mtime, size), so re-runs only re-parse changed
files — essential for the 'always fresh, never stale, fast on a 1668-file repo'
goal. Stored in a sqlite DB per project root under ~/.claude/.cache/codegraph/.

A schema version is embedded so changing the extractor invalidates the cache.
Any sqlite failure degrades silently to a no-op cache (correctness over speed).
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3

SCHEMA = 6  # bump when extractor output shape changes


def _cache_dir() -> str:
    """OS-standard per-user cache dir, decoupled from any install location so
    codegraph is portable. Windows: %LOCALAPPDATA%; else XDG_CACHE_HOME / ~/.cache."""
    home = os.path.expanduser("~")
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
        return os.path.join(base, "codegraph", "cache")
    xdg = os.environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache")
    return os.path.join(xdg, "codegraph")


def _cache_path(root: str) -> str:
    base = _cache_dir()
    os.makedirs(base, exist_ok=True)
    digest = hashlib.sha1(os.path.abspath(root).encode("utf-8")).hexdigest()[:16]
    return os.path.join(base, f"{digest}.db")


class TagCache:
    """Maps abspath -> file index dict, validated by (mtime_ns, size). `tier`
    namespaces entries so the T0 and T2 extractors never read each other's data."""

    def __init__(self, root: str, tier: str):
        self.tier = tier
        self.conn: sqlite3.Connection | None = None
        try:
            self.conn = sqlite3.connect(_cache_path(root))
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS tags ("
                "path TEXT, tier TEXT, schema INT, mtime INT, size INT, data TEXT, "
                "PRIMARY KEY(path, tier))"
            )
            self.conn.commit()
        except sqlite3.Error:
            if self.conn is not None:
                try:
                    self.conn.close()
                except sqlite3.Error:
                    pass
            self.conn = None

    def get(self, path: str, mtime: int, size: int) -> dict | None:
        if not self.conn:
            return None
        try:
            row = self.conn.execute(
                "SELECT mtime, size, schema, data FROM tags WHERE path=? AND tier=?",
                (path, self.tier),
            ).fetchone()
        except sqlite3.Error:
            return None
        if not row or row[0] != mtime or row[1] != size or row[2] != SCHEMA:
            return None
        try:
            return json.loads(row[3])
        except (ValueError, TypeError):
            return None

    def put(self, path: str, mtime: int, size: int, data: dict) -> None:
        if not self.conn:
            return
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO tags(path, tier, schema, mtime, size, data) "
                "VALUES (?,?,?,?,?,?)",
                (path, self.tier, SCHEMA, mtime, size, json.dumps(data)),
            )
        except sqlite3.Error:
            pass

    def commit(self) -> None:
        if self.conn:
            try:
                self.conn.commit()
            except sqlite3.Error:
                pass

    def close(self) -> None:
        if self.conn:
            try:
                self.conn.commit()
                self.conn.close()
            except sqlite3.Error:
                pass
            self.conn = None
