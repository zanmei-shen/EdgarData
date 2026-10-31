from edgardata.ingestion.company_lookup import (
    company_record_label,
    lookup_company_records,
    normalize_company_value,
    suggest_company_records,
)


COMPANY_TICKERS = {
    "data": [
        {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
        {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
        {"cik_str": 1326801, "ticker": "META", "title": "Meta Platforms, Inc."},
        {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
        {"cik_str": 723254, "ticker": "MU", "title": "Micron Technology, Inc."},
    ]
}


def test_lookup_accepts_tickers_and_company_names() -> None:
    assert lookup_company_records("msft", COMPANY_TICKERS)[0]["ticker"] == "MSFT"
    assert lookup_company_records(" Microsoft Corporation ", COMPANY_TICKERS)[0]["ticker"] == "MSFT"
    assert lookup_company_records("Apple", COMPANY_TICKERS)[0]["ticker"] == "AAPL"
    assert lookup_company_records("Tesla", COMPANY_TICKERS)[0]["ticker"] == "TSLA"
    assert lookup_company_records("Facebook", COMPANY_TICKERS)[0]["ticker"] == "META"
    assert lookup_company_records("Google", COMPANY_TICKERS)[0]["ticker"] == "GOOGL"


def test_lookup_ignores_punctuation_and_formatting() -> None:
    assert normalize_company_value("Tesla, Inc.") == "teslainc"
    assert lookup_company_records("Tesla, Inc.", COMPANY_TICKERS)[0]["ticker"] == "TSLA"
    assert lookup_company_records("meta-platforms", COMPANY_TICKERS)[0]["ticker"] == "META"


def test_suggestions_match_partial_names_and_tickers() -> None:
    assert suggest_company_records("tes", COMPANY_TICKERS)[0]["ticker"] == "TSLA"
    assert suggest_company_records("goo", COMPANY_TICKERS)[0]["ticker"] == "GOOGL"
    assert [record["ticker"] for record in suggest_company_records("mic", COMPANY_TICKERS)] == ["MSFT", "MU"]


def test_lookup_returns_all_ambiguous_name_matches() -> None:
    records = {
        "data": [
            {"ticker": "ABC", "title": "Example Holdings"},
            {"ticker": "XYZ", "title": "Example Holdings"},
        ]
    }

    assert [record["ticker"] for record in lookup_company_records("Example Holdings", records)] == ["ABC", "XYZ"]


def test_lookup_unknown_value_returns_no_matches() -> None:
    assert lookup_company_records("not a company", COMPANY_TICKERS) == []


def test_company_record_label_includes_name_and_ticker() -> None:
    assert company_record_label({"ticker": "MSFT", "title": "Microsoft Corporation"}) == (
        "MSFT - Microsoft Corporation"
    )
    assert company_record_label({"ticker": "META", "title": "Meta Platforms, Inc."}) == (
        "META - Meta Platforms, Inc. (Facebook)"
    )
