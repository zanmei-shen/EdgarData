from edgardata.exports.sankey_exporter import export_to_sankey_json
from edgardata.models.schema import IncomeStatementPayload, SegmentRevenue


def test_export_to_sankey_json_shape() -> None:
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
                value=100.0,
                fiscal_year=2025,
                fiscal_period="FY",
            )
        ],
    )

    exported = export_to_sankey_json(payload)

    assert exported["ticker"] == "AAPL"
    assert exported["period"] == "FY2025"
    assert exported["top_level"]["total_revenue"] == 100.0
    assert exported["segment_breakdown"][0]["source"] == "iPhone"
    assert exported["segment_breakdown"][0]["target"] == "Revenue"
