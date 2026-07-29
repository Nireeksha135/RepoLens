"""
Extracts imports, functions, classes, and API routes from a Python file
using the standard library `ast` module -- no guessing, no regex.

Detects FastAPI / Flask-style routes via decorators like:
    @app.get("/users/{id}")
    @router.post("/login")
"""
from __future__ import annotations

import ast

from .models import ApiRouteInfo, ClassInfo, FileAnalysis, FunctionInfo, ImportRef

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

DB_MODEL_BASE_HINTS = {"Model", "Base", "BaseModel", "db.Model", "SQLModel"}


def _decorator_name(dec: ast.expr) -> str:
    """Best-effort string form of a decorator expression, e.g. 'app.get' or 'staticmethod'."""
    if isinstance(dec, ast.Call):
        dec = dec.func
    parts = []
    node = dec
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _route_from_decorator(dec: ast.expr) -> tuple[str, str] | None:
    """If dec is like @app.get("/path") or @router.post('/path'), return (METHOD, path)."""
    if not isinstance(dec, ast.Call):
        return None
    name = _decorator_name(dec)
    method = name.split(".")[-1].lower()
    if method not in HTTP_METHODS:
        return None
    for arg in dec.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return method.upper(), arg.value
    return None


def _base_name(base: ast.expr) -> str:
    if isinstance(base, ast.Attribute):
        return f"{_base_name(base.value)}.{base.attr}"
    if isinstance(base, ast.Name):
        return base.id
    return ast.dump(base)


def parse_python_file(source: str, relative_path: str, loc: int) -> FileAnalysis:
    result = FileAnalysis(path=relative_path, language="Python", loc=loc)

    try:
        tree = ast.parse(source, filename=relative_path)
    except SyntaxError as e:
        result.parse_error = f"SyntaxError: {e}"
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.imports.append(ImportRef(module=alias.name, line=node.lineno))

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            is_relative = node.level > 0
            prefix = "." * node.level
            result.imports.append(
                ImportRef(
                    module=f"{prefix}{module}",
                    names=[a.name for a in node.names],
                    is_relative=is_relative,
                    line=node.lineno,
                )
            )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [_decorator_name(d) for d in node.decorator_list]
            result.functions.append(
                FunctionInfo(
                    name=node.name,
                    line=node.lineno,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    decorators=decorators,
                )
            )
            for dec in node.decorator_list:
                route = _route_from_decorator(dec)
                if route:
                    method, path = route
                    result.api_routes.append(
                        ApiRouteInfo(method=method, path=path, handler=node.name, line=node.lineno)
                    )

        elif isinstance(node, ast.ClassDef):
            bases = [_base_name(b) for b in node.bases]
            is_model = any(
                hint in b for b in bases for hint in DB_MODEL_BASE_HINTS
            )
            result.classes.append(ClassInfo(name=node.name, line=node.lineno, bases=bases))
            if is_model:
                result.is_db_model_file = True

    return result
