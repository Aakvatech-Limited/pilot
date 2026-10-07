from __future__ import annotations

import typing

from pilot._vendor.packaging.specifiers import InvalidSpecifier, SpecifierSet
from pilot.core.app.validator.base import bench_table, get_bench_python, module_path, read_pyproject
from pilot.core.app.validator.utils.bench_runner import run_in_bench
from pilot.exceptions import AppValidationError

if typing.TYPE_CHECKING:
    from pilot.core.app import App

_EXAMPLE_SPECIFIER = ">=16.0.0,<17.0.0"

_REQUIRED_APPS_AST_SCRIPT = """
import ast, json, sys

req = json.load(sys.stdin)
path = req["path"]
try:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        tree = ast.parse(f.read(), filename=path)
except SyntaxError as exc:
    print(json.dumps({"syntax_error": f"line {exc.lineno}: {exc.msg}"}))
    sys.exit(0)
except (OSError, UnicodeDecodeError):
    print(json.dumps({"required_apps": []}))
    sys.exit(0)

def extract_string_values(val_node):
    if isinstance(val_node, (ast.List, ast.Tuple, ast.Set)):
        return [
            elt.value.rsplit("/", 1)[-1]
            for elt in val_node.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
    elif isinstance(val_node, ast.Constant) and isinstance(val_node.value, str):
        return [val_node.value.rsplit("/", 1)[-1]]
    return []

def module_level_statements(body):
    stmts = []
    for node in body:
        stmts.append(node)
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Constant):
                if node.test.value:
                    stmts += module_level_statements(node.body)
                else:
                    stmts += module_level_statements(node.orelse)
            elif isinstance(node.test, ast.Name) and node.test.id in ("True", "False"):
                if node.test.id == "True":
                    stmts += module_level_statements(node.body)
                else:
                    stmts += module_level_statements(node.orelse)
            else:
                stmts += module_level_statements(node.body + node.orelse)
        elif isinstance(node, ast.Try):
            handled = [s for h in node.handlers for s in h.body]
            stmts += module_level_statements(node.body + node.orelse + node.finalbody + handled)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            stmts += module_level_statements(node.body)
    return stmts

required_apps = []
for node in module_level_statements(tree.body):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "required_apps":
                required_apps.extend(extract_string_values(node.value))
    elif isinstance(node, ast.AnnAssign):
        if isinstance(node.target, ast.Name) and node.target.id == "required_apps" and node.value is not None:
            required_apps.extend(extract_string_values(node.value))
    elif isinstance(node, ast.AugAssign):
        if isinstance(node.target, ast.Name) and node.target.id == "required_apps":
            required_apps.extend(extract_string_values(node.value))
    elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call = node.value
        if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
            if call.func.value.id == "required_apps":
                if call.func.attr == "append" and call.args:
                    arg = call.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        required_apps.append(arg.value.rsplit("/", 1)[-1])
                elif call.func.attr == "extend" and call.args:
                    arg = call.args[0]
                    required_apps.extend(extract_string_values(arg))

print(json.dumps({"required_apps": list(dict.fromkeys(required_apps))}))
"""


class DependencyDeclarationsCheck:
    """Ensure hooks and pyproject.toml have sane dependency requirements."""

    def run(self, app: "App") -> None:
        if app.module_name == "frappe":
            return  # the framework itself has nothing to declare a dependency on

        declared = self.get_frappe_dependencies(app)
        if "frappe" not in declared:
            raise AppValidationError(
                f"'{app.config.name}' must declare the frappe versions it supports in pyproject.toml.\n"
                "Add:\n"
                "  [tool.bench.frappe-dependencies]\n"
                f'  frappe = "{_EXAMPLE_SPECIFIER}"'
            )
        self._check_version_specifiers(app, declared)

        # hooks.py's required_apps never lists frappe itself (it's implicit),
        # while pyproject.toml always does - exclude it before comparing.
        missing = sorted(set(self.get_hooks_required_apps(app)) - (set(declared) - {"frappe"}))
        if missing:
            raise AppValidationError(
                f"'{app.config.name}' requires {missing} in hooks.py, but pyproject.toml's "
                "[tool.bench.frappe-dependencies] doesn't declare them.\n"
                f'Add one entry per app, e.g. {missing[0]} = "{_EXAMPLE_SPECIFIER}"'
            )

    def get_hooks_required_apps(self, app: "App") -> list[str]:
        """Parse hooks.py (guaranteed present by RepoStructureCheck) for required_apps."""
        hooks_path = module_path(app) / "hooks.py"
        if not hooks_path.is_file():
            return []
        bench_python = get_bench_python(app)
        data = run_in_bench(bench_python, _REQUIRED_APPS_AST_SCRIPT, {"path": str(hooks_path)})
        if "syntax_error" in data:
            raise AppValidationError(
                f"'{app.config.name}' has syntax errors in {app.module_name}/hooks.py: {data['syntax_error']}"
            )
        return data.get("required_apps", [])

    def get_frappe_dependencies(self, app: "App") -> dict[str, str]:
        """The `[tool.bench.frappe-dependencies]` table as {app: version specifier}."""
        pyproject_data = read_pyproject(app)
        if pyproject_data is None:
            raise AppValidationError(
                f"'{app.config.name}' has no pyproject.toml, so it can't declare the frappe "
                "versions it supports. Scaffold one with 'bench new-app'."
            )

        declared = bench_table(app).get("frappe-dependencies", {})
        if not isinstance(declared, dict):
            raise AppValidationError(
                f"'{app.config.name}' has an invalid [tool.bench.frappe-dependencies] in "
                f"pyproject.toml: expected a table of versions, got {type(declared).__name__}.\n"
                f'Use one entry per app, e.g. frappe = "{_EXAMPLE_SPECIFIER}"'
            )
        return declared

    def _check_version_specifiers(self, app: "App", declared: dict[str, str]) -> None:
        for name, specifier in declared.items():
            if not isinstance(specifier, str):
                raise AppValidationError(
                    f"'{app.config.name}' has an invalid [tool.bench.frappe-dependencies] in "
                    f"pyproject.toml: {name}'s version must be a string, got {type(specifier).__name__}."
                )
            if not specifier.strip():
                raise AppValidationError(
                    f"'{app.config.name}' declares '{name}' with no version in pyproject.toml's "
                    f"[tool.bench.frappe-dependencies].\nUse PEP 440 ranges, e.g. {name} = \"{_EXAMPLE_SPECIFIER}\""
                )
            try:
                SpecifierSet(specifier)
            except InvalidSpecifier as exc:
                raise AppValidationError(
                    f"'{app.config.name}' declares an invalid version for '{name}' in "
                    f'pyproject.toml: "{specifier}".\nUse a valid PEP 440 specifier, e.g. "{_EXAMPLE_SPECIFIER}".'
                ) from exc
