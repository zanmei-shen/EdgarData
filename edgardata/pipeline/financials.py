"""Financial statement derivation and reconciliation helpers."""

from __future__ import annotations

from typing import Any

from edgardata.models.schema import ExpenseDetail
from edgardata.parser.taxonomy_mapper import resolve_metric_fact


def resolve_operating_expenses(
    company_facts: dict[str, Any],
    fiscal_year: int,
    fiscal_period: str,
    period_start: str | None,
    period_end: str | None,
    reported_operating_expenses: Any = None,
    total_revenue: float | None = None,
    cost_of_revenue: float | None = None,
    operating_income: float | None = None,
) -> tuple[float | None, list[ExpenseDetail]]:
    component_specs = (
        ("R&D", "research_and_development"),
        ("Sales & marketing", "sales_and_marketing"),
        ("General & admin", "general_and_administrative"),
    )
    details: list[ExpenseDetail] = []
    for expense_label, metric_name in component_specs:
        resolved = resolve_metric_fact(
            company_facts,
            metric_name,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            period_start=period_start,
            period_end=period_end,
        )
        if resolved is not None:
            details.append(
                ExpenseDetail(
                    expense_label=expense_label,
                    value=resolved.value,
                    fiscal_year=resolved.fiscal_year or fiscal_year,
                    fiscal_period=resolved.fiscal_period or fiscal_period,
                )
            )

    if total_revenue is not None and cost_of_revenue is not None and operating_income is not None:
        derived_total = total_revenue - cost_of_revenue - operating_income
        component_total = sum(detail.value for detail in details)
        tolerance = max(1.0, abs(derived_total) * 0.000001)
        if details and abs(component_total - derived_total) <= tolerance:
            return derived_total, details
        return derived_total, []
    if details:
        return sum(detail.value for detail in details), details
    if reported_operating_expenses is not None:
        return reported_operating_expenses.value, []
    return None, []