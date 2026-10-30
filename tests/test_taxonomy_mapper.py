from types import SimpleNamespace

import pytest

from edgardata.pipeline.financials import resolve_operating_expenses
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


def test_resolve_operating_expense_component_concepts() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "ResearchAndDevelopmentExpense": {
                    "units": {"USD": [{"val": 18.219, "fy": 2026, "fp": "Q2", "form": "10-Q", "start": "2026-04-01", "end": "2026-06-30"}]}
                },
                "SellingAndMarketingExpense": {
                    "units": {"USD": [{"val": 8.403, "fy": 2026, "fp": "Q2", "form": "10-Q", "start": "2026-04-01", "end": "2026-06-30"}]}
                },
                "GeneralAndAdministrativeExpense": {
                    "units": {"USD": [{"val": 6.461, "fy": 2026, "fp": "Q2", "form": "10-Q", "start": "2026-04-01", "end": "2026-06-30"}]}
                },
            }
        }
    }

    values = [
        resolve_metric_fact(company_facts, metric, 2026, "Q2", "2026-04-01", "2026-06-30").value
        for metric in ("research_and_development", "sales_and_marketing", "general_and_administrative")
    ]

    assert values == [18.219, 8.403, 6.461]
    assert sum(values) == 33.083


def test_resolve_operating_income_concept_for_derived_expenses() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "val": 27.461,
                                "fy": 2026,
                                "fp": "Q2",
                                "form": "10-Q",
                                "start": "2026-04-01",
                                "end": "2026-06-30",
                            }
                        ]
                    }
                }
            }
        }
    }

    resolved = resolve_metric_fact(
        company_facts,
        "operating_income",
        fiscal_year=2026,
        fiscal_period="Q2",
        period_start="2026-04-01",
        period_end="2026-06-30",
    )

    assert resolved is not None
    assert resolved.value == 27.461


def test_derived_operating_expenses_prefer_aligned_facts_over_ambiguous_aggregate() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "ResearchAndDevelopmentExpense": {
                    "units": {"USD": [{"val": 20.6, "fy": 2026, "fp": "Q3", "start": "2026-04-01", "end": "2026-06-30"}]}
                },
                "SellingAndMarketingExpense": {
                    "units": {"USD": [{"val": 8.8, "fy": 2026, "fp": "Q3", "start": "2026-04-01", "end": "2026-06-30"}]}
                },
                "GeneralAndAdministrativeExpense": {
                    "units": {"USD": [{"val": 6.1, "fy": 2026, "fp": "Q3", "start": "2026-04-01", "end": "2026-06-30"}]}
                },
            }
        }
    }

    value, details = resolve_operating_expenses(
        company_facts,
        fiscal_year=2026,
        fiscal_period="Q3",
        period_start="2026-04-01",
        period_end="2026-06-30",
        reported_operating_expenses=SimpleNamespace(value=87.0),
        total_revenue=127.6,
        cost_of_revenue=51.4,
        operating_income=40.6,
    )

    assert value == pytest.approx(35.6)
    assert [detail.expense_label for detail in details] == ["R&D", "Sales & marketing", "General & admin"]
