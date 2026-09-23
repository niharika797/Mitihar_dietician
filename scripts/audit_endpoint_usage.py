"""
Cross-reference every FastAPI route against every path literal in the clients.

Why this exists
---------------
A grep-based pass over this repo flagged four live endpoints as dead. Three of
those were missed for one reason: the pattern tried to match the *call
expression* -- `.post(` and the path string on the same line:

    apiClient
      .post<{
        dish_name: string;
        ...
      }>('/doctor/recipes/estimate', { dish_name: dishName })

The path sits seven lines below `.post(`, so a single-line regex sees nothing
and reports the endpoint unused. Widening that regex to span lines only moves
the goalposts -- the next formatter change breaks it again.

The fix is to stop matching calls entirely. A path literal is a path literal
regardless of which call it belongs to, how many lines that call spans, or
whether it is in a call at all (it might be a bare `const`). So: extract every
string literal from the client sources, keep the ones shaped like API paths,
and set-compare against a route table parsed from the FastAPI decorators.

Known blind spots (printed at the end of every run, deliberately -- a scan that
hides its gaps is how the original false positives happened):
  * paths assembled at runtime by concatenation, e.g. BASE + '/x'
  * paths held entirely in variables with no literal anywhere

Because of those, UNREFERENCED means "look at this", never "safe to delete".

Usage:
    python -m scripts.audit_endpoint_usage
    python -m scripts.audit_endpoint_usage --json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ROUTER_DIR = REPO / "app" / "routers"
MAIN_PY = REPO / "app" / "main.py"

# Everything that might reference a backend path. Frontends, tests, dev scripts,
# and docs all count as inbound references for this audit.
CLIENT_ROOTS = [
    REPO / "mitihar-frontend" / "apps" / "src",
    REPO / "mitihar-patient-app",
    REPO / "tests",
    REPO / "tools",
    REPO / "scripts",
    REPO / "docs",
]
CLIENT_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".py", ".md"}
SKIP_DIRS = {"node_modules", "venv", ".git", "__pycache__", "archive", ".expo", "dist", "build"}

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

# A route carrying this marker is driven by something outside the repo (Cloud
# Scheduler, a webhook provider). Absence of an in-repo caller is expected and
# must not read as dead.
EXTERNAL_MARKER = "dead-code-scan: external-trigger"

# This file is the audit itself; its example strings are not real references.
SELF = Path(__file__).resolve()


def _placeholders(path: str) -> str:
    """Collapse every parameter form to {} so both sides compare equal.

    Backend  /patients/{patient_id}/visits   -> /patients/{}/visits
    TS       /patients/${patientId}/visits   -> /patients/{}/visits
    Python   {BASE}/patients/{pid}/visits    -> /patients/{}/visits
    """
    path = re.sub(r"\$\{[^}]*\}", "{}", path)   # TS template interpolation
    path = re.sub(r"\{[^}]*\}", "{}", path)      # FastAPI + f-string params
    # An f-string base like {BASE}/foo collapses to {}/foo; drop that leading {}
    # so it lines up with a route that starts at /foo.
    if path.startswith("{}"):
        path = path[2:]
    path = path.split("?", 1)[0].split("#", 1)[0]   # drop query/fragment
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def _normalize_route(path: str) -> str:
    """Strip the /api/v1 prefix so client-relative paths match.

    Clients set baseURL to `.../api/v1` and then call '/doctor/patients', so the
    version prefix is never present in a client literal. /internal/cron/* has no
    version prefix on either side and is left alone.
    """
    path = _placeholders(path)
    if path.startswith("/api/v1"):
        path = path[len("/api/v1"):] or "/"
    return path


def collect_routes() -> list[dict]:
    """Parse route decorators out of app/routers/*.py via AST.

    AST rather than regex because decorators are structured data -- this reads
    the actual argument, not a line that looks like one.
    """
    prefixes = _router_prefixes()
    routes: list[dict] = []

    for py in sorted(ROUTER_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        source = py.read_text(encoding="utf-8")
        tree = ast.parse(source)
        lines = source.splitlines()
        local_prefix = _local_router_prefix(tree)
        mount_prefix = prefixes.get(py.stem, "")

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                parsed = _parse_route_decorator(deco)
                if parsed is None:
                    continue
                method, raw_path = parsed
                full = f"{mount_prefix}{local_prefix}{raw_path}"
                routes.append({
                    "method": method.upper(),
                    "path": full,
                    "match": _normalize_route(full),
                    "handler": node.name,
                    "file": str(py.relative_to(REPO)).replace("\\", "/"),
                    "line": node.lineno,
                    "external": _has_marker(lines, node),
                })
    return routes


def _parse_route_decorator(deco: ast.expr) -> tuple[str, str] | None:
    """Return (method, path) for @router.get("/x") style decorators, else None."""
    if not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Attribute):
        return None
    method = deco.func.attr
    if method not in HTTP_METHODS:
        return None
    if not deco.args or not isinstance(deco.args[0], ast.Constant):
        return None
    path = deco.args[0].value
    if not isinstance(path, str):
        return None
    return method, path


def _local_router_prefix(tree: ast.AST) -> str:
    """Read prefix= from the module's own APIRouter(...) construction."""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "APIRouter"):
            for kw in node.keywords:
                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                    return kw.value.value or ""
    return ""


def _router_prefixes() -> dict[str, str]:
    """Map router module name -> prefix passed to include_router in main.py.

    main.py mixes two import styles, and both must resolve or the affected
    routers silently get an empty prefix -- which makes every one of their
    routes look unreferenced:
        from .routers import auth            -> include_router(auth.router, ...)
        from .routers.doctor import router as doctor_router
                                             -> include_router(doctor_router, ...)
    """
    if not MAIN_PY.exists():
        return {}
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    aliases = _router_aliases(tree)
    out: dict[str, str] = {}

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "include_router" and node.args):
            continue
        module = _router_module_name(node.args[0], aliases)
        if module is None:
            continue
        prefix = ""
        for kw in node.keywords:
            if kw.arg == "prefix":
                prefix = _static_str(kw.value)
        out[module] = prefix
    return out


def _router_aliases(tree: ast.AST) -> dict[str, str]:
    """Local name -> router module, for `from .routers.X import router as Y`."""
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        parts = node.module.split(".")
        if "routers" not in parts:
            continue
        tail = parts[-1]
        for alias in node.names:
            if tail != "routers":          # from .routers.doctor import router as doctor_router
                out[alias.asname or alias.name] = tail
            else:                          # from .routers import auth, users
                out[alias.asname or alias.name] = alias.name
    return out


def _router_module_name(arg: ast.expr, aliases: dict[str, str]) -> str | None:
    """Resolve the router argument of include_router to its module name."""
    if isinstance(arg, ast.Name):                       # doctor_router
        return aliases.get(arg.id)
    if isinstance(arg, ast.Attribute):                  # auth.router / routers.auth.router
        if isinstance(arg.value, ast.Attribute):
            return arg.value.attr
        if isinstance(arg.value, ast.Name):
            return aliases.get(arg.value.id, arg.value.id)
    return None


def _static_str(node: ast.expr) -> str:
    """Best-effort literal value of a prefix expression.

    settings.API_V1_STR is resolved to its known value; anything else
    unresolvable contributes nothing rather than crashing the scan.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(_static_str(v) for v in node.values)
    if isinstance(node, ast.FormattedValue):
        return _static_str(node.value)
    if isinstance(node, ast.Attribute) and node.attr == "API_V1_STR":
        return "/api/v1"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _static_str(node.left) + _static_str(node.right)
    return ""


def _has_marker(lines: list[str], node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Look for the external-trigger marker in comments above the decorators.

    Scans upward from the topmost decorator through the contiguous comment
    block, so the marker can sit above or between decorator lines.
    """
    first = min([d.lineno for d in node.decorator_list] + [node.lineno])
    i = first - 2                      # 0-indexed line above the decorator
    while i >= 0:
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            if EXTERNAL_MARKER in stripped:
                return True
            i -= 1
            continue
        if not stripped:               # allow blank lines inside the block
            i -= 1
            continue
        break
    return False


# Quoted strings, including multi-line template literals. DOTALL on the backtick
# arm is what lets a template literal span lines; the single/double arms stop at
# a newline because a real JS string cannot contain a raw one.
_STRING_RE = re.compile(
    r"`(?P<bt>(?:[^`\\]|\\.)*)`"
    r"|'(?P<sq>(?:[^'\\\n]|\\.)*)'"
    r'|"(?P<dq>(?:[^"\\\n]|\\.)*)"',
    re.DOTALL,
)


def collect_references() -> dict[str, list[str]]:
    """Map normalized path -> locations that mention it.

    Deliberately indifferent to surrounding syntax: no knowledge of `.post(`,
    axios, fetch, or argument position. That indifference is the whole fix --
    a multi-line call is no different from a single-line one to this scanner.
    """
    refs: dict[str, list[str]] = {}

    for root in CLIENT_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in CLIENT_SUFFIXES or not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.resolve() == SELF:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            rel = str(path.relative_to(REPO)).replace("\\", "/")
            for m in _STRING_RE.finditer(text):
                literal = m.group("bt") or m.group("sq") or m.group("dq") or ""
                for candidate in _path_candidates(literal):
                    line = text.count("\n", 0, m.start()) + 1
                    refs.setdefault(candidate, []).append(f"{rel}:{line}")
    return refs


def _path_candidates(literal: str) -> list[str]:
    """Normalized API-path forms for one string literal.

    Yields both the literal as-is and a version with any leading base-URL
    interpolation removed, so `${BASE}/auth/token` matches /auth/token and a
    full https://host/api/v1/... URL in a test matches too.
    """
    literal = literal.strip()
    if not literal or len(literal) > 300:
        return []

    out: list[str] = []
    # Absolute URL -> keep the path portion only.
    url = re.match(r"https?://[^/]+(/.*)$", literal)
    if url:
        out.append(url.group(1))
    if literal.startswith("/"):
        out.append(literal)
    # ${BASE}/foo or {BASE}/foo -> /foo
    stripped = re.sub(r"^(?:\$?\{[^}]*\})+", "", literal)
    if stripped.startswith("/"):
        out.append(stripped)

    seen, result = set(), []
    for raw in out:
        norm = _normalize_route(raw)
        if len(norm) > 1 and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def audit() -> dict:
    routes = collect_routes()
    refs = collect_references()

    active, external, unreferenced = [], [], []
    for route in routes:
        locations = refs.get(route["match"], [])
        route["referenced_by"] = locations[:5]
        route["reference_count"] = len(locations)
        if route["external"]:
            external.append(route)
        elif locations:
            active.append(route)
        else:
            unreferenced.append(route)

    return {
        "total": len(routes),
        "active": active,
        "external": external,
        "unreferenced": unreferenced,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    result = audit()
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        return 0

    print(f"Routes discovered: {result['total']}")
    print(f"  ACTIVE       {len(result['active'])}")
    print(f"  EXTERNAL     {len(result['external'])}  (marked '{EXTERNAL_MARKER}')")
    print(f"  UNREFERENCED {len(result['unreferenced'])}")

    if result["external"]:
        print("\nEXTERNAL — driven from outside the repo, no in-repo caller expected:")
        for r in result["external"]:
            print(f"  {r['method']:6} {r['path']:<50} {r['file']}:{r['line']}")

    if result["unreferenced"]:
        print("\nUNREFERENCED — candidates for review, NOT confirmed dead:")
        for r in sorted(result["unreferenced"], key=lambda x: x["path"]):
            print(f"  {r['method']:6} {r['path']:<50} {r['file']}:{r['line']}")

    print("\nBlind spots — an unreferenced result may still be live if the path is:")
    print("  * built by concatenation at runtime (BASE + '/x')")
    print("  * held only in a variable, with no literal anywhere in the repo")
    print("  * requested by an external client this repo does not contain")
    print("Confirm by hand before deleting anything.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
