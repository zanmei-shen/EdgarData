"""Segment dimension parsing utilities."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from itertools import combinations
from typing import Any, Iterable
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from edgardata.models.schema import SegmentRevenue
from edgardata.parser.taxonomy_mapper import FALLBACK_CONCEPTS


def normalize_segment_label(segment_member: str) -> str:
    local_name = segment_member.split(":", 1)[-1].removesuffix("Member")
    if local_name == "IPhone":
        return "iPhone"
    google_labels = {
        "GoogleServices": "Google Services",
        "GoogleCloud": "Google Cloud",
        "AllOtherSegments": "Other",
    }
    if local_name in google_labels:
        return google_labels[local_name]
    if "_" in local_name:
        return local_name.replace("_", " ").strip()
    return local_name


def build_segment_revenue(
    segment_axis: str,
    segment_member: str,
    value: float,
    fiscal_year: int,
    fiscal_period: str,
    parent_id: str | None = None,
    display_label: str | None = None,
) -> SegmentRevenue:
    return SegmentRevenue(
        segment_axis=segment_axis,
        segment_member=segment_member,
        segment_label=display_label or normalize_segment_label(segment_member),
        value=value,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        parent_id=parent_id,
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
    preferred = (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenues",
    )
    facts_by_concept = _concepts(company_facts, taxonomy)
    # Pick the first concept that exists in company_facts
    target_concepts = [c for c in preferred if c in facts_by_concept][:1]

    # If none found, fall back to original list (rare)
    if not target_concepts:
        target_concepts = concepts or FALLBACK_CONCEPTS["total_revenue"][:1]
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
    undimensioned_values: list[float] = []

    for fact in root:
        context_ref = fact.attrib.get("contextRef")
        if not context_ref or context_ref not in contexts:
            continue
        if _local_name(fact.tag) not in revenue_concepts:
            continue
        start, end, dimensions = contexts[context_ref]
        if start != period_start or end != period_end:
            continue
        value = _numeric_fact_value(fact)
        if value is None:
            continue
        if not dimensions:
            # Undimensioned revenue fact for the period: the filing's own
            # reported total. Used below to pick the axis that reconciles.
            undimensioned_values.append(value)
            continue
        if len(dimensions) != 1:
            # Multi-dimensional fact (e.g. a segment x product intersection
            # cell): its value is only a slice of the member total, so it
            # must not be attributed to any single axis. Attributing it
            # would duplicate members (GOOG: four "GoogleServices" entries)
            # and could make the aggregate filter delete the true total.
            continue
        for axis, member in dimensions.items():
            if _local_name(axis) not in allowed_axes:
                continue
            candidates_by_axis[axis].append((member, value))

    filing_total = _most_common(undimensioned_values)

    # Score every candidate axis by how well its (de-duplicated,
    # de-aggregated) members reconcile to the filing's reported total.
    # This rejects axes that mix parent aggregates with their children,
    # e.g. srt:ProductOrServiceAxis in MSFT 10-Qs, where Product ($16.5B)
    # and ServiceOther ($64.8B) double-count the 10 leaf members and the
    # subset-sum aggregate filter cannot remove them (filing rounding of
    # ~$2M exceeds its 1e-6 relative tolerance).
    axis_results: dict[str, list[SegmentRevenue]] = {}
    scored: list[tuple[float, int, str]] = []
    for axis in candidates_by_axis:
        results: list[SegmentRevenue] = []
        seen: set[tuple[str, float]] = set()
        for member, value in _remove_aggregate_members(candidates_by_axis[axis]):
            key = (member, value)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                build_segment_revenue(
                    segment_axis=axis,
                    segment_member=member,
                    value=value,
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                )
            )
        axis_results[axis] = results
        segment_sum = sum(item.value for item in results)
        if filing_total:
            reconciliation_error = abs(segment_sum - filing_total) / abs(filing_total)
        else:
            # No reported total to check against: keep the old behavior and
            # fall through to the hard-coded axis preference order.
            reconciliation_error = float("inf")
        scored.append((reconciliation_error, _axis_preference_rank(axis), axis))

    if not scored:
        return []
    scored.sort(key=lambda item: (item[0], item[1]))
    selected_axis = scored[0][2]
    selected_results = axis_results[selected_axis]
    if filing_total is not None:
        segment_sum = sum(segment.value for segment in selected_results)
        residual = filing_total - segment_sum
        tolerance = max(1.0, abs(filing_total) * 0.000001)
        if residual > tolerance:
            other_segment = next(
                (segment for segment in selected_results if segment.segment_label == "Other"),
                None,
            )
            if other_segment is not None:
                other_segment.value += residual
            else:
                selected_results.append(
                    build_segment_revenue(
                        segment_axis=selected_axis,
                        segment_member="ResidualRevenueMember",
                        value=residual,
                        fiscal_year=fiscal_year or 0,
                        fiscal_period=fiscal_period or "",
                        display_label="Other",
                    )
                )
    return selected_results


def extract_filing_product_revenues(
    html_bytes: bytes,
    xml_bytes: bytes,
    period_start: str,
    period_end: str,
    fiscal_year: int,
    fiscal_period: str,
) -> list[SegmentRevenue]:
    """Extract Google product revenue rows from Inline XBRL filing tables."""
    contexts = _filing_contexts(xml_bytes)
    parser = _InlineRevenueTableParser()
    parser.feed(html_bytes.decode("utf-8", errors="ignore"))

    label_map = {
        "google search & other": ("GoogleSearchOtherMember", "Google Search & other"),
        "youtube ads": ("YouTubeAdsMember", "YouTube ads"),
        "google network": ("GoogleNetworkMember", "Google Network"),
        "google subscriptions, platforms, and devices": (
            "GoogleSubscriptionsPlatformsDevicesMember",
            "Google subscriptions, platforms, and devices",
        ),
    }
    segments: list[SegmentRevenue] = []
    for row_label, facts in parser.rows:
        normalized_label = " ".join(row_label.split()).lower()
        matched = next(
            (entry for label, entry in label_map.items() if normalized_label.startswith(label)),
            None,
        )
        if matched is None:
            continue
        member, label = matched
        for fact in facts:
            context = contexts.get(fact.get("contextref", ""))
            if context is None or context[:2] != (period_start, period_end):
                continue
            if _local_name(fact.get("name", "")) not in FALLBACK_CONCEPTS["total_revenue"]:
                continue
            value = _inline_fact_value(fact)
            if value is None:
                continue
            segments.append(
                build_segment_revenue(
                    segment_axis="goog:GoogleServicesProductAxis",
                    segment_member=f"goog:{member}",
                    value=value,
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    parent_id="segment_googleservices",
                    display_label=label,
                )
            )
            break
    return segments


_AXIS_PREFERENCE = ("ProductOrServiceAxis", "StatementBusinessSegmentsAxis")


def _axis_preference_rank(axis: str) -> int:
    """Lower is better. Used only to break ties between equally reconciling axes."""
    try:
        return _AXIS_PREFERENCE.index(_local_name(axis))
    except ValueError:
        return len(_AXIS_PREFERENCE)


def _most_common(values: list[float]) -> float | None:
    """Most frequently reported value (filings repeat the total across notes)."""
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


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


def _filing_contexts(xml_bytes: bytes) -> dict[str, tuple[str, str, dict[str, str]]]:
    root = ET.fromstring(xml_bytes)
    return {
        context.attrib.get("id", ""): _xbrl_context_period(context)
        for context in root.iter()
        if _local_name(context.tag) == "context"
    }


class _InlineRevenueTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_row = False
        self._row_text: list[str] = []
        self._row_facts: list[dict[str, str]] = []
        self._active_fact: dict[str, str] | None = None
        self.rows: list[tuple[str, list[dict[str, str]]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "tr":
            self._in_row = True
            self._row_text = []
            self._row_facts = []
        if self._in_row and normalized_tag == "ix:nonfraction":
            fact = {key.lower(): value or "" for key, value in attrs}
            fact["text"] = ""
            self._row_facts.append(fact)
            self._active_fact = fact

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if self._in_row and normalized_tag == "ix:nonfraction":
            self._active_fact = None
        elif self._in_row and normalized_tag == "tr":
            self.rows.append((" ".join(self._row_text), self._row_facts))
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if not self._in_row:
            return
        self._row_text.append(data)
        if self._active_fact is not None:
            self._active_fact["text"] += data


def _inline_fact_value(fact: dict[str, str]) -> float | None:
    raw_value = fact.get("text", "").replace(",", "").strip()
    try:
        value = float(raw_value)
    except ValueError:
        return None
    value *= 10 ** int(fact.get("scale", "0") or 0)
    if fact.get("sign") == "-":
        value = -value
    return value


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
