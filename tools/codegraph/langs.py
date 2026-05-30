"""Per-language configuration for codegraph.

Two layers per language:
  - T0 (zero-dep): regex patterns to extract definitions + import edges, run by
    the RegexExtractor. References are derived by tokenizing and intersecting with
    the global definition set (see extract.py / graph.py).
  - T2 (tree-sitter): the tree-sitter grammar module name + the tags query (from the
    grammar's bundled queries/tags.scm, or a vendored queries/<lang>-tags.scm if one
    is dropped in). Kotlin and Objective-C have no usable tags query (the Kotlin
    grammar also mis-parses class declarations), so they run the regex tier even
    under T2 — handled by the graceful per-language fallback in extract.py.

The design deliberately keeps definitions heuristic-but-cheap. Precision for the
LLM map comes from the PageRank ranking surfacing the architectural spine, not from
perfect parsing — see render.py / graph.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Directories we never descend into (build output / vendored deps / VCS).
IGNORE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "Pods", "Carthage", ".build",
    "build", "dist", "out", "target", "bin", "obj", ".venv", "venv", "env",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".tox", ".gradle", ".idea",
    "DerivedData", "vendor", "third_party", "thirdparty", "external", ".next",
    ".cache", "coverage", ".dart_tool", ".terraform",
}

MAX_FILE_BYTES = 1_200_000  # skip files larger than ~1.2MB (generated/minified)


@dataclass
class Lang:
    name: str
    exts: tuple[str, ...]
    # (compiled regex, symbol-kind) — group(1) must capture the defined name.
    defs: list[tuple[re.Pattern, str]] = field(default_factory=list)
    # import/include edges — group(1) captures the imported module/path token.
    imports: list[re.Pattern] = field(default_factory=list)
    # tree-sitter grammar module (e.g. "tree_sitter_python"); None if unsupported.
    ts_module: str | None = None
    # name of a vendored queries/<file>; None => use the grammar's bundled tags.scm.
    ts_tags_file: str | None = None
    # line-comment prefixes, to skip def matches inside comments.
    line_comment: tuple[str, ...] = ("//",)
    # HTTP route patterns (decorator/method-call frameworks): each is
    # (regex, method: group-index|literal, path: group-index). See extract._routes.
    routes: list = field(default_factory=list)


def _c(*patterns: str) -> list[re.Pattern]:
    return [re.compile(p) for p in patterns]


def _defs(*pairs: tuple[str, str]) -> list[tuple[re.Pattern, str]]:
    return [(re.compile(p), k) for p, k in pairs]


def _routes_spec(*triples) -> list:
    return [(re.compile(p), m, g) for p, m, g in triples]


# Express (method-call, path must start with "/") + NestJS (decorator) — shared by
# both .js and .ts. The leading-"/" guard keeps `.get(`/`.post(` from matching
# unrelated calls like `map.get("key")` / `cache.post`.
_JS_ROUTES = (
    (r"""^\s*@(Get|Post|Put|Patch|Delete|All)\s*\(\s*['"]?([^'")]*)""", 1, 2),
    (r"""\b[\w$.]+\.(get|post|put|patch|delete|all)\s*\(\s*['"](/[^'"]*)""", 1, 2),
)


# ---- language table --------------------------------------------------------

LANGS: dict[str, Lang] = {
    "python": Lang(
        "python", (".py", ".pyi"),
        defs=_defs(
            (r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)", "function"),
            (r"^\s*class\s+([A-Za-z_]\w*)", "class"),
        ),
        imports=_c(r"^\s*(?:from\s+([.\w]+)\s+import|import\s+([.\w]+))"),
        ts_module="tree_sitter_python",
        line_comment=("#",),
        routes=_routes_spec(
            # FastAPI / APIRouter / Flask verb decorators: @app.get("/path")
            (r"""^\s*@\s*[\w.]+\.(get|post|put|patch|delete|head|options|websocket)\s*\(\s*['"]([^'"]*)""", 1, 2),
            # Flask @app.route("/path"[, methods=...]) — verb unknown -> ANY
            (r"""^\s*@\s*[\w.]+\.route\s*\(\s*['"]([^'"]*)""", "ANY", 1),
        ),
    ),
    "swift": Lang(
        "swift", (".swift",),
        defs=_defs(
            (r"\bfunc\s+([A-Za-z_]\w*)", "function"),
            (r"\b(?:class|struct|enum|protocol|actor)\s+([A-Za-z_]\w*)", "type"),
            (r"\bextension\s+([A-Za-z_][\w.]*)", "extension"),
        ),
        imports=_c(r"^\s*import\s+([A-Za-z_]\w*)"),
        ts_module="tree_sitter_swift",
    ),
    "kotlin": Lang(
        "kotlin", (".kt", ".kts"),
        defs=_defs(
            # skip an optional extension receiver: `fun Foo.bar(` -> bar, not Foo
            (r"\bfun\s+(?:<[^>]*>\s*)?(?:[A-Za-z_][\w.]*\.)?([A-Za-z_]\w*)\s*\(", "function"),
            (r"\b(?:class|interface|object|enum\s+class)\s+([A-Za-z_]\w*)", "type"),
        ),
        imports=_c(r"^\s*import\s+([\w.]+)"),
        ts_module="tree_sitter_kotlin",
        ts_tags_file="kotlin-tags.scm",
        routes=_routes_spec(  # Spring MVC mapping annotations (Kotlin)
            (r"""@(Get|Post|Put|Patch|Delete|Request)Mapping\s*\(\s*(?:value\s*=\s*)?['"]([^'"]+)""", 1, 2),
        ),
    ),
    "java": Lang(
        "java", (".java",),
        defs=_defs(
            (r"\b(?:class|interface|enum|record)\s+([A-Za-z_]\w*)", "type"),
            (r"\b(?:public|private|protected|static|final|\s)+[\w<>\[\].,\s]+\s+([A-Za-z_]\w*)\s*\([^)]*\)\s*(?:throws[\w,\s]*)?\{", "method"),
        ),
        imports=_c(r"^\s*import\s+(?:static\s+)?([\w.]+)"),
        ts_module="tree_sitter_java",
        routes=_routes_spec(  # Spring MVC mapping annotations
            (r"""@(Get|Post|Put|Patch|Delete|Request)Mapping\s*\(\s*(?:value\s*=\s*)?['"]([^'"]+)""", 1, 2),
        ),
    ),
    "c": Lang(
        "c", (".c", ".h"),
        defs=_defs(
            (r"^[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*\([^;{]*\)\s*\{", "function"),
            (r"\b(?:struct|enum|union)\s+([A-Za-z_]\w*)", "type"),
            (r"\btypedef\b[^;]*?\b([A-Za-z_]\w*)\s*;", "typedef"),
            (r"^\s*#\s*define\s+([A-Za-z_]\w*)", "macro"),
        ),
        imports=_c(r'^\s*#\s*include\s+[<"]([^>"]+)[>"]'),
        ts_module="tree_sitter_c",
    ),
    "cpp": Lang(
        "cpp", (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"),
        defs=_defs(
            (r"\b(?:class|struct|enum\s+class|enum|union)\s+([A-Za-z_]\w*)", "type"),
            (r"^[A-Za-z_][\w\s\*:&<>,]*?\b([A-Za-z_]\w*)\s*\([^;{]*\)\s*(?:const|noexcept|override|final|\s)*\{", "function"),
            (r"^\s*#\s*define\s+([A-Za-z_]\w*)", "macro"),
        ),
        imports=_c(r'^\s*#\s*include\s+[<"]([^>"]+)[>"]'),
        ts_module="tree_sitter_cpp",
    ),
    "objc": Lang(
        "objc", (".m", ".mm"),
        defs=_defs(
            (r"^\s*[-+]\s*\([^)]*\)\s*([A-Za-z_]\w*)", "method"),
            (r"^\s*@(?:interface|implementation|protocol)\s+([A-Za-z_]\w*)", "type"),
        ),
        imports=_c(r'^\s*#\s*(?:include|import)\s+[<"]([^>"]+)[>"]'),
        ts_module="tree_sitter_objc",
        ts_tags_file="objc-tags.scm",
    ),
    "javascript": Lang(
        "javascript", (".js", ".jsx", ".mjs", ".cjs"),
        defs=_defs(
            (r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)", "function"),
            (r"\bclass\s+([A-Za-z_$][\w$]*)", "class"),
            (r"\b(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)", "function"),
        ),
        imports=_c(r"""^\s*import\b[^'"]*['"]([^'"]+)['"]""", r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)"""),
        ts_module="tree_sitter_javascript",
        routes=_routes_spec(*_JS_ROUTES),
    ),
    "typescript": Lang(
        "typescript", (".ts", ".tsx", ".mts", ".cts"),
        defs=_defs(
            (r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)", "function"),
            (r"\b(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"\b(?:export\s+)?(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)", "type"),
            (r"\b(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function|\([^)]*\)(?:\s*:[^=]+)?\s*=>|[A-Za-z_$][\w$]*\s*=>)", "function"),
        ),
        imports=_c(r"""^\s*import\b[^'"]*['"]([^'"]+)['"]""", r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)"""),
        ts_module="tree_sitter_typescript",  # parser name is "typescript"/"tsx"; see extract.py
        routes=_routes_spec(*_JS_ROUTES),
    ),
    "go": Lang(
        "go", (".go",),
        defs=_defs(
            (r"\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)", "function"),
            (r"\btype\s+([A-Za-z_]\w*)\s+(?:struct|interface)", "type"),
        ),
        imports=_c(r'^\s*(?:import\s+)?(?:[\w.]+\s+)?"([^"]+)"'),
        ts_module="tree_sitter_go",
    ),
    "rust": Lang(
        "rust", (".rs",),
        defs=_defs(
            (r"\bfn\s+([A-Za-z_]\w*)", "function"),
            (r"\b(?:struct|enum|trait|union)\s+([A-Za-z_]\w*)", "type"),
            (r"\bmacro_rules!\s+([A-Za-z_]\w*)", "macro"),
        ),
        imports=_c(r"\buse\s+([\w:]+)"),
        ts_module="tree_sitter_rust",
    ),
}

# ext -> lang-name index.
_EXT_INDEX: dict[str, str] = {}
for _ln, _lc in LANGS.items():
    for _e in _lc.exts:
        # .h is claimed by C, but appears in ObjC/C++ too; first writer wins, the
        # extractor disambiguates .h by content if needed.
        _EXT_INDEX.setdefault(_e, _ln)


def lang_for(path: str) -> str | None:
    import os
    ext = os.path.splitext(path)[1].lower()
    return _EXT_INDEX.get(ext)


# Identifier token (used by T0 reference extraction). 3+ chars to cut noise.
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")

# Per-language keyword stoplist for T0 reference tokenizing (cuts the bulk of noise).
KEYWORDS: dict[str, frozenset[str]] = {
    "python": frozenset("def class return import from async await self None True False and not for while with try except finally lambda yield global nonlocal pass raise elif else assert print len str int float list dict set tuple bool type range".split()),
    "swift": frozenset("func var let class struct enum protocol extension actor return guard else for while switch case default import public private internal fileprivate open final static weak self init deinit override some any throws async await nil true false where defer".split()),
    "kotlin": frozenset("fun val var class object interface enum return when for while import public private internal protected open final override companion data sealed suspend null true false this super lateinit init constructor".split()),
    "java": frozenset("public private protected class interface enum return import package void int long float double boolean char byte short final static abstract new this super extends implements throws try catch finally for while switch case null true false instanceof synchronized volatile".split()),
    "c": frozenset("int char void float double long short unsigned signed struct enum union typedef return for while switch case default break continue sizeof const static extern include define ifdef ifndef endif else elif if goto NULL true false".split()),
    "cpp": frozenset("int char void float double long short unsigned signed bool struct enum union class template typename namespace using return for while switch case break continue sizeof const constexpr static extern public private protected virtual override final new delete this nullptr true false auto include define".split()),
    "objc": frozenset("interface implementation protocol property synthesize end import include void int return self super nil YES NO BOOL NSString NSInteger id instancetype nonatomic strong weak copy assign readonly readwrite".split()),
    "javascript": frozenset("function class return import export from const let var async await this new typeof instanceof for while switch case default break continue null undefined true false void delete yield require module exports".split()),
    "typescript": frozenset("function class interface type enum return import export from const let var async await this new typeof instanceof for while switch case default break continue null undefined true false void delete yield public private protected readonly namespace declare as keyof".split()),
    "go": frozenset("func package import return for range switch case default break continue var const type struct interface map chan go defer nil true false make new len cap append".split()),
    "rust": frozenset("fn let mut struct enum trait impl pub use mod return for while loop match if else where async await self Self crate super const static unsafe ref move dyn Some None Ok Err true false".split()),
}
_COMMON_STOP = frozenset("the and for not get set add new init main run test value name data list item index count result error".split())


def stopwords(lang: str) -> frozenset[str]:
    return KEYWORDS.get(lang, frozenset()) | _COMMON_STOP
