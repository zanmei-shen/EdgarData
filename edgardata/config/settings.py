"""Shared runtime settings for SEC EDGAR access."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecEdgarSettings:
    user_agent: str
    company_tickers_url: str = "https://www.sec.gov/files/company_tickers.json"
    companyfacts_base_url: str = "https://data.sec.gov/api/xbrl/companyfacts"
    companyconcept_base_url: str = "https://data.sec.gov/api/xbrl/companyconcept"
    requests_per_second: float = 10.0
    retry_attempts: int = 3
    retry_backoff_seconds: float = 0.5

    @property
    def min_request_interval_seconds(self) -> float:
        return 1.0 / self.requests_per_second


DEFAULT_SETTINGS = SecEdgarSettings(user_agent="Sample Company Name AdminContact@domain.com")
