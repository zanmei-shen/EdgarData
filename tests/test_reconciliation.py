from edgardata.models.schema import IncomeStatementPayload, SegmentRevenue
from edgardata.pipeline.reconciliation import reconcile_revenue


def test_reconcile_revenue_exact() -> None:
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

    result = reconcile_revenue(payload)

    assert result.status == "RECONCILED_EXACT"
    assert result.reconciliation_error_pct == 0.0
    assert result.residual_value == 0.0


def test_reconcile_revenue_with_residual() -> None:
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
                value=90.0,
                fiscal_year=2025,
                fiscal_period="FY",
            )
        ],
    )

    result = reconcile_revenue(payload)

    assert result.status == "RECONCILED_WITH_RESIDUAL"
    assert result.residual_label == "Corporate / Unallocated Revenue"
    assert result.residual_value == 10.0
