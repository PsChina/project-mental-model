"""Reference graph + ranking — the Aider RepoMap recipe, reimplemented offline.

  nodes  = files
  edge   = (file that REFERENCES ident) -> (file that DEFINES ident),
           weighted by ident-multiplier * sqrt(ref_count)
  rank   = personalized PageRank over that graph (pure python, no networkx)
  output = per (file, ident) definition score, by distributing each file's rank
           across its outgoing reference edges.

The ident multipliers (mention x10, long-structured-name x10, _private x0.1,
defined-in-many-files x0.1) come straight from aider/repomap.py and are what make
the architectural spine — symbols many files depend on — float to the top.
"""
from __future__ import annotations

import math
import os
import re
from collections import defaultdict, deque

# "structured" = snake_case, camelCase, OR PascalCase (incl. single PascalCase words
# like "Database" — those previously missed the camelCase test and were under-ranked).
_STRUCTURED = re.compile(r"_|[a-z][A-Z]|[A-Z][a-z]")

# Test-file heuristic (cross-language). Path: a `test/tests/__tests__/spec/specs`
# segment. Filename: conventional markers that need a real boundary (underscore or
# PascalCase T/S) so plain words like "latest.go" / "contest.py" don't false-match.
_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|specs?)(/|$)", re.I)
_TEST_FILE = re.compile(
    r"^test_"                        # test_foo.py
    r"|_test\.[A-Za-z]+$"            # foo_test.go, foo_test.py
    r"|Tests?\.[A-Za-z]+$"           # FooTests.swift, FooTest.kt
    r"|\.(test|spec)\.[A-Za-z]+$"    # foo.test.ts, foo.spec.ts
    r"|Spec\.[A-Za-z]+$"             # FooSpec.kt
)


def _is_test_file(rel: str) -> bool:
    return bool(_TEST_PATH.search(rel) or _TEST_FILE.search(os.path.basename(rel)))


def _ident_mul(ident: str, n_definer_files: int, mentioned: set[str]) -> float:
    mul = 1.0
    if ident in mentioned:
        mul *= 10.0
    if len(ident) >= 8 and _STRUCTURED.search(ident):
        mul *= 10.0
    if ident.startswith("_"):
        mul *= 0.1
    if n_definer_files > 5:   # ubiquitous names (init/main/toString) are noise
        mul *= 0.1
    return mul


class Graph:
    """Holds the built reference structure and answers the four CLI views."""

    def __init__(self):
        self.files: dict[str, dict] = {}                 # rel -> file index
        self.defines: dict[str, set[str]] = defaultdict(set)   # ident -> {definer rel}
        # detailed reference edges: (referrer, definer, ident, count)
        self.edges: list[tuple[str, str, str, int]] = []
        self.rank: dict[str, float] = {}

    # ---- build -------------------------------------------------------------

    @classmethod
    def build(cls, file_index: dict[str, dict], mentioned: set[str] | None = None) -> "Graph":
        g = cls()
        g.files = file_index
        mentioned = mentioned or set()

        for rel, idx in file_index.items():
            for name, *_ in idx.get("defs", []):
                g.defines[name].add(rel)

        # weighted, collapsed file->file adjacency for PageRank
        adj: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        nodes = set(file_index.keys())

        for rel, idx in file_index.items():
            for ident, lines in idx.get("refs", {}).items():
                definers = g.defines.get(ident)
                if not definers:
                    continue
                count = len(lines) if isinstance(lines, list) else int(lines)
                mul = _ident_mul(ident, len(definers), mentioned)
                w = mul * math.sqrt(max(count, 1))
                for definer in definers:
                    if definer == rel:
                        continue
                    adj[rel][definer] += w
                    g.edges.append((rel, definer, ident, count))

        # defined-but-never-referenced: tiny self-edge so it can still surface
        for ident, definers in g.defines.items():
            referenced = any(ident in idx.get("refs", {}) for idx in file_index.values())
            if not referenced:
                for d in definers:
                    adj[d][d] += 0.1

        pers = None
        if mentioned:
            pers = {}
            base = 100.0 / max(len(nodes), 1)
            for rel, idx in file_index.items():
                hit = any(name in mentioned for name, *_ in idx.get("defs", []))
                # also personalize files whose path matches a mentioned token
                if hit or any(m.lower() in rel.lower() for m in mentioned):
                    pers[rel] = base
        g.rank = pagerank(nodes, adj, personalization=pers)
        # freeze to plain dicts: out-of-range access becomes a loud KeyError instead
        # of a defaultdict phantom 0.0, and removes mutation side-effects.
        g._adj = {src: dict(dsts) for src, dsts in adj.items()}
        return g

    def resolve_file(self, rel: str):
        """Map a file arg to an indexed path. Returns (resolved|None, candidates).
        Shared by the markdown and JSON `deps` views so both handle ambiguity."""
        if rel in self.files:
            return rel, []
        cand = [f for f in self.files
                if f.endswith(rel) or os.path.basename(f) == os.path.basename(rel)]
        if len(cand) == 1:
            return cand[0], []
        return None, cand

    # ---- ranked definition list (for `map`) --------------------------------

    def ranked_definitions(self) -> list[tuple[float, str, str]]:
        """Return [(score, definer_rel, ident)] sorted desc — the most depended-upon
        definitions first. Each file's rank flows along its outgoing file-edges in
        proportion to edge weight, then splits evenly across the idents on that edge."""
        out_total = {src: sum(dsts.values()) for src, dsts in self._adj.items()}
        scores: dict[tuple[str, str], float] = defaultdict(float)
        for (src, dst, ident, _count) in self.edges:
            tot = out_total.get(src, 0.0) or 1.0
            edge_rank = self.rank.get(src, 0.0) * (self._adj[src][dst] / tot)
            scores[(dst, ident)] += edge_rank / max(self._edge_ident_count(src, dst), 1)
        # baseline coverage: every definition gets at least a file-rank-scaled score,
        # so files with sparse/no reference edges (decompiled code, ref-less grammars,
        # leaf modules) still surface — ranked below the edge-ranked spine.
        for ident, definers in self.defines.items():
            for d in definers:
                if (d, ident) not in scores:
                    scores[(d, ident)] = self.rank.get(d, 0.0) * 1e-3
        ranked = [(sc, dst, ident) for (dst, ident), sc in scores.items()]
        ranked.sort(key=lambda t: (-t[0], t[1], t[2]))
        return ranked

    def _edge_ident_count(self, src: str, dst: str) -> int:
        if not hasattr(self, "_eic"):
            eic: dict[tuple[str, str], int] = defaultdict(int)
            for (s, d, _i, _c) in self.edges:
                eic[(s, d)] += 1
            self._eic = eic
        return self._eic[(src, dst)]

    def ranked_files(self) -> list[tuple[float, str]]:
        return sorted(((r, f) for f, r in self.rank.items()), key=lambda t: (-t[0], t[1]))

    # ---- views -------------------------------------------------------------

    def where(self, symbol: str) -> list[tuple[str, int, str, str]]:
        """Definition sites of `symbol`: [(rel, line, kind, sig)]."""
        out = []
        for rel in sorted(self.defines.get(symbol, ()), key=lambda r: -self.rank.get(r, 0.0)):
            for name, line, kind, sig in self.files[rel].get("defs", []):
                if name == symbol:
                    out.append((rel, line, kind, sig))
        return out

    def callers(self, symbol: str) -> list[tuple[str, int]]:
        """Reference sites of `symbol` (excluding its own definition files), ranked."""
        out: list[tuple[str, int]] = []
        definers = self.defines.get(symbol, set())
        for rel, idx in self.files.items():
            lines = idx.get("refs", {}).get(symbol)
            if not lines:
                continue
            if rel in definers and len(definers) == 1:
                continue
            for ln in (lines if isinstance(lines, list) else [0]):
                out.append((rel, ln))
        out.sort(key=lambda t: (-self.rank.get(t[0], 0.0), t[0], t[1]))
        return out

    def deps(self, rel: str) -> dict:
        """For a file: internal definer files it depends on, external imports, and
        reverse deps (files that reference symbols this file defines)."""
        idx = self.files.get(rel, {})
        internal: dict[str, set[str]] = defaultdict(set)   # definer file -> idents
        external = list(dict.fromkeys(idx.get("imports", [])))
        for ident in idx.get("refs", {}):
            for definer in self.defines.get(ident, ()):
                if definer != rel:
                    internal[definer].add(ident)
        my_defs = {name for name, *_ in idx.get("defs", [])}
        rdeps: dict[str, set[str]] = defaultdict(set)
        for other, oidx in self.files.items():
            if other == rel:
                continue
            for ident in oidx.get("refs", {}):
                if ident in my_defs:
                    rdeps[other].add(ident)
        return {
            "internal": {k: sorted(v) for k, v in sorted(
                internal.items(), key=lambda kv: -self.rank.get(kv[0], 0.0))},
            "external": external,
            "rdeps": {k: sorted(v) for k, v in sorted(
                rdeps.items(), key=lambda kv: -self.rank.get(kv[0], 0.0))},
        }

    def impact(self, changed: list[str]) -> dict:
        """What could break if `changed` files change: reverse-edge BFS over the
        reference graph (X depends on Y when X references a symbol Y defines), plus
        the test files among the blast radius to re-run.

        Propagation is through SYMBOLS defined in the changed files — a file with no
        defs has no downstream symbol dependents. Test detection is heuristic
        (`_is_test_file`). `changed` are file args, resolved leniently like `deps`."""
        seeds: list[str] = []
        unresolved: list[tuple[str, list[str]]] = []
        for c in changed:
            r, cand = self.resolve_file(c)
            seeds.append(r) if r else unresolved.append((c, cand))
        seed_set = set(seeds)

        # Cut name-match noise so impact isn't "everything": references are matched by
        # name (no type resolution), so an edge through a ubiquitous name (__init__,
        # build, run — defined in >5 files, same threshold as _ident_mul) or a name the
        # referrer ALSO defines itself (local shadowing) almost never means a real
        # cross-file dependency on the changed file. Both are dropped from propagation.
        n_def = {ident: len(d) for ident, d in self.defines.items()}
        own = {rel: {nm for nm, *_ in idx.get("defs", [])} for rel, idx in self.files.items()}
        rev: dict[str, set[str]] = defaultdict(set)     # definer file -> referrer files
        direct_idents: dict[str, set[str]] = defaultdict(set)  # referrer -> seed idents used
        for (referrer, definer, ident, _count) in self.edges:
            if n_def.get(ident, 0) > 5 or ident in own.get(referrer, ()):
                continue
            rev[definer].add(referrer)
            if definer in seed_set and referrer not in seed_set:
                direct_idents[referrer].add(ident)

        depth = {s: 0 for s in seeds}
        q = deque(seeds)
        while q:
            cur = q.popleft()
            for dep in rev.get(cur, ()):
                if dep not in depth:
                    depth[dep] = depth[cur] + 1
                    q.append(dep)

        affected = [f for f in depth if f not in seed_set]
        direct = sorted((f for f in affected if depth[f] == 1),
                        key=lambda f: (-self.rank.get(f, 0.0), f))
        transitive = sorted(((f, depth[f]) for f in affected if depth[f] >= 2),
                            key=lambda t: (t[1], -self.rank.get(t[0], 0.0), t[0]))
        tests = sorted((f for f in depth if _is_test_file(f)),
                       key=lambda f: (depth[f], -self.rank.get(f, 0.0), f))
        return {
            "changed": seeds,
            "unresolved": unresolved,
            "direct": {f: sorted(direct_idents[f]) for f in direct},
            "transitive": transitive,
            "tests": tests,
        }


# ---- personalized PageRank (pure python) -----------------------------------

def pagerank(nodes, adj, personalization=None, damping=0.85, max_iter=100, tol=1.0e-6):
    """Weighted personalized PageRank. `adj` is dict[src] -> dict[dst] -> weight.
    Dangling mass is redistributed by the personalization vector (matching aider's
    `dangling=pers`), so rank doesn't leak into a uniform sink."""
    nodes = list(nodes)
    n = len(nodes)
    if n == 0:
        return {}
    if personalization:
        s = sum(personalization.values()) or 1.0
        p = {nd: personalization.get(nd, 0.0) / s for nd in nodes}
    else:
        p = {nd: 1.0 / n for nd in nodes}
    rank = {nd: 1.0 / n for nd in nodes}
    out_sum = {src: sum(d.values()) for src, d in adj.items()}
    dangling = [nd for nd in nodes if out_sum.get(nd, 0.0) <= 0.0]

    for _ in range(max_iter):
        prev = rank
        dangling_mass = damping * sum(prev[nd] for nd in dangling)
        rank = {nd: (1.0 - damping) * p[nd] + dangling_mass * p[nd] for nd in nodes}
        for src, dsts in adj.items():
            tot = out_sum.get(src, 0.0)
            if tot <= 0.0:
                continue
            f = damping * prev[src] / tot
            for dst, w in dsts.items():
                rank[dst] += f * w
        if sum(abs(rank[nd] - prev[nd]) for nd in nodes) < tol * n:
            break
    return rank
