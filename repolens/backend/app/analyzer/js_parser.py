"""
Lightweight structural parser for JavaScript/TypeScript/JSX/TSX.

This is intentionally regex-based rather than a full Tree-sitter grammar.
It won't handle every syntactic edge case, but for the patterns that
actually show up in React + Node/Express/FastAPI-client code (import
statements, function/arrow component declarations, axios/fetch calls) it's
accurate enough to build a real dependency graph -- and it has zero native
build dependencies, which matters for a v1.

Swap-in point: replace this module's internals with a real Tree-sitter
grammar later without touching callers, since it only exposes
`parse_js_file(source, relative_path, loc) -> FileAnalysis`.
"""
from __future__ import annotations

import re

from .models import ApiRouteInfo, ClassInfo, FileAnalysis, FunctionInfo, ImportRef

# import X from 'y'; import { a, b } from "y"; import * as x from 'y'
IMPORT_RE = re.compile(
    r"""^\s*import\s+
        (?:
            (?P<default>[A-Za-z_$][\w$]*)\s*(?:,\s*)?      # default import
        )?
        (?:
            \{\s*(?P<named>[^}]*)\s*\}                       # named imports
            |
            \*\s+as\s+(?P<star>[A-Za-z_$][\w$]*)             # namespace import
        )?
        \s*from\s+
        ['"](?P<module>[^'"]+)['"]
    """,
    re.MULTILINE | re.VERBOSE,
)

# require('y')
REQUIRE_RE = re.compile(r"""require\(\s*['"](?P<module>[^'"]+)['"]\s*\)""")

# function Foo(...) {   |   export function Foo(...)  |  async function Foo(
FUNCTION_DEF_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?P<async>async\s+)?function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\(",
    re.MULTILINE,
)

# const Foo = (...) => {   |   const useFoo = async (...) =>
ARROW_FUNCTION_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?P<async>async\s+)?\(",
    re.MULTILINE,
)

# class Foo extends Bar {
CLASS_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?class\s+(?P<name>[A-Za-z_$][\w$]*)"
    r"(?:\s+extends\s+(?P<base>[A-Za-z_$][\w$.]*))?",
    re.MULTILINE,
)

# axios.get('/api/x')  |  axios.post("/api/x", ...)  |  fetch(`/api/x`)
AXIOS_CALL_RE = re.compile(
    r"""axios\.(?P<method>get|post|put|delete|patch)\(\s*[`'"](?P<path>/[^`'"]*)[`'"]""",
)
FETCH_CALL_RE = re.compile(
    r"""fetch\(\s*[`'"](?P<path>/[^`'"]*)[`'"](?:\s*,\s*\{[^}]*method\s*:\s*['"](?P<method>[A-Za-z]+)['"])?""",
    re.DOTALL,
)

JSX_RETURN_HINT_RE = re.compile(r"return\s*\(?\s*<[A-Za-z]")
REACT_IMPORT_RE = re.compile(r"""from\s+['"]react['"]""")


def _is_probably_component(name: str, source: str) -> bool:
    """Heuristic: PascalCase name + the file renders JSX somewhere."""
    if not name or not name[0].isupper():
        return False
    return bool(JSX_RETURN_HINT_RE.search(source))


def parse_js_file(source: str, relative_path: str, loc: int) -> FileAnalysis:
    language = "TypeScript" if relative_path.endswith((".ts", ".tsx")) else "JavaScript"
    result = FileAnalysis(path=relative_path, language=language, loc=loc)

    for m in IMPORT_RE.finditer(source):
        module = m.group("module")
        names = []
        if m.group("default"):
            names.append(m.group("default"))
        if m.group("named"):
            names.extend(n.strip().split(" as ")[0].strip() for n in m.group("named").split(",") if n.strip())
        if m.group("star"):
            names.append(m.group("star"))
        line = source[: m.start()].count("\n") + 1
        result.imports.append(
            ImportRef(module=module, names=names, is_relative=module.startswith("."), line=line)
        )

    for m in REQUIRE_RE.finditer(source):
        module = m.group("module")
        line = source[: m.start()].count("\n") + 1
        result.imports.append(ImportRef(module=module, is_relative=module.startswith("."), line=line))

    has_react_import = bool(REACT_IMPORT_RE.search(source)) or ".tsx" in relative_path or ".jsx" in relative_path

    for m in FUNCTION_DEF_RE.finditer(source):
        name = m.group("name")
        line = source[: m.start()].count("\n") + 1
        result.functions.append(FunctionInfo(name=name, line=line, is_async=bool(m.group("async"))))
        if has_react_import and _is_probably_component(name, source):
            result.classes.append(ClassInfo(name=name, line=line, is_react_component=True))
            result.is_react_component_file = True

    for m in ARROW_FUNCTION_RE.finditer(source):
        name = m.group("name")
        line = source[: m.start()].count("\n") + 1
        result.functions.append(FunctionInfo(name=name, line=line, is_async=bool(m.group("async"))))
        if has_react_import and _is_probably_component(name, source):
            result.classes.append(ClassInfo(name=name, line=line, is_react_component=True))
            result.is_react_component_file = True

    for m in CLASS_RE.finditer(source):
        name = m.group("name")
        base = m.group("base")
        line = source[: m.start()].count("\n") + 1
        is_component = base in {"React.Component", "Component", "PureComponent"}
        result.classes.append(
            ClassInfo(name=name, line=line, bases=[base] if base else [], is_react_component=is_component)
        )
        if is_component:
            result.is_react_component_file = True

    for m in AXIOS_CALL_RE.finditer(source):
        line = source[: m.start()].count("\n") + 1
        result.api_routes.append(
            ApiRouteInfo(method=m.group("method").upper(), path=m.group("path"), handler="(client call)", line=line)
        )
    for m in FETCH_CALL_RE.finditer(source):
        line = source[: m.start()].count("\n") + 1
        method = (m.group("method") or "GET").upper()
        result.api_routes.append(
            ApiRouteInfo(method=method, path=m.group("path"), handler="(client call)", line=line)
        )

    return result
