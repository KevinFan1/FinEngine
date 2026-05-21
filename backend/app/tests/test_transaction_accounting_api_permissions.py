import ast
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "api" / "v1" / "transaction_accounting.py"


def _dependency_names(function: ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for default in function.args.defaults:
        if (
            isinstance(default, ast.Call)
            and isinstance(default.func, ast.Name)
            and default.func.id == "Depends"
            and default.args
            and isinstance(default.args[0], ast.Name)
        ):
            names.add(default.args[0].id)
    return names


def test_transaction_rule_routes_require_superadmin_dependency() -> None:
    module = ast.parse(SOURCE.read_text())
    route_functions = {
        node.name: node
        for node in module.body
        if isinstance(node, ast.AsyncFunctionDef)
    }

    for function_name in {
        "list_rules",
        "create_rule",
        "update_rule",
        "delete_rule",
    }:
        assert "require_superadmin" in _dependency_names(route_functions[function_name])
