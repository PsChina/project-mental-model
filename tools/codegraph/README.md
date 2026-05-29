# codegraph

A fresh-from-source structure-understanding engine for the project-mental-model
system. It is the **derivable structural half** of a project's mental model:
where symbols live, who calls what, what a file depends on, the architectural
spine — regenerated from current code on every run, so it **never goes stale**
(unlike hand-written skeleton/flow/map docs, which rot). The non-derivable half
(pits, business rules, constraints) lives in auto-memory; codegraph does NOT
duplicate it.

Design = the proven recipe from **Aider's RepoMap** (def/ref tag graph →
personalized PageRank → token-budgeted ranked output) + the data-model ideas from
**Sourcegraph SCIP** (flat per-file occurrences, definition/reference roles).

## Why it exists

The mental-model skill says "structure → read code / codegraph". codegraph makes
that real: instead of re-reading a whole repo every session, an AI runs one
command and gets a ranked, file:line-anchored map within a token budget.

## Install / out-of-the-box

codegraph runs **out of the box at T0** (zero dependencies, pure Python ≥3.7 +
regex) — copy the folder and it works, no install, on macOS / Linux / Windows.

The high-accuracy **T2** tier (tree-sitter ASTs) is **bundled-auto-install**: on
the first run, if no venv is present, codegraph builds a self-contained `.venv`
and installs the grammars (one-time network), then transparently re-runs under it.
You can also do it explicitly:

```sh
python3 install.py            # macOS / Linux
py     install.py             # Windows (or python install.py)
```

Or install it as a real, isolated package (it ships a `pyproject.toml`, so it is a
standalone pip-installable tool, not just loose files). The PyPI **distribution**
name is `codegraph-pmm` (plain `codegraph` was taken); the **command** stays
`codegraph`:

```sh
pipx install codegraph-pmm        # from PyPI (recommended: isolated, no collision)
pipx install "codegraph-pmm[t2]"  # + tree-sitter grammars (T2)

pipx install .                    # from a source checkout (T0)
pipx install ".[t2]"              # from source + grammars (T2)
pip  install ".[t2]"              # into the current environment
```

When pip-installed, codegraph uses the environment's packages and never self-builds
a venv. (We deliberately depend on per-language grammar wheels, not
tree-sitter-language-pack, whose v1.x downloads grammars on first use — breaking offline.)

Notes on the auto-install:
- It is **local to this tool dir** (a `.venv/`), never a global/system/Homebrew
  install. Output goes to stderr, so it never pollutes results on stdout.
- **Opt out** with `CODEGRAPH_NO_AUTOINSTALL=1` (stays on T0), or force a tier with
  `--tier t0`. `--tier t0` never triggers an install.
- If it fails (e.g. offline), codegraph **falls back to T0** and writes a marker so
  it doesn't retry every run; delete `.autoinstall-skip` (or run `install.py`) to retry.
- **Offline shops**: `python3 install.py --download` pre-fetches wheels into
  `./wheels/`; ship that folder and the auto-install (or `--offline`) uses it with
  no network. Wheels are per-platform (mac-arm64 ≠ win ≠ linux), so vendor the ones
  you need.

T0 vs T2: T2 is materially more accurate for Swift / C / C++ / TS (real ASTs).
Kotlin and Objective-C currently fall back to the regex tier even under T2 (the
available Kotlin grammar mis-parses class declarations; ObjC ships no tags query)
— this is automatic and graceful, never an error.

## Invocation (interface contract)

Canonical, cross-platform call (the form the skill should use):

```sh
python3 <skill>/tools/codegraph/cli.py <command> [args] [flags]
# Windows: python <skill>\tools\codegraph\cli.py ...
# or via the launcher: <skill>/tools/codegraph/bin/codegraph <command> ...
```

### Commands

| Command | Output |
|---|---|
| `map [path]` | ranked overview: stack, entry points, dirs by symbol density, PageRank-ranked key definitions with file:line |
| `where <symbol>` | definition site(s) `file:line [kind]` + signature + top reference sites |
| `callers <symbol>` | every reference site of the symbol, ranked |
| `deps <file>` | the file's imports / internal definer files it depends on / reverse deps |

### Flags

| Flag | Meaning |
|---|---|
| `--root DIR` | repo root (default: cwd, or inferred from a path/file arg) |
| `--tier {auto,t0,t2}` | force a tier (default `auto`: T2 if the venv exists, else T0) |
| `--budget N` | approx token budget for `map` (default 900) |
| `--json` | machine-readable JSON instead of markdown |
| `--mentioned a,b` | comma-separated identifiers to focus (personalizes the ranking) |
| `--exclude GLOB` | exclude paths (repeatable); also reads `.codegraphignore` |
| `--no-cache` / `-v` | bypass cache / verbose (tier, file counts, timing on stderr) |

### Exclusion (general, no hardcoded ecosystem dirs)

Build/dep dirs (`node_modules`, `build`, `Pods`, `.venv`, …) and binary bundles
(`*.framework`, `*.xcframework`) are skipped by default, and `.gitignore` is
honored (via `git ls-files`). For vendored **source** that is committed and not
gitignored (e.g. an embedded SDK under `Frameworks/`), add a repo-root
`.codegraphignore` (gitignore-style globs) or pass `--exclude Frameworks` — the
tool hardcodes no project-specific names.

## Properties

- **Fresh / incremental**: re-reads current code each run; a per-file cache keyed
  on (mtime, size) means only changed files are re-parsed (1600+ files in <1s warm).
- **Polyglot**: Python, Swift, Kotlin, Java, C, C++, Objective-C, JS, TS, Go, Rust.
- **Offline**: no network at runtime (only `install.py` fetches wheels once).
- **Cross-platform**: macOS / Linux / Windows (stdlib only at T0; venv layout and
  cache dir resolved per-OS).
- **Cache location**: OS cache dir (`$XDG_CACHE_HOME/codegraph` or
  `%LOCALAPPDATA%\codegraph`), not the repo — nothing written into your project.

## Limitations (honest)

- References are matched by identifier name (no full type resolution), so
  `callers` over-matches on very common names; the ranking down-weights names
  defined in >5 files to compensate.
- T0 C/C++ misses functions whose `{` is on the next line (use T2 for C-heavy repos).
- Kotlin / Objective-C use the regex tier (see Install).

## Files

`cli.py` (entry + venv self-bootstrap) · `extract.py` (T0 regex + T2 tree-sitter,
graceful per-language fallback) · `graph.py` (reference graph + pure-python
personalized PageRank) · `render.py` (budgeted markdown/JSON) · `cache.py`
(incremental cache) · `langs.py` (per-language config) · `install.py`
(cross-platform venv) · `bin/codegraph[.cmd]` (launchers).
