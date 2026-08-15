import json

from edgardata.models.schema import IncomeStatementPayload, ReconciliationResult, SegmentRevenue
from edgardata.storage.persistence import payload_to_record, persist_partitioned_json


def test_persist_partitioned_json_writes_expected_layout(tmp_path) -> None:
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
    reconciliation = ReconciliationResult(
        ticker="AAPL",
        fiscal_year=2025,
        fiscal_period="FY",
        total_revenue=100.0,
        segment_revenue_sum=100.0,
        reconciliation_error_pct=0.0,
        status="RECONCILED_EXACT",
    )

    target_file = persist_partitioned_json(payload, tmp_path, reconciliation)

    assert target_file.name == "data.json"
    assert target_file.parent.name == "ticker=AAPL"
    assert target_file.parent.parent.name == "year=2025"

    record = json.loads(target_file.read_text(encoding="utf-8"))
    assert record["ticker"] == "AAPL"
    assert record["reconciliation"]["status"] == "RECONCILED_EXACT"


def test_payload_to_record_includes_reconciliation() -> None:
    payload = IncomeStatementPayload(
        ticker="AAPL",
        cik="0000320193",
        fiscal_year=2025,
        fiscal_period="FY",
    )
    reconciliation = ReconciliationResult(
        ticker="AAPL",
        fiscal_year=2025,
        fiscal_period="FY",
        total_revenue=0.0,
        segment_revenue_sum=0.0,
        reconciliation_error_pct=0.0,
        status="RECONCILED_EXACT",
    )

    record = payload_to_record(payload, reconciliation)

    assert record["ticker"] == "AAPL"
    assert record["reconciliation"]["status"] == "RECONCILED_EXACT"
