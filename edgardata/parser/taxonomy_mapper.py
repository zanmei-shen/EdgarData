"""US-GAAP taxonomy fallback resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable


FALLBACK_CONCEPTS: dict[str, tuple[str, ...]] = {
    "total_revenue": (
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
    ),
    "cost_of_revenue": (
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
    ),
    "operating_expenses": (
        "OperatingExpenses",
        "OperatingCostsAndExpenses",
        "CostsAndExpenses",
        "OperatingCosts",
        "SellingGeneralAndAdministrativeExpense",
    ),

    "operating_income": (
        "OperatingIncomeLoss",
    ),
    "research_and_development": (
        "ResearchAndDevelopmentExpense",
    ),
    "sales_and_marketing": (
        "SellingAndMarketingExpense",
    ),
    "general_and_administrative": (
        "GeneralAndAdministrativeExpense",
    ),
    "income_before_tax": (
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ),
    "income_tax_expense": (
        "IncomeTaxExpenseBenefit",
    ),
    "other_income_expense": (
        "OtherNonoperatingIncomeExpense",
        "NonoperatingIncomeExpense",
    ),
    "net_profit": (
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ),
}


@dataclass(frozen=True, slots=True)
class ResolvedConcept:
    metric_name: str
    concept: str
    value: float
    unit: str
    period_end: str
    fiscal_year: int
    fiscal_period: str
    form: str
    period_start: str = ""
    accession: str = ""


def get_fallback_concepts(metric_name: str) -> tuple[str, ...]:
    try:
        return FALLBACK_CONCEPTS[metric_name]
    except KeyError as exc:
        raise KeyError(f"Unknown metric name: {metric_name}") from exc


def resolve_metric_fact(
    company_facts: dict[str, Any],
    metric_name: str,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    preferred_forms: tuple[str, ...] = ("10-K", "10-Q"),
    taxonomy: str = "us-gaap",
) -> ResolvedConcept | None:
    concepts = _concepts_for_metric(company_facts, metric_name, taxonomy)
    if not concepts:
        return None

    for concept in get_fallback_concepts(metric_name):
        concept_payload = concepts.get(concept)
        if not concept_payload:
            continue

        facts = list(_iter_fact_entries(concept_payload))
        if not facts:
            continue

        selected_fact = _select_best_fact(
            facts=facts,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            period_start=period_start,
            period_end=period_end,
            preferred_forms=preferred_forms,
        )
        if selected_fact is not None:
            return ResolvedConcept(
                metric_name=metric_name,
                concept=concept,
                value=float(selected_fact["val"]),
                unit=str(selected_fact.get("unit", "")),
                period_end=str(selected_fact.get("end", "")),
                fiscal_year=int(selected_fact.get("fy", 0) or 0),
                fiscal_period=str(selected_fact.get("fp", "")),
                form=str(selected_fact.get("form", "")),
                period_start=str(selected_fact.get("start", "")),
                accession=str(selected_fact.get("accn", "")),
            )

    return None


def _concepts_for_metric(
    company_facts: dict[str, Any],
    metric_name: str,
    taxonomy: str,
) -> dict[str, dict[str, Any]]:
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


def _select_best_fact(
    facts: Iterable[dict[str, Any]],
    fiscal_year: int | None,
    fiscal_period: str | None,
    period_start: str | None,
    period_end: str | None,
    preferred_forms: tuple[str, ...],
) -> dict[str, Any] | None:
    candidates = [
        fact
        for fact in facts
        if _matches_period(fact, fiscal_year, fiscal_period, period_start, period_end)
    ]
    if not candidates:
        return None

    def sort_key(fact: dict[str, Any]) -> tuple[int, int, str, str]:
        form_rank = 1 if fact.get("form") in preferred_forms else 0
        return (
            form_rank,
            0 if fact.get("fy") == fiscal_year and (fiscal_period is None or fact.get("fp") == fiscal_period) else 1,
            str(fact.get("filed", "")),
            str(fact.get("end", "")),
        )

    return max(candidates, key=sort_key)


def _matches_period(
    fact: dict[str, Any],
    fiscal_year: int | None,
    fiscal_period: str | None,
    period_start: str | None,
    period_end: str | None,
) -> bool:
    if fiscal_year is not None and fact.get("fy") != fiscal_year:
        return False
    if fiscal_period is not None and fact.get("fp") != fiscal_period:
        return False
    if period_start is not None and fact.get("start") != period_start:
        return False
    if period_end is not None and fact.get("end") != period_end:
        return False
    if fiscal_period in {"Q1", "Q2", "Q3", "Q4"} and not _is_quarter_duration(fact):
        return False
    return True


def _is_quarter_duration(fact: dict[str, Any]) -> bool:
    start = fact.get("start")
    end = fact.get("end")
    if not start or not end:
        return False
    try:
        duration_days = (date.fromisoformat(str(end)) - date.fromisoformat(str(start))).days + 1
    except ValueError:
        return False
    return 70 <= duration_days <= 110
