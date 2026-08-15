"""HTTP client for SEC EDGAR endpoints."""

from __future__ import annotations

import time
from typing import Any

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from edgardata.config.settings import DEFAULT_SETTINGS, SecEdgarSettings


class EdgarIngestionEngine:
    def __init__(self, user_agent: str, settings: SecEdgarSettings | None = None) -> None:
        self.settings = settings or DEFAULT_SETTINGS
        self.settings = SecEdgarSettings(
            user_agent=user_agent,
            company_tickers_url=self.settings.company_tickers_url,
            companyfacts_base_url=self.settings.companyfacts_base_url,
            companyconcept_base_url=self.settings.companyconcept_base_url,
            requests_per_second=self.settings.requests_per_second,
            retry_attempts=self.settings.retry_attempts,
            retry_backoff_seconds=self.settings.retry_backoff_seconds,
        )
        self.headers = {"User-Agent": user_agent}
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.settings.min_request_interval_seconds:
            time.sleep(self.settings.min_request_interval_seconds - elapsed)
        self._last_request_time = time.monotonic()

    def _get_json(self, url: str) -> dict[str, Any]:
        retrying = Retrying(
            retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
            stop=stop_after_attempt(self.settings.retry_attempts),
            wait=wait_exponential(
                multiplier=self.settings.retry_backoff_seconds,
                min=self.settings.retry_backoff_seconds,
                max=5.0,
            ),
            reraise=True,
        )

        for attempt in retrying:
            with attempt:
                self._rate_limit()
                with httpx.Client(headers=self.headers, timeout=30.0) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    return response.json()

        raise RuntimeError("request failed")

    def fetch_company_tickers(self) -> dict[str, Any]:
        return self._get_json(self.settings.company_tickers_url)

    def fetch_company_facts(self, cik: str) -> dict[str, Any]:
        padded_cik = str(cik).zfill(10)
        url = f"{self.settings.companyfacts_base_url}/CIK{padded_cik}.json"
        return self._get_json(url)

    def fetch_company_concept(self, cik: str, taxonomy: str, concept: str) -> dict[str, Any]:
        padded_cik = str(cik).zfill(10)
        url = f"{self.settings.companyconcept_base_url}/CIK{padded_cik}/{taxonomy}/{concept}.json"
        return self._get_json(url)
