from edgardata.config.settings import DEFAULT_SETTINGS
from edgardata.ingestion.edgar_client import EdgarIngestionEngine
from edgardata.models.schema import IncomeStatementPayload, SegmentRevenue


def test_schema_and_client_scaffold() -> None:
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

    client = EdgarIngestionEngine(user_agent=DEFAULT_SETTINGS.user_agent)

    assert payload.ticker == "AAPL"
    assert client.headers["User-Agent"] == DEFAULT_SETTINGS.user_agent
