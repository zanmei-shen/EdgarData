"""Helpers for resolving SEC company directory records."""

from __future__ import annotations

import re
from typing import Any


COMPANY_ALIASES = {
    "facebook": "META",
    "google": "GOOGL",
    "alphabet": "GOOGL",
}

__all__ = [
    "COMPANY_ALIASES",
    "company_record_label",
    "company_records",
    "lookup_company_records",
    "normalize_company_value",
    "suggest_company_records",
]


def normalize_company_value(value: str) -> str:
    """Normalize names and tickers for punctuation-insensitive matching."""

    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _company_records(company_tickers: dict[str, Any]) -> list[dict[str, Any]]:
    records = company_tickers.get("data")
    if isinstance(records, list):
        return [record for record in records if isinstance(record, dict)]

    return [
        value
        for value in company_tickers.values()
        if isinstance(value, dict) and value.get("ticker")
    ]


def company_records(company_tickers: dict[str, Any]) -> list[dict[str, Any]]:
    """Return valid SEC company records for autocomplete controls."""

    return _company_records(company_tickers)


def lookup_company_records(
    value: str,
    company_tickers: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return records matching a ticker or company name, case-insensitively."""

    normalized_value = normalize_company_value(value)
    if not normalized_value:
        return []

    records = _company_records(company_tickers)
    alias_ticker = COMPANY_ALIASES.get(normalized_value)
    ticker_matches = [
        record
        for record in records
        if normalize_company_value(str(record.get("ticker", "")))
        == (normalize_company_value(alias_ticker) if alias_ticker else normalized_value)
    ]
    if ticker_matches:
        return ticker_matches

    matches = []
    for record in records:
        names = [
            normalize_company_value(str(record.get(field, "")))
            for field in ("title", "name", "company_name")
        ]
        if any(name == normalized_value or name.startswith(normalized_value) for name in names):
            matches.append(record)
    return matches


def suggest_company_records(
    value: str,
    company_tickers: dict[str, Any],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return likely company matches for an in-progress input."""

    normalized_value = normalize_company_value(value)
    if not normalized_value:
        return []

    records = _company_records(company_tickers)
    alias_ticker = COMPANY_ALIASES.get(normalized_value)
    ranked_matches: list[tuple[int, str, dict[str, Any]]] = []
    for record in records:
        ticker_text = str(record.get("ticker", "")).strip()
        ticker = normalize_company_value(ticker_text)
        names = [
            normalize_company_value(str(record.get(field, "")))
            for field in ("title", "name", "company_name")
        ]
        if alias_ticker and ticker == normalize_company_value(alias_ticker):
            score = 0
        elif ticker == normalized_value:
            score = 1
        elif ticker.startswith(normalized_value):
            score = 2
        elif any(name == normalized_value for name in names):
            score = 3
        elif any(name.startswith(normalized_value) for name in names if name):
            score = 4
        elif any(normalized_value in name for name in names if name):
            score = 5
        else:
            continue
        ranked_matches.append((score, ticker_text.casefold(), record))

    ranked_matches.sort(key=lambda match: (match[0], match[1]))
    return [record for _, _, record in ranked_matches[:limit]]


def company_record_label(record: dict[str, Any]) -> str:
    ticker = str(record.get("ticker", "")).strip().upper()
    name = str(record.get("title") or record.get("name") or "Unknown company").strip()
    aliases = [
        alias.title()
        for alias, alias_ticker in COMPANY_ALIASES.items()
        if alias_ticker == ticker and alias.title() not in name
    ]
    alias_suffix = f" ({', '.join(aliases)})" if aliases else ""
    return f"{ticker} - {name}{alias_suffix}"
