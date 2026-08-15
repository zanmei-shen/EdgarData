from edgardata.parser.segment_parser import extract_segment_revenues, group_segment_revenues_by_period, normalize_segment_label


def test_normalize_segment_label_handles_member_suffix() -> None:
    assert normalize_segment_label("aapl:IPhoneMember") == "iPhone"
    assert normalize_segment_label("ServicesMember") == "Services"


def test_extract_segment_revenues_filters_dimensional_facts() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "val": 200.0,
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "dimensions": {
                                    "us-gaap:ProductOrServiceAxis": "aapl:IPhoneMember",
                                },
                            },
                            {
                                "val": 300.0,
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "dimensions": {
                                    "us-gaap:StatementBusinessSegmentsAxis": "aapl:ServicesMember",
                                },
                            },
                        ]
                    }
                }
            }
        }
    }

    segments = extract_segment_revenues(company_facts, fiscal_year=2025, fiscal_period="FY")
    grouped = group_segment_revenues_by_period(segments)

    assert len(segments) == 2
    assert segments[0].segment_label == "iPhone"
    assert segments[1].segment_label == "Services"
    assert grouped[(2025, "FY")][0].value == 200.0
