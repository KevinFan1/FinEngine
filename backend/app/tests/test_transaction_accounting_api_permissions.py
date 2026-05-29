import ast
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "api" / "v1" / "transaction_accounting.py"
BIC_SOURCE = Path(__file__).resolve().parents[1] / "api" / "v1" / "bic_accounting.py"
UPLOAD_SOURCE = Path(__file__).resolve().parents[1] / "api" / "v1" / "uploads.py"
OSS_SOURCE = Path(__file__).resolve().parents[1] / "api" / "v1" / "oss.py"
USER_SOURCE = Path(__file__).resolve().parents[1] / "api" / "v1" / "users.py"
AUDIT_SOURCE = Path(__file__).resolve().parents[1] / "api" / "v1" / "audit_logs.py"


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


def _route_functions(source: Path) -> dict[str, ast.AsyncFunctionDef]:
    module = ast.parse(source.read_text())
    return {
        node.name: node
        for node in module.body
        if isinstance(node, ast.AsyncFunctionDef)
    }


def test_transaction_rule_routes_require_superadmin_dependency() -> None:
    route_functions = _route_functions(SOURCE)

    for function_name in {
        "list_rules",
        "create_rule",
        "update_rule",
        "delete_rule",
    }:
        assert "require_superadmin" in _dependency_names(route_functions[function_name])


def test_member_business_operation_routes_do_not_require_admin_dependency() -> None:
    routes_by_source = {
        UPLOAD_SOURCE: {"create_upload_batch", "upload_file_callback"},
        OSS_SOURCE: {"get_oss_sts"},
        SOURCE: {"upload_init", "upload_callback", "rerun_task", "batch_recalculate_tasks"},
        BIC_SOURCE: {"rerun_task", "batch_recalculate_tasks"},
    }
    admin_dependencies = {"require_org_admin_or_above", "require_superadmin"}

    for source, function_names in routes_by_source.items():
        route_functions = _route_functions(source)
        for function_name in function_names:
            dependencies = _dependency_names(route_functions[function_name])
            assert "get_current_user" in dependencies
            assert dependencies.isdisjoint(admin_dependencies)


def test_member_restricted_admin_routes_keep_admin_dependency() -> None:
    routes_by_source = {
        USER_SOURCE: {
            "list_users",
            "create_user",
            "get_user",
            "update_user",
            "update_user_status",
            "reset_user_password",
        },
        AUDIT_SOURCE: {"list_audit_logs"},
    }

    for source, function_names in routes_by_source.items():
        route_functions = _route_functions(source)
        for function_name in function_names:
            assert "require_org_admin_or_above" in _dependency_names(route_functions[function_name])
