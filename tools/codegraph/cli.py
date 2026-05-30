"""codegraph CLI — fresh, ranked, budgeted structural map of a codebase.

  codegraph map [path]          ranked overview (stack, entry points, HTTP routes, key defs)
  codegraph where <symbol>      definition site(s) + top callers
  codegraph callers <symbol>    all reference sites, ranked
  codegraph deps <file>         imports / internal definers / reverse deps
  codegraph impact <file>...    files downstream of a change + affected tests to re-run

Global flags: --root DIR  --tier {auto,t0,t2}  --budget N  --json  --mentioned a,b

It re-reads current code every run (incremental via mtime cache), so output never
goes stale — that is the whole point versus a hand-written skeleton doc.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

# resolve sibling modules whether run as a loose file (copy-and-go) or installed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _find_venv_python(here: str) -> str | None:
    for rel in (("bin", "python3"), ("bin", "python"), ("Scripts", "python.exe")):
        cand = os.path.join(here, ".venv", *rel)
        if os.path.isfile(cand):
            return cand
    return None


def _argv_tier() -> str | None:
    for i, a in enumerate(sys.argv):
        if a == "--tier" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith("--tier="):
            return a.split("=", 1)[1]
    return None


def _autoinstall(here: str) -> str | None:
    """First-run bundled install of the tree-sitter venv (T2). Local to the tool
    dir — NOT a global/system install. Opt-out via CODEGRAPH_NO_AUTOINSTALL=1;
    skipped (no retry) after a prior failure marker; all output to stderr so it
    never pollutes the result on stdout. Returns the venv python, or None on T0."""
    if os.environ.get("CODEGRAPH_NO_AUTOINSTALL"):
        return None
    if _argv_tier() == "t0":               # explicit T0 must never trigger install
        return None
    if "site-packages" in here or "dist-packages" in here:
        return None  # installed via pip: deps come from the env, never self-install
    skip = os.path.join(here, ".autoinstall-skip")
    if os.path.exists(skip):
        return None
    install_py = os.path.join(here, "install.py")
    if not os.path.isfile(install_py):
        return None
    import subprocess
    print("codegraph: first run — building tree-sitter venv (one-time; "
          "set CODEGRAPH_NO_AUTOINSTALL=1 to skip)...", file=sys.stderr)
    cmd = [sys.executable, install_py]
    if os.path.isdir(os.path.join(here, "wheels")):
        cmd.append("--offline")            # use vendored wheels if shipped
    try:
        subprocess.run(cmd, stdout=sys.stderr, stderr=sys.stderr, timeout=900)
    except Exception:
        pass
    vpy = _find_venv_python(here)
    if not vpy:
        try:
            open(skip, "w").close()        # don't retry every run after a failure
        except OSError:
            pass
        print("codegraph: T2 setup unavailable (offline?) — using T0 (regex). "
              "Run install.py later for full accuracy.", file=sys.stderr)
    return vpy


def _maybe_reexec_into_venv() -> None:
    """Cross-platform: if the current interpreter lacks tree_sitter, re-run under a
    sibling .venv (building it on first run if needed), so `python cli.py` upgrades
    T0->T2 on any OS. No venv / install opted-out or failed -> run as-is (T0).
    subprocess (not execv) for Windows reliability; guarded against re-entry."""
    if os.environ.get("CODEGRAPH_BOOTSTRAPPED"):
        return
    try:
        import tree_sitter  # noqa: F401
        return
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    vpy = _find_venv_python(here) or _autoinstall(here)
    if vpy and os.path.abspath(vpy) != os.path.abspath(sys.executable):
        import subprocess
        env = dict(os.environ, CODEGRAPH_BOOTSTRAPPED="1")
        try:
            r = subprocess.run([vpy, os.path.abspath(__file__), *sys.argv[1:]], env=env)
            sys.exit(r.returncode)
        except OSError:
            return  # venv python unusable -> fall through to T0
    return


_maybe_reexec_into_venv()

import render  # noqa: E402
from cache import TagCache  # noqa: E402
from extract import get_extractor, walk  # noqa: E402


def _build_index(root, tier, use_cache, verbose, exclude=None):
    queries_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queries")
    extractor, real_tier = get_extractor(tier, queries_dir)
    cache = TagCache(root, extractor.tier) if use_cache else None
    file_index, scanned, cached = {}, 0, 0
    try:
        for ap, rel, lang in walk(root, exclude=exclude):
            try:
                st = os.stat(ap)
                mtime, size = st.st_mtime_ns, st.st_size
            except OSError:
                continue
            idx = cache.get(ap, mtime, size) if cache else None
            if idx is None:
                idx = extractor.scan(ap, rel, lang)
                if cache:
                    cache.put(ap, mtime, size, idx)
                scanned += 1
            else:
                cached += 1
            file_index[rel] = idx
    finally:
        if cache:
            cache.close()  # guaranteed flush even if a scan raises
    if verbose:
        print(f"[codegraph] tier={real_tier} files={len(file_index)} "
              f"parsed={scanned} cached={cached}", file=sys.stderr)
    if real_tier == "t0-fallback":
        print("[codegraph] WARN: tier t2 requested but tree_sitter unavailable; "
              "ran T0 (regex). Run install.sh to enable T2.", file=sys.stderr)
    return file_index, real_tier


def main(argv=None) -> int:
    # shared flags usable either before OR after the subcommand
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=None, help="repo root (default: cwd or path arg)")
    common.add_argument("--tier", choices=["auto", "t0", "t2"], default="auto")
    common.add_argument("--budget", type=int, default=900, help="approx token budget for `map`")
    common.add_argument("--json", action="store_true")
    common.add_argument("--mentioned", default="", help="comma-separated idents to focus ranking")
    common.add_argument("--no-cache", action="store_true")
    common.add_argument("--exclude", action="append", default=[],
                        help="glob to exclude (repeatable); also reads .codegraphignore")
    common.add_argument("-v", "--verbose", action="store_true")

    ap = argparse.ArgumentParser(prog="codegraph", description=__doc__, parents=[common],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_map = sub.add_parser("map", parents=[common]); p_map.add_argument("path", nargs="?", default=None)
    p_where = sub.add_parser("where", parents=[common]); p_where.add_argument("symbol")
    p_callers = sub.add_parser("callers", parents=[common]); p_callers.add_argument("symbol")
    p_deps = sub.add_parser("deps", parents=[common]); p_deps.add_argument("file")
    p_impact = sub.add_parser("impact", parents=[common]); p_impact.add_argument("files", nargs="+")
    args = ap.parse_args(argv)

    # emit UTF-8 regardless of console codepage (Windows cp1252 would otherwise
    # crash on non-ASCII identifiers / the arrow glyph). 3.7+; best-effort.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    # resolve root
    root = args.root
    if root is None and args.cmd == "map" and args.path:
        root = args.path if os.path.isdir(args.path) else os.path.dirname(args.path) or "."
    if root is None and args.cmd in ("deps", "impact"):
        first = args.file if args.cmd == "deps" else (args.files[0] if args.files else None)
        if first and os.path.isfile(first):
            root = os.path.dirname(os.path.abspath(first))
            # climb to a sensible repo root (where a manifest or .git lives)
            root = _repo_root(root) or root
    root = os.path.abspath(root or os.getcwd())
    if not os.path.isdir(root):
        print(f"codegraph: not a directory: {root}", file=sys.stderr)
        return 2

    project = os.path.basename(os.path.normpath(root)) or root
    mentioned = {m.strip() for m in args.mentioned.split(",") if m.strip()}
    if args.cmd in ("where", "callers"):
        mentioned.add(args.symbol)

    t0 = time.time()
    file_index, real_tier = _build_index(root, args.tier, not args.no_cache, args.verbose, args.exclude)
    if not file_index:
        print(f"codegraph: no source files found under {root}", file=sys.stderr)
        return 1

    from graph import Graph
    g = Graph.build(file_index, mentioned=mentioned)

    if args.cmd == "map":
        out = (render.as_json("map", project, root, real_tier, g, budget=args.budget)
               if args.json else render.render_map(project, root, real_tier, g, args.budget))
    elif args.cmd == "where":
        out = (render.as_json("where", project, root, real_tier, g, arg=args.symbol)
               if args.json else render.render_where(args.symbol, g, args.budget))
    elif args.cmd == "callers":
        out = (render.as_json("callers", project, root, real_tier, g, arg=args.symbol)
               if args.json else render.render_callers(args.symbol, g))
    elif args.cmd == "deps":
        rel = (os.path.relpath(os.path.abspath(args.file), root).replace(os.sep, "/")
               if os.path.exists(args.file) else args.file.replace(os.sep, "/"))
        out = (render.as_json("deps", project, root, real_tier, g, arg=rel)
               if args.json else render.render_deps(rel, g))
    elif args.cmd == "impact":
        rels = [(os.path.relpath(os.path.abspath(f), root).replace(os.sep, "/")
                 if os.path.exists(f) else f.replace(os.sep, "/")) for f in args.files]
        out = (render.as_json("impact", project, root, real_tier, g, arg=rels)
               if args.json else render.render_impact(rels, g))
    else:
        out = ""

    sys.stdout.write(out)
    if not out.endswith("\n"):
        sys.stdout.write("\n")
    if args.verbose:
        print(f"[codegraph] {time.time() - t0:.2f}s", file=sys.stderr)
    return 0


def _repo_root(start: str) -> str | None:
    cur = os.path.abspath(start)
    markers = {".git", "Package.swift", "package.json", "pyproject.toml",
               "build.gradle", "build.gradle.kts", "Cargo.toml", "go.mod", "CMakeLists.txt"}
    while True:
        try:
            if markers & set(os.listdir(cur)):
                return cur
        except OSError:
            return None
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


if __name__ == "__main__":
    raise SystemExit(main())
