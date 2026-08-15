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
