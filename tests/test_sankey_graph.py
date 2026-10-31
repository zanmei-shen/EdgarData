from edgardata.exports.sankey_exporter import build_tencent_style_sankey_graph
from edgardata.models.schema import ExpenseDetail, IncomeStatementPayload, SegmentRevenue


def test_build_tencent_style_sankey_graph_layers_nodes_and_links() -> None:
    payload = IncomeStatementPayload(
        ticker="AAPL",
        cik="0000320193",
        fiscal_year=2025,
        fiscal_period="FY",
        total_revenue=100.0,
        cost_of_revenue=40.0,
        operating_expenses=20.0,
        net_profit=30.0,
        segments=[
            SegmentRevenue(
                segment_axis="us-gaap:ProductOrServiceAxis",
                segment_member="IPhoneMember",
                segment_label="iPhone",
                value=60.0,
                fiscal_year=2025,
                fiscal_period="FY",
            ),
            SegmentRevenue(
                segment_axis="us-gaap:ProductOrServiceAxis",
                segment_member="ServicesMember",
                segment_label="Services",
                value=40.0,
                fiscal_year=2025,
                fiscal_period="FY",
            ),
        ],
    )

    graph = build_tencent_style_sankey_graph(payload)

    assert graph.ticker == "AAPL"
    assert any(node.id == "gross_profit" for node in graph.nodes)
    assert any(node.id == "operating_profit" for node in graph.nodes)
    assert any(link.source == "revenue" and link.target == "gross_profit" for link in graph.links)
    assert any(link.source == "gross_profit" and link.target == "operating_profit" for link in graph.links)
    assert graph.top_level["gross_profit"] == 60.0
    assert graph.top_level["operating_profit"] == 40.0


def test_build_tencent_style_sankey_graph_includes_expense_details_when_present() -> None:
    payload = IncomeStatementPayload(
        ticker="AAPL",
        cik="0000320193",
        fiscal_year=2025,
        fiscal_period="FY",
        total_revenue=100.0,
        cost_of_revenue=40.0,
        operating_expenses=20.0,
        net_profit=30.0,
        segments=[],
        operating_expense_details=[
            ExpenseDetail(expense_label="R&D", value=12.0, fiscal_year=2025, fiscal_period="FY"),
            ExpenseDetail(expense_label="Sales & marketing", value=8.0, fiscal_year=2025, fiscal_period="FY"),
        ],
    )

    graph = build_tencent_style_sankey_graph(payload)

    assert any(node.id == "expense_r_d" for node in graph.nodes)
    assert any(node.id == "expense_sales_marketing" for node in graph.nodes)
    assert any(link.source == "operating_expenses" and link.target == "expense_r_d" for link in graph.links)
    assert any(link.source == "operating_expenses" and link.target == "expense_sales_marketing" for link in graph.links)


def test_build_graph_handles_negative_profit_flows() -> None:
    payload = IncomeStatementPayload(
        ticker="LOSS",
        cik="0000000000",
        fiscal_year=2026,
        fiscal_period="Q3",
        total_revenue=100.0,
        cost_of_revenue=140.0,
        operating_expenses=20.0,
        net_profit=-70.0,
    )

    graph = build_tencent_style_sankey_graph(payload)

    assert all(link.value >= 0 for link in graph.links)
    assert graph.top_level["gross_profit"] == -40.0
    assert graph.top_level["operating_profit"] == -60.0


def test_build_graph_preserves_nested_segment_flow() -> None:
    payload = IncomeStatementPayload(
        ticker="GOOG",
        cik="0001652044",
        fiscal_year=2026,
        fiscal_period="Q3",
        total_revenue=100.0,
        cost_of_revenue=40.0,
        operating_expenses=20.0,
        net_profit=30.0,
        segments=[
            SegmentRevenue(
                segment_axis="custom:RevenueAxis",
                segment_member="custom:SearchMember",
                segment_label="Search advertising",
                value=60.0,
                fiscal_year=2026,
                fiscal_period="Q3",
                parent_id="segment_googleservices",
            ),
            SegmentRevenue(
                segment_axis="custom:RevenueAxis",
                segment_member="custom:GoogleServicesMember",
                segment_label="Google Services",
                value=60.0,
                fiscal_year=2026,
                fiscal_period="Q3",
            ),
        ],
    )

    graph = build_tencent_style_sankey_graph(payload)

    assert any(
        link.source == "segment_search_advertising"
        and link.target == "segment_google_services"
        and link.value == 60.0
        for link in graph.links
    )
    assert any(
        link.source == "segment_google_services"
        and link.target == "revenue"
        and link.value == 60.0
        for link in graph.links
    )
    assert all(link.value >= 0 for link in graph.links)


def test_build_tencent_style_sankey_graph_formats_quarter_period_label() -> None:
    payload = IncomeStatementPayload(
        ticker="AAPL",
        cik="0000320193",
        fiscal_year=2025,
        fiscal_period="Q2",
        total_revenue=100.0,
        cost_of_revenue=40.0,
        operating_expenses=20.0,
        net_profit=30.0,
        segments=[],
    )

    graph = build_tencent_style_sankey_graph(payload)

    assert graph.period == "Q2FY2025"


def test_build_graph_rejects_invalid_period_label() -> None:
    payload = IncomeStatementPayload(
        ticker="AAPL",
        cik="0000320193",
        fiscal_year=2025,
        fiscal_period="NONE",
        total_revenue=100.0,
        cost_of_revenue=40.0,
        operating_expenses=20.0,
        net_profit=30.0,
    )

    try:
        build_tencent_style_sankey_graph(payload)
    except ValueError as exc:
        assert "Unsupported fiscal period" in str(exc)
    else:
        raise AssertionError("Invalid fiscal period should be rejected")


def test_build_graph_uses_below_operating_bridge() -> None:
    payload = IncomeStatementPayload(
        ticker="GOOG",
        cik="0001652044",
        fiscal_year=2026,
        fiscal_period="Q2",
        total_revenue=100.0,
        cost_of_revenue=40.0,
        operating_expenses=20.0,
        income_before_tax=50.0,
        other_income_expense=10.0,
        income_tax_expense=20.0,
        net_profit=30.0,
    )

    graph = build_tencent_style_sankey_graph(payload)

    assert any(node.id == "other_income" for node in graph.nodes)
    assert any(node.id == "income_before_tax" for node in graph.nodes)
    assert any(node.id == "income_tax" for node in graph.nodes)
    assert not any(link.source == "operating_profit" and link.target == "net_profit" for link in graph.links)

    incoming = {node.id: 0.0 for node in graph.nodes}
    outgoing = {node.id: 0.0 for node in graph.nodes}
    for link in graph.links:
        outgoing[link.source] += link.value
        incoming[link.target] += link.value

    assert incoming["income_before_tax"] == outgoing["income_before_tax"] == 50.0
    assert incoming["operating_profit"] == outgoing["operating_profit"] == 40.0


def test_build_graph_keeps_missing_bridge_as_explicit_adjustment() -> None:
    payload = IncomeStatementPayload(
        ticker="AMZN",
        cik="0001018724",
        fiscal_year=2026,
        fiscal_period="Q2",
        total_revenue=200.0,
        cost_of_revenue=95.0,
        operating_expenses=77.0,
        net_profit=62.0,
    )

    graph = build_tencent_style_sankey_graph(payload)

    adjustment = next(node for node in graph.nodes if node.id == "below_operating_adjustment")
    assert adjustment.value == 34.0
    assert not any(link.source == "operating_profit" and link.target == "net_profit" and link.value == 62.0 for link in graph.links)
    assert any(link.source == "below_operating_adjustment" and link.target == "net_profit" for link in graph.links)
