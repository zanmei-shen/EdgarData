from edgardata.parser.segment_parser import (
    extract_filing_product_revenues,
    extract_filing_segment_revenues,
    extract_segment_revenues,
    group_segment_revenues_by_period,
    normalize_segment_label,
)


def test_extract_filing_product_revenues_reads_inline_xbrl_quarter_value() -> None:
    xml = b'''<root xmlns="urn:test"><context id="q3"><period><startDate>2026-07-01</startDate><endDate>2026-09-30</endDate></period></context></root>'''
    html = b'''<table><tr><td>Google Search &amp; other</td><td><ix:nonFraction name="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax" contextRef="q3" scale="6">63,350</ix:nonFraction></td></tr></table>'''

    segments = extract_filing_product_revenues(
        html,
        xml,
        period_start="2026-07-01",
        period_end="2026-09-30",
        fiscal_year=2026,
        fiscal_period="Q3",
    )

    assert len(segments) == 1
    assert segments[0].segment_label == "Google Search & other"
    assert segments[0].value == 63_350_000_000
    assert segments[0].parent_id == "segment_googleservices"


def test_normalize_segment_label_handles_member_suffix() -> None:
    assert normalize_segment_label("aapl:IPhoneMember") == "iPhone"
    assert normalize_segment_label("ServicesMember") == "Services"
    assert normalize_segment_label("goog:GoogleServicesMember") == "Google Services"


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


def test_extract_segment_revenues_accepts_sec_segment_shape() -> None:
    company_facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "val": 75.0,
                                "fy": 2025,
                                "fp": "FY",
                                "segment": {
                                    "dimension": "us-gaap:ProductOrServiceAxis",
                                    "value": "aapl:ServicesMember",
                                },
                            }
                        ]
                    }
                }
            }
        }
    }

    segments = extract_segment_revenues(company_facts, fiscal_year=2025, fiscal_period="FY")

    assert len(segments) == 1
    assert segments[0].segment_label == "Services"
    assert segments[0].value == 75.0


def test_extract_filing_segment_revenues_matches_exact_context_and_removes_subtotal() -> None:
        xml = b'''<?xml version="1.0"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
                    xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
                    xmlns:srt="http://fasb.org/srt/2025"
                    xmlns:us-gaap="http://fasb.org/us-gaap/2025"
                    xmlns:aapl="http://www.apple.com/20260328">
            <context id="q2product"><period><startDate>2025-12-28</startDate><endDate>2026-03-28</endDate></period>
                <entity><segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">us-gaap:ProductMember</xbrldi:explicitMember></segment></entity>
            </context>
            <context id="q2iphone"><period><startDate>2025-12-28</startDate><endDate>2026-03-28</endDate></period>
                <entity><segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">aapl:IPhoneMember</xbrldi:explicitMember></segment></entity>
            </context>
            <context id="q2mac"><period><startDate>2025-12-28</startDate><endDate>2026-03-28</endDate></period>
                <entity><segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">aapl:MacMember</xbrldi:explicitMember></segment></entity>
            </context>
            <context id="ytd"><period><startDate>2025-09-28</startDate><endDate>2026-03-28</endDate></period>
                <entity><segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">aapl:IPhoneMember</xbrldi:explicitMember></segment></entity>
            </context>
            <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q2product">100</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
            <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q2iphone">60</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
            <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q2mac">40</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
        </xbrl>'''

        segments = extract_filing_segment_revenues(xml, "2025-12-28", "2026-03-28", 2026, "Q2")

        assert len(segments) == 2
        assert sum(segment.value for segment in segments) == 100.0
        assert {segment.segment_label for segment in segments} == {"iPhone", "Mac"}


def test_extract_filing_segment_revenues_adds_residual_to_other() -> None:
    xml = b'''<?xml version="1.0"?>
    <xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:us-gaap="http://fasb.org/us-gaap/2025">
        <context id="total"><period><startDate>2026-07-01</startDate><endDate>2026-09-30</endDate></period></context>
        <context id="services"><period><startDate>2026-07-01</startDate><endDate>2026-09-30</endDate></period><entity><segment><xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">us-gaap:GoogleServicesMember</xbrldi:explicitMember></segment></entity></context>
        <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="total">100</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
        <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="services">90</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
    </xbrl>'''

    segments = extract_filing_segment_revenues(xml, "2026-07-01", "2026-09-30", 2026, "Q3")

    assert len(segments) == 2
    assert sum(segment.value for segment in segments) == 100.0
    assert next(segment for segment in segments if segment.segment_label == "Other").value == 10.0
