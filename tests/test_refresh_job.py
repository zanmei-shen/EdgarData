from edgardata.jobs.refresh_job import materialize_income_statement
from edgardata.models.schema import IncomeStatementPayload, SegmentRevenue


def test_materialize_income_statement_composes_pipeline(tmp_path) -> None:
    payload = IncomeStatementPayload(
        ticker="AAPL",
        cik="0000320193",
        fiscal_year=2025,
        fiscal_period="FY",
        total_revenue=100.0,
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

    artifacts = materialize_income_statement(payload, tmp_path)

    assert artifacts["reconciliation"].status == "RECONCILED_EXACT"
    assert artifacts["sankey_json"]["ticker"] == "AAPL"
    assert artifacts["persisted_path"].exists()
