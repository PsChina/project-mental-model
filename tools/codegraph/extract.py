"""Extraction layer: walk a repo and turn each source file into a compact index
of definitions, references and imports.

Two interchangeable extractors behind one interface:
  - RegexExtractor  (T0): zero dependency. Regex defs + tokenized refs. Always works.
  - TreeSitterExtractor (T2): AST-accurate defs/refs via tree-sitter tag queries,
    used automatically when the `tree_sitter` venv is present. Falls back to the
    regex path per-language when a grammar/query is missing (hybrid, never worse).

Output per file (cached by cache.TagCache):
    {"lang": str,
     "defs":  [[name, line, kind, sig], ...],
     "refs":  {name: [line, ...]},          # capped; filtered to defs at graph time
     "imports": [module, ...]}
"""
from __future__ import annotations

import fnmatch
import os
import subprocess
from collections import defaultdict

from langs import (IDENT_RE, IGNORE_DIRS, LANGS, MAX_FILE_BYTES, lang_for,
                   stopwords)

MAX_REFS_PER_FILE = 800      # distinct identifiers kept per file
MAX_LINES_PER_REF = 6        # source lines recorded per identifier (for callers)


def _load_ignore(root: str) -> list[str]:
    """Read a repo-root .codegraphignore (gitignore-ish globs, '#' comments). The
    general, project-configurable escape hatch for excluding vendored source that
    isn't .gitignore'd — instead of hardcoding ecosystem dir names in the tool."""
    pats: list[str] = []
    try:
        with open(os.path.join(root, ".codegraphignore"), encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    pats.append(ln.rstrip("/"))
    except OSError:
        pass
    return pats


def _matches_glob(rel: str, globs: list[str]) -> bool:
    if not globs:
        return False
    for g in globs:
        if fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(rel, g + "/*") or fnmatch.fnmatch(rel, "*/" + g + "/*"):
            return True
        # bare dir/prefix match (e.g. "Frameworks" excludes Frameworks/**)
        if rel == g or rel.startswith(g + "/") or ("/" + g + "/") in ("/" + rel):
            return True
    return False

# Directory suffixes for committed-but-vendored bundles (Apple frameworks, asset
# catalogs) that would otherwise drown app code with third-party headers.
_VENDOR_SUFFIXES = (".framework", ".xcframework", ".bundle", ".lproj",
                    ".app", ".xcassets", ".appiconset", ".dSYM")


def _vendored(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    for p in parts:
        if p in IGNORE_DIRS or p.startswith("."):
            return True
        if p.endswith(_VENDOR_SUFFIXES):
            return True
    return False


def _git_files(root: str) -> list[str] | None:
    """Tracked + untracked-but-not-ignored files (honors .gitignore). None if not a
    git repo / git unavailable."""
    if not os.path.exists(os.path.join(root, ".git")):  # dir, or file in worktrees
        return None
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", "--cached", "--others",
             "--exclude-standard", "-z"],
            capture_output=True, timeout=30, check=True).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def walk(root: str, exclude: list[str] | None = None):
    """Yield (abspath, relpath, lang) for indexable source files under root.
    Prefers `git ls-files` (respects .gitignore), skips vendored bundles and any
    glob in .codegraphignore / `exclude`, so SDK headers don't dominate the map."""
    root = os.path.abspath(root)
    globs = _load_ignore(root) + list(exclude or [])
    rels = _git_files(root)
    if rels is not None:
        for rel in rels:                       # git already yields '/'-separated
            lang = lang_for(rel)
            if not lang or _vendored(rel) or _matches_glob(rel, globs):
                continue
            ap = os.path.join(root, rel)
            try:
                if not os.path.isfile(ap) or os.path.getsize(ap) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield ap, rel, lang
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in IGNORE_DIRS and not d.startswith(".")
                       and not d.endswith(_VENDOR_SUFFIXES)]
        for fn in filenames:
            lang = lang_for(fn)
            if not lang:
                continue
            ap = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(ap) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            # normalize to '/' so keys/output match the git path on every OS
            rel = os.path.relpath(ap, root).replace(os.sep, "/")
            if _matches_glob(rel, globs):
                continue
            yield ap, rel, lang


def _read(ap: str) -> tuple[str, bytes] | None:
    try:
        with open(ap, "rb") as f:
            raw = f.read()
    except OSError:
        return None
    return raw.decode("utf-8", errors="replace"), raw


def _imports(lang: str, lines: list[str]) -> list[str]:
    out: list[str] = []
    pats = LANGS[lang].imports
    for line in lines[:400]:  # imports live near the top
        for p in pats:
            m = p.search(line)
            if m:
                tok = next((g for g in m.groups() if g), None)
                if tok:
                    out.append(tok)
    return out


def _tokenize_refs(lines: list[str], lang: str) -> dict[str, list[int]]:
    """References = identifier occurrences (filtered to the global definition set at
    graph-build time). Comment lines are skipped; capped per file. Used by BOTH
    tiers: tree-sitter's @reference captures are call-only (they miss type
    annotations, base classes, imports), so the tokenizer — which empirically tracks
    ground truth — is the reference source in every tier. T2 contributes accurate
    DEFINITIONS, the tokenizer contributes complete REFERENCES."""
    stop = stopwords(lang)
    comment_marks = LANGS[lang].line_comment
    refs: dict[str, list[int]] = defaultdict(list)
    for i, line in enumerate(lines, 1):
        s = line.lstrip()
        if any(s.startswith(c) for c in comment_marks):  # skip comment lines
            continue
        for tok in IDENT_RE.findall(line):
            if tok in stop:
                continue
            if tok not in refs and len(refs) >= MAX_REFS_PER_FILE:
                continue  # at cap: stop adding new idents, keep filling known ones
            bucket = refs[tok]
            if len(bucket) < MAX_LINES_PER_REF:
                bucket.append(i)
    return dict(refs)


# ---- T0: regex + tokenize --------------------------------------------------

class RegexExtractor:
    tier = "t0"

    def scan(self, ap: str, rel: str, lang: str) -> dict:
        rd = _read(ap)
        if rd is None:
            return {"lang": lang, "defs": [], "refs": {}, "imports": []}
        text, _ = rd
        lines = text.split("\n")
        cfg = LANGS[lang]
        comment_marks = cfg.line_comment

        defs: list[list] = []
        seen_def: set[tuple[str, int]] = set()
        for i, line in enumerate(lines, 1):
            if any(line.lstrip().startswith(c) for c in comment_marks):
                continue
            for pat, kind in cfg.defs:
                m = pat.search(line)
                if m and m.group(1):
                    name = m.group(1)
                    if (name, i) not in seen_def:
                        seen_def.add((name, i))
                        defs.append([name, i, kind, line.strip()[:160]])

        return {"lang": lang, "defs": defs, "refs": _tokenize_refs(lines, lang),
                "imports": _imports(lang, lines)}


# ---- T2: tree-sitter tag queries -------------------------------------------

class TreeSitterExtractor:
    tier = "t2"

    def __init__(self, queries_dir: str):
        self.queries_dir = queries_dir
        self._fallback = RegexExtractor()
        self._cache: dict[str, object] = {}   # lang -> (parser, query) | None

    def _load(self, lang: str):
        if lang in self._cache:
            return self._cache[lang]
        result = None
        try:
            result = self._build(lang)
        except Exception:
            result = None
        self._cache[lang] = result
        return result

    def _build(self, lang: str):
        from tree_sitter import Language, Parser, Query  # noqa
        cfg = LANGS[lang]
        if not cfg.ts_module:
            return None
        mod = __import__(cfg.ts_module)
        # typescript module exposes two grammars; pick by language name.
        if cfg.ts_module == "tree_sitter_typescript":
            lang_obj = Language(mod.language_typescript())
        else:
            lang_obj = Language(mod.language())
        scm = self._query_text(lang, cfg)
        if not scm:
            return None
        parser = Parser(lang_obj)
        query = Query(lang_obj, scm)
        return (parser, query, lang_obj)

    def _query_text(self, lang: str, cfg) -> str | None:
        # 1) our vendored query (we own these, fills grammar gaps like Kotlin/ObjC)
        for fname in ([cfg.ts_tags_file] if cfg.ts_tags_file else []) + [f"{lang}-tags.scm"]:
            p = os.path.join(self.queries_dir, fname)
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as fh:
                        return fh.read()
                except OSError:
                    pass
        # 2) the grammar wheel's bundled tags.scm, if any
        try:
            mod = __import__(cfg.ts_module)
            base = os.path.dirname(mod.__file__)
            cand = os.path.join(base, "queries", "tags.scm")
            if os.path.exists(cand):
                with open(cand, encoding="utf-8") as fh:
                    return fh.read()
        except Exception:
            pass
        return None

    def scan(self, ap: str, rel: str, lang: str) -> dict:
        built = self._load(lang)
        if built is None:
            return self._fallback.scan(ap, rel, lang)  # hybrid: regex for this lang
        rd = _read(ap)
        if rd is None:
            return {"lang": lang, "defs": [], "refs": {}, "imports": []}
        text, raw = rd
        lines = text.split("\n")
        parser, query, _ = built
        try:
            tree = parser.parse(raw)
            matches = list(self._matches(query, tree.root_node))
        except Exception:
            return self._fallback.scan(ap, rel, lang)

        # tree-sitter contributes accurate DEFINITIONS only. Tags conventions vary:
        # bundled/nvim grammars put @name on the identifier + @definition.<kind> on
        # the enclosing node; aider puts everything on @name.definition.<kind>. We
        # do NOT read @reference here — those are call-only and miss type/import
        # refs; references come from the tokenizer (complete, matches ground truth).
        defs: list[list] = []
        seen: set[tuple[str, int]] = set()
        for caps in matches:
            is_def = False
            kind = None
            name_node = None
            for cname, nodes in caps.items():
                if not nodes:
                    continue
                if cname == "name":
                    name_node = name_node or nodes[0]
                elif cname.startswith("name.definition."):
                    is_def, kind = True, cname.rsplit(".", 1)[-1]
                    name_node = name_node or nodes[0]
                elif cname.startswith("definition."):
                    is_def, kind = True, cname.rsplit(".", 1)[-1]
            if not is_def or name_node is None:
                continue
            name = self._text(name_node, raw)
            if not name:
                continue
            row = name_node.start_point[0]
            if (name, row) in seen:
                continue
            seen.add((name, row))
            sig = lines[row].strip()[:160] if row < len(lines) else name
            defs.append([name, row + 1, kind or "def", sig])

        return {"lang": lang, "defs": defs, "refs": _tokenize_refs(lines, lang),
                "imports": _imports(lang, lines)}

    @staticmethod
    def _matches(query, root):
        """Yield per-match capture dicts {capture_name: [Node]}, across tree-sitter
        API versions (0.25 QueryCursor.matches -> [(idx, dict)]; older variants)."""
        try:
            from tree_sitter import QueryCursor
            res = QueryCursor(query).matches(root)
        except Exception:
            res = query.matches(root)
        for item in res:
            caps = item[1] if isinstance(item, tuple) and len(item) == 2 else item
            if isinstance(caps, dict):
                yield caps
            elif isinstance(caps, list):  # very old API: [(name, node), ...]
                d = defaultdict(list)
                for nm, nd in caps:
                    d[nm].append(nd)
                yield d

    @staticmethod
    def _text(node, raw: bytes) -> str:
        try:
            return raw[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        except Exception:
            return ""


# ---- selection -------------------------------------------------------------

def get_extractor(force_tier: str | None, queries_dir: str):
    """Return (extractor, tier). T2 if tree_sitter importable (venv present) unless
    force_tier=='t0'. Never raises — degrades to T0."""
    if force_tier == "t0":
        return RegexExtractor(), "t0"
    if force_tier in (None, "t2", "auto"):
        try:
            import tree_sitter  # noqa: F401
            return TreeSitterExtractor(queries_dir), "t2"
        except Exception:
            if force_tier == "t2":
                # explicitly requested but unavailable: caller may warn
                return RegexExtractor(), "t0-fallback"
    return RegexExtractor(), "t0"
