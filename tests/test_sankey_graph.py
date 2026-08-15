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
