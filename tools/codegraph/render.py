"""Rendering: turn a built Graph into LLM-facing output, fit to a token budget.

The `map` view binary-searches how many ranked definitions to include so the
rendered text lands within ~15% of the budget (aider's trick), grouped by file
with file:line anchors and signature lines. JSON variants are exact (no budget).
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

# Manifest -> human stack label (cheap, high-signal overview).
_MANIFESTS = [
    ("Package.swift", "Swift / SwiftPM"), ("Podfile", "iOS / CocoaPods"),
    ("*.xcodeproj", "Xcode project"), ("build.gradle.kts", "Android/Kotlin / Gradle"),
    ("build.gradle", "JVM / Gradle"), ("settings.gradle.kts", "Gradle"),
    ("pyproject.toml", "Python / pyproject"), ("requirements.txt", "Python / pip"),
    ("setup.py", "Python / setuptools"), ("package.json", "Node / npm"),
    ("Cargo.toml", "Rust / Cargo"), ("go.mod", "Go modules"),
    ("CMakeLists.txt", "C/C++ / CMake"), ("Makefile", "Make"),
]

# Definition names that signal an entry point.
_ENTRY_NAMES = {"main", "App", "AppDelegate", "Application", "SceneDelegate"}
_ENTRY_RE_KIND = {"function": {"main"}}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def detect_stack(root: str) -> list[str]:
    out: list[str] = []
    try:
        entries = os.listdir(root)
    except OSError:
        entries = []
    for pat, label in _MANIFESTS:
        if pat.startswith("*"):
            if any(e.endswith(pat[1:]) for e in entries):
                out.append(label)
        elif pat in entries:
            out.append(label)
    return out


def entry_points(file_index: dict[str, dict]) -> list[tuple[str, int, str]]:
    out = []
    for rel, idx in file_index.items():
        for name, line, kind, _sig in idx.get("defs", []):
            if name in _ENTRY_NAMES or name.lower() == "main":
                out.append((rel, line, name))
    out.sort(key=lambda t: t[0])
    return out[:12]


def _lang_summary(file_index: dict[str, dict]) -> str:
    by_lang = defaultdict(lambda: [0, 0])  # lang -> [files, defs]
    for idx in file_index.values():
        by_lang[idx["lang"]][0] += 1
        by_lang[idx["lang"]][1] += len(idx.get("defs", []))
    parts = [f"{lg} {c[0]}f/{c[1]}d" for lg, c in sorted(by_lang.items(), key=lambda kv: -kv[1][0])]
    return ", ".join(parts)


def _top_dirs(file_index: dict[str, dict], limit: int = 10) -> list[tuple[str, int, int]]:
    agg = defaultdict(lambda: [0, 0])
    for rel, idx in file_index.items():
        d = os.path.dirname(rel) or "."
        agg[d][0] += 1
        agg[d][1] += len(idx.get("defs", []))
    rows = [(d, c[0], c[1]) for d, c in agg.items()]
    rows.sort(key=lambda t: (-t[2], -t[1]))
    return rows[:limit]


def _render_defs(ranked, file_index, k) -> str:
    """Group the top-k ranked definitions by file (file order = first appearance)."""
    by_file: "dict[str, list]" = defaultdict(list)
    order: list[str] = []
    for _score, rel, ident in ranked[:k]:
        if rel not in by_file:
            order.append(rel)
        by_file[rel].append(ident)
    # map ident -> (line, kind, sig) for lookup
    lines = []
    for rel in order:
        idx = file_index.get(rel, {})
        defmap = {name: (ln, kind, sig) for name, ln, kind, sig in idx.get("defs", [])}
        lines.append(f"\n{rel}")
        seen = set()
        for ident in by_file[rel]:
            if ident in seen:
                continue
            seen.add(ident)
            info = defmap.get(ident)
            if info:
                ln, kind, sig = info
                lines.append(f"  L{ln} {kind} {ident} — {sig}" if sig and sig != ident else f"  L{ln} {kind} {ident}")
            else:
                lines.append(f"  {ident}")
    return "\n".join(lines)


def budget_fit(ranked, file_index, budget_tokens: int) -> str:
    n = len(ranked)
    if n == 0:
        return "(no definitions extracted)"
    lo, hi = 0, n
    best = ""
    guess = min(max(budget_tokens // 25, 1), n)
    while lo <= hi:
        text = _render_defs(ranked, file_index, guess)
        tok = estimate_tokens(text)
        err = abs(tok - budget_tokens) / max(budget_tokens, 1)
        if tok <= budget_tokens and len(text) > len(best):
            best = text
        if err < 0.15:
            best = best or text
            break
        if tok < budget_tokens:
            lo = guess + 1
        else:
            hi = guess - 1
        if lo > hi:
            break
        guess = (lo + hi) // 2
    return best or _render_defs(ranked, file_index, min(guess or 1, n))


# ---- top-level views -------------------------------------------------------

def render_map(project, root, tier, graph, budget) -> str:
    fi = graph.files
    stack = detect_stack(root)
    eps = entry_points(fi)
    dirs = _top_dirs(fi)
    ranked = graph.ranked_definitions()
    head = [
        f"# codegraph · {project}  ({tier}, fresh from source)",
        f"stack: {', '.join(stack) if stack else 'n/a'}",
        f"files: {len(fi)}  ·  langs: {_lang_summary(fi)}",
    ]
    if eps:
        head.append("entry points: " + ", ".join(f"{r}:{ln}({n})" for r, ln, n in eps))
    out = ["\n".join(head)]
    out.append("\n## structure (dirs by symbol density)")
    out.append("\n".join(f"- {d}/ — {f}f, {de}d" for d, f, de in dirs))
    out.append(f"\n## key definitions (PageRank-ranked, ~{budget} tok)")
    out.append(budget_fit(ranked, fi, budget))
    return "\n".join(out).strip() + "\n"


def render_where(symbol, graph, budget) -> str:
    sites = graph.where(symbol)
    if not sites:
        return f"# codegraph where {symbol}\n(no definition found)\n"
    out = [f"# codegraph where {symbol}  ({len(sites)} definition(s))"]
    for rel, line, kind, sig in sites:
        out.append(f"\n{rel}:{line}  [{kind}]\n  {sig}")
    callers = graph.callers(symbol)
    if callers:
        out.append(f"\n## referenced by ({len(callers)} site(s), top 15)")
        out.append("\n".join(f"  {r}:{ln}" for r, ln in callers[:15]))
    return "\n".join(out).strip() + "\n"


def render_callers(symbol, graph) -> str:
    sites = graph.callers(symbol)
    defs = graph.where(symbol)
    out = [f"# codegraph callers {symbol}  ({len(sites)} reference site(s))"]
    if defs:
        out.append("defined at: " + ", ".join(f"{r}:{ln}" for r, ln, _k, _s in defs))
    out.append("")
    out.append("\n".join(f"  {r}:{ln}" for r, ln in sites[:60]) or "  (none)")
    return "\n".join(out).strip() + "\n"


def render_deps(rel, graph) -> str:
    resolved, cand = graph.resolve_file(rel)
    if resolved is None:
        if cand:
            return f"# codegraph deps {rel}\nambiguous — candidates:\n" + "\n".join("  " + c for c in cand) + "\n"
        return f"# codegraph deps {rel}\n(file not in index)\n"
    rel = resolved
    d = graph.deps(rel)
    out = [f"# codegraph deps {rel}"]
    out.append("\n## imports (external)")
    out.append("\n".join(f"  {m}" for m in d["external"][:40]) or "  (none)")
    out.append("\n## depends on (internal definers)")
    out.append("\n".join(f"  {f}  <-- {', '.join(ids[:8])}" for f, ids in list(d["internal"].items())[:30]) or "  (none)")
    out.append("\n## depended on by (reverse)")
    out.append("\n".join(f"  {f}  <-- {', '.join(ids[:8])}" for f, ids in list(d["rdeps"].items())[:30]) or "  (none)")
    return "\n".join(out).strip() + "\n"


# ---- json ------------------------------------------------------------------

def as_json(kind, project, root, tier, graph, arg=None, budget=400) -> str:
    fi = graph.files
    if kind == "map":
        ranked = graph.ranked_definitions()
        payload = {
            "project": project, "tier": tier, "stack": detect_stack(root),
            "files": len(fi), "entry_points": [
                {"file": r, "line": ln, "name": n} for r, ln, n in entry_points(fi)],
            "definitions": [
                {"file": r, "ident": i, "score": round(s, 6)} for s, r, i in ranked[:budget]],
        }
    elif kind == "where":
        payload = {"symbol": arg, "definitions": [
            {"file": r, "line": ln, "kind": k, "sig": s} for r, ln, k, s in graph.where(arg)],
            "callers": [{"file": r, "line": ln} for r, ln in graph.callers(arg)[:50]]}
    elif kind == "callers":
        payload = {"symbol": arg, "callers": [
            {"file": r, "line": ln} for r, ln in graph.callers(arg)]}
    elif kind == "deps":
        resolved, cand = graph.resolve_file(arg)
        if resolved is None:
            payload = {"file": arg, "ambiguous": cand} if cand else {"file": arg, "found": False}
        else:
            payload = {"file": resolved, **graph.deps(resolved)}
    else:
        payload = {}
    return json.dumps(payload, ensure_ascii=False, indent=2)
