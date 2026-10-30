"""Segment dimension parsing utilities."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from itertools import combinations
from typing import Any, Iterable
import xml.etree.ElementTree as ET

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

            dimensions = _segment_dimensions(fact)
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


def extract_filing_segment_revenues(
    xml_bytes: bytes,
    period_start: str,
    period_end: str,
    fiscal_year: int,
    fiscal_period: str,
    allowed_axes: tuple[str, ...] = ("StatementBusinessSegmentsAxis", "ProductOrServiceAxis"),
) -> list[SegmentRevenue]:
    root = ET.fromstring(xml_bytes)
    contexts = {
        context.attrib.get("id", ""): _xbrl_context_period(context)
        for context in root.iter()
        if _local_name(context.tag) == "context"
    }
    candidates_by_axis: dict[str, list[tuple[str, float]]] = defaultdict(list)
    revenue_concepts = set(FALLBACK_CONCEPTS["total_revenue"])

    for fact in root:
        context_ref = fact.attrib.get("contextRef")
        if not context_ref or context_ref not in contexts:
            continue
        if _local_name(fact.tag) not in revenue_concepts:
            continue
        start, end, dimensions = contexts[context_ref]
        if start != period_start or end != period_end or not dimensions:
            continue
        for axis, member in dimensions.items():
            if _local_name(axis) not in allowed_axes:
                continue
            value = _numeric_fact_value(fact)
            if value is None:
                continue
            candidates_by_axis[axis].append((member, value))

    selected_axis = _select_segment_axis(candidates_by_axis, allowed_axes)
    results: list[SegmentRevenue] = []
    seen: set[tuple[str, float]] = set()
    for member, value in _remove_aggregate_members(candidates_by_axis.get(selected_axis, [])):
        key = (member, value)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            build_segment_revenue(
                segment_axis=selected_axis,
                segment_member=member,
                value=value,
                fiscal_year=fiscal_year,
                fiscal_period=fiscal_period,
            )
        )
    return results


def _select_segment_axis(candidates_by_axis: dict[str, list[tuple[str, float]]], allowed_axes: tuple[str, ...]) -> str:
    for preferred_axis in ("ProductOrServiceAxis", "StatementBusinessSegmentsAxis"):
        for axis in candidates_by_axis:
            if _local_name(axis) == preferred_axis and _local_name(axis) in allowed_axes:
                return axis
    return next(iter(candidates_by_axis), "")


def _remove_aggregate_members(candidates: list[tuple[str, float]]) -> list[tuple[str, float]]:
    remaining = list(candidates)
    changed = True
    while changed and len(remaining) > 1:
        changed = False
        for index, (_, value) in sorted(enumerate(remaining), key=lambda item: item[1][1], reverse=True):
            others = [other_value for other_index, (_, other_value) in enumerate(remaining) if other_index != index]
            if _has_subset_sum(others, value):
                remaining.pop(index)
                changed = True
                break
    return remaining


def _has_subset_sum(values: list[float], target: float) -> bool:
    tolerance = max(1.0, abs(target) * 0.000001)
    for subset_size in range(2, len(values) + 1):
        for subset in combinations(values, subset_size):
            if abs(sum(subset) - target) <= tolerance:
                return True
    return False


def _xbrl_context_period(context: ET.Element) -> tuple[str, str, dict[str, str]]:
    start = ""
    end = ""
    dimensions: dict[str, str] = {}
    for element in context.iter():
        name = _local_name(element.tag)
        if name == "startDate":
            start = element.text or ""
        elif name == "endDate":
            end = element.text or ""
        elif name == "explicitMember":
            axis = element.attrib.get("dimension", "")
            if axis and element.text:
                dimensions[axis] = element.text
    return start, end, dimensions


def _numeric_fact_value(fact: ET.Element) -> float | None:
    try:
        return float((fact.text or "").strip())
    except ValueError:
        return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":", 1)[-1]


def _segment_dimensions(fact: dict[str, Any]) -> dict[str, str]:
    dimensions = fact.get("dimensions") or fact.get("dim")
    if isinstance(dimensions, dict):
        return {str(axis): str(member) for axis, member in dimensions.items()}

    segment = fact.get("segment")
    if isinstance(segment, dict):
        axis = segment.get("dimension")
        member = segment.get("value")
        if axis and member:
            return {str(axis): str(member)}

    return {}


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
