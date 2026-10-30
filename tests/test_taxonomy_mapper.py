from edgardata.parser.taxonomy_mapper import resolve_metric_fact


def test_resolve_metric_fact_uses_primary_concept() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "val": 100.0,
                                "unit": "USD",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2025-09-27",
                            }
                        ]
                    }
                }
            }
        }
    }

    resolved = resolve_metric_fact(company_facts, "total_revenue", fiscal_year=2025, fiscal_period="FY")

    assert resolved is not None
    assert resolved.concept == "Revenues"
    assert resolved.value == 100.0


def test_resolve_metric_fact_falls_back_to_secondary_concept() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "SalesRevenueNet": {
                    "units": {
                        "USD": [
                            {
                                "val": 250.0,
                                "unit": "USD",
                                "fy": 2024,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2024-09-28",
                            }
                        ]
                    }
                }
            }
        }
    }

    resolved = resolve_metric_fact(company_facts, "total_revenue", fiscal_year=2024, fiscal_period="FY")

    assert resolved is not None
    assert resolved.concept == "SalesRevenueNet"
    assert resolved.value == 250.0


def test_resolve_metric_fact_prefers_latest_matching_fact() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "val": 100.0,
                                "unit": "USD",
                                "fy": 2024,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2024-09-28",
                                "filed": "2024-11-01",
                            },
                            {
                                "val": 200.0,
                                "unit": "USD",
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2025-09-27",
                                "filed": "2025-10-31",
                            },
                        ]
                    }
                }
            }
        }
    }

    resolved = resolve_metric_fact(company_facts, "total_revenue")

    assert resolved is not None
    assert resolved.value == 200.0


def test_resolve_metric_fact_rejects_missing_period_metadata() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "SalesRevenueNet": {
                    "units": {
                        "USD": [
                            {
                                "val": 182.8,
                                "fy": 0,
                                "fp": "None",
                                "form": "8-K",
                            },
                            {
                                "val": 416.2,
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                            },
                        ]
                    }
                }
            }
        }
    }

    resolved = resolve_metric_fact(company_facts, "total_revenue", fiscal_year=2025, fiscal_period="FY")

    assert resolved is not None
    assert resolved.value == 416.2


def test_resolve_metric_fact_rejects_q2_year_to_date_fact() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "val": 250.0,
                                "start": "2025-09-28",
                                "end": "2026-03-28",
                                "fy": 2026,
                                "fp": "Q2",
                                "form": "10-Q",
                            },
                            {
                                "val": 111.0,
                                "start": "2025-12-28",
                                "end": "2026-03-28",
                                "fy": 2026,
                                "fp": "Q2",
                                "form": "10-Q",
                                "accn": "0000320193-26-000013",
                            },
                        ]
                    }
                }
            }
        }
    }

    resolved = resolve_metric_fact(company_facts, "total_revenue", fiscal_year=2026, fiscal_period="Q2")

    assert resolved is not None
    assert resolved.value == 111.0
    assert resolved.period_start == "2025-12-28"
    assert resolved.accession == "0000320193-26-000013"
