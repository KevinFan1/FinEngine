from app.services.cash_flow_seed_service import DEFAULT_CASH_FLOW_ITEMS


def test_default_cash_flow_items_keep_parent_child_structure() -> None:
    groups = [item for item in DEFAULT_CASH_FLOW_ITEMS if item.parent_code is None]
    children = [item for item in DEFAULT_CASH_FLOW_ITEMS if item.parent_code is not None]

    assert len(groups) == 9
    assert len(children) == 51
    assert {item.code for item in groups} == {"A", "B", "C", "D", "E", "F", "G", "H", "I"}


def test_default_cash_flow_items_mark_summary_and_check_rows() -> None:
    by_code = {item.code: item for item in DEFAULT_CASH_FLOW_ITEMS}

    assert by_code["A"].summary_method == "sum_children"
    assert by_code["A"].item_type == "group"
    assert by_code["A1"].parent_code == "A"
    assert by_code["A1"].flow_direction == "inflow"
    assert by_code["B12"].name == "支付达人分账佣金"
    assert by_code["B18"].name == "支付达人分账佣金"
    assert by_code["C"].item_type == "net"
    assert by_code["C"].summary_method == "formula"
    assert by_code["C_CHECK"].name == "校验"
    assert by_code["C_CHECK"].item_type == "check"
