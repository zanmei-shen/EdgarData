"""Segment dimension parsing utilities."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from edgardata.models.schema import SegmentRevenue
from edgardata.parser.taxonomy_mapper import FALLBACK_CONCEPTS


def normalize_segment_label(segment_member: str) -> str:
    local_name = segment_member.split(":", 1)[-1].removesuffix("Member")
    if local_name == "IPhone":
        return "iPhone"
    if "_" in local_name:
        return local_name.replace("_", " ").strip()
    return local_name


def build_segment_revenue(segment_axis: str, segment_member: str, value: float, fiscal_year: int, fiscal_period: str) -> SegmentRevenue:
    return SegmentRevenue(
        segment_axis=segment_axis,
        segment_member=segment_member,
        segment_label=normalize_segment_label(segment_member),
        value=value,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
    )


def extract_segment_revenues(
    company_facts: dict[str, Any],
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    concepts: tuple[str, ...] | None = None,
    taxonomy: str = "us-gaap",
    allowed_axes: tuple[str, ...] = (
        "us-gaap:StatementBusinessSegmentsAxis",
        "us-gaap:ProductOrServiceAxis",
    ),
) -> list[SegmentRevenue]:
    target_concepts = concepts or FALLBACK_CONCEPTS["total_revenue"]
    facts_by_concept = _concepts(company_facts, taxonomy)
    segment_revenues: list[SegmentRevenue] = []

    for concept in target_concepts:
        concept_payload = facts_by_concept.get(concept)
        if not concept_payload:
            continue

        for fact in _iter_fact_entries(concept_payload):
            if not _matches_period(fact, fiscal_year, fiscal_period):
                continue

            dimensions = fact.get("dimensions") or fact.get("dim") or {}
            if not isinstance(dimensions, dict) or not dimensions:
                continue

            for segment_axis, segment_member in dimensions.items():
                if allowed_axes and segment_axis not in allowed_axes:
                    continue
                segment_revenues.append(
                    build_segment_revenue(
                        segment_axis=str(segment_axis),
                        segment_member=str(segment_member),
                        value=float(fact.get("val", 0.0)),
                        fiscal_year=int(fact.get("fy", fiscal_year or 0) or 0),
                        fiscal_period=str(fact.get("fp", fiscal_period or "")),
                    )
                )

    return segment_revenues


def group_segment_revenues_by_period(segments: Iterable[SegmentRevenue]) -> dict[tuple[int, str], list[SegmentRevenue]]:
    grouped: dict[tuple[int, str], list[SegmentRevenue]] = defaultdict(list)
    for segment in segments:
        grouped[(segment.fiscal_year, segment.fiscal_period)].append(segment)
    return dict(grouped)


def _concepts(company_facts: dict[str, Any], taxonomy: str) -> dict[str, dict[str, Any]]:
    facts = company_facts.get("facts", {})
    taxonomy_facts = facts.get(taxonomy, {}) if isinstance(facts, dict) else {}
    return taxonomy_facts if isinstance(taxonomy_facts, dict) else {}


def _iter_fact_entries(concept_payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    units = concept_payload.get("units", {}) if isinstance(concept_payload, dict) else {}
    if not isinstance(units, dict):
        return []

    for unit_facts in units.values():
        if isinstance(unit_facts, list):
            for fact in unit_facts:
                if isinstance(fact, dict):
                    yield fact


def _matches_period(fact: dict[str, Any], fiscal_year: int | None, fiscal_period: str | None) -> bool:
    if fiscal_year is not None and fact.get("fy") not in (None, fiscal_year):
        return False
    if fiscal_period is not None and fact.get("fp") not in (None, fiscal_period):
        return False
    return True
