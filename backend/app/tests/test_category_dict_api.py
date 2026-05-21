import ast
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "api" / "v1" / "category_dicts.py"


def test_category_dict_routes_require_superadmin_dependency() -> None:
    module = ast.parse(SOURCE.read_text())
    route_functions = {
        node.name: node
        for node in module.body
        if isinstance(node, ast.AsyncFunctionDef)
    }

    for function_name in {
        "list_category_dicts",
        "create_category_dict",
        "update_category_dict",
        "delete_category_dict",
        "classify_single",
        "classify_batch_endpoint",
    }:
        dependency_names = {
            default.args[0].id
            for default in route_functions[function_name].args.defaults
            if isinstance(default, ast.Call)
            and isinstance(default.func, ast.Name)
            and default.func.id == "Depends"
            and default.args
            and isinstance(default.args[0], ast.Name)
        }

        assert "require_superadmin" in dependency_names
