#!/usr/bin/env python3
"""Cross-platform installer for codegraph's T2 (tree-sitter) tier.

    python3 install.py              create .venv + install tree-sitter grammars
    python3 install.py --force      recreate the venv from scratch
    python3 install.py --download   pip-download wheels into ./wheels (for offline reuse)
    python3 install.py --offline    install from ./wheels with no network

Runs on macOS / Linux / Windows (uses the stdlib `venv` module and the correct
per-OS venv layout). T2 is optional: without it codegraph still runs the T0
(regex) tier. Installing nothing breaks — failures per grammar are tolerated.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(HERE, ".venv")
WHEELS = os.path.join(HERE, "wheels")

CORE = ["tree-sitter>=0.23"]
# (pip package, python module) — installed best-effort; missing wheels are skipped.
GRAMMARS = [
    ("tree-sitter-python", "tree_sitter_python"),
    ("tree-sitter-javascript", "tree_sitter_javascript"),
    ("tree-sitter-typescript", "tree_sitter_typescript"),
    ("tree-sitter-c", "tree_sitter_c"),
    ("tree-sitter-cpp", "tree_sitter_cpp"),
    ("tree-sitter-java", "tree_sitter_java"),
    ("tree-sitter-go", "tree_sitter_go"),
    ("tree-sitter-rust", "tree_sitter_rust"),
    ("tree-sitter-swift", "tree_sitter_swift"),
    ("tree-sitter-kotlin", "tree_sitter_kotlin"),
    ("tree-sitter-objc", "tree_sitter_objc"),
]


def venv_python(vdir: str) -> str:
    if os.name == "nt":
        return os.path.join(vdir, "Scripts", "python.exe")
    return os.path.join(vdir, "bin", "python")


def run(cmd: list[str]) -> int:
    print("  $", " ".join(cmd))
    return subprocess.run(cmd).returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="recreate the venv")
    ap.add_argument("--download", action="store_true", help="download wheels into ./wheels")
    ap.add_argument("--offline", action="store_true", help="install from ./wheels, no network")
    args = ap.parse_args(argv)

    pkgs = CORE + [p for p, _ in GRAMMARS]

    if args.download:
        os.makedirs(WHEELS, exist_ok=True)
        # download into ./wheels using the *current* interpreter's pip
        rc = run([sys.executable, "-m", "pip", "download", "-d", WHEELS, *pkgs])
        print("downloaded wheels -> ./wheels" if rc == 0 else "download had errors (some grammars may lack wheels)")
        return 0

    if args.force and os.path.isdir(VENV):
        import shutil
        shutil.rmtree(VENV, ignore_errors=True)

    vpy = venv_python(VENV)
    if not os.path.isfile(vpy):
        print(f"creating venv at {VENV} ...")
        venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
    if not os.path.isfile(vpy):
        print("ERROR: venv creation failed", file=sys.stderr)
        return 1

    run([vpy, "-m", "pip", "install", "--upgrade", "pip", "-q"])

    base_install = [vpy, "-m", "pip", "install", "-q"]
    if args.offline:
        base_install += ["--no-index", "--find-links", WHEELS]

    # core first (grammars need a compatible tree-sitter ABI)
    if run(base_install + CORE) != 0:
        print("ERROR: failed to install tree-sitter core", file=sys.stderr)
        return 1
    # grammars best-effort: one missing wheel must not abort the rest
    for pkg, _mod in GRAMMARS:
        if run(base_install + [pkg]) != 0:
            print(f"  (skipped {pkg} — no wheel for this platform/python)")

    # verify which grammars actually load under the venv interpreter
    verify = (
        "import importlib, sys\n"
        "mods = %r\n"
        "ok=[]; bad=[]\n"
        "import tree_sitter\n"
        "from tree_sitter import Language\n"
        "for pip_name, mod in mods:\n"
        "    try:\n"
        "        m = importlib.import_module(mod)\n"
        "        fn = getattr(m,'language_typescript',None) or getattr(m,'language')\n"
        "        Language(fn()); ok.append(mod)\n"
        "    except Exception as e:\n"
        "        bad.append((mod, str(e)[:60]))\n"
        "print('OK  :', ', '.join(sorted(ok)) or '(none)')\n"
        "print('MISS:', ', '.join(m for m,_ in bad) or '(none)')\n"
        % GRAMMARS
    )
    print("\nverifying grammars under venv:")
    subprocess.run([vpy, "-c", verify])
    print(f"\ndone. codegraph will auto-use this venv (T2). venv python: {vpy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
