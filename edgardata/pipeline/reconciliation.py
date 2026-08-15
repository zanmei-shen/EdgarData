"""Reconciliation rules for segment and top-level revenue."""

from __future__ import annotations

from edgardata.models.schema import IncomeStatementPayload, ReconciliationResult


def reconcile_revenue(payload: IncomeStatementPayload) -> ReconciliationResult:
    total_revenue = float(payload.total_revenue or 0.0)
    segment_sum = float(sum(segment.value for segment in payload.segments))
    if total_revenue == 0.0:
        error_pct = 0.0 if segment_sum == 0.0 else 100.0
    else:
        error_pct = abs(total_revenue - segment_sum) / total_revenue * 100.0

    if error_pct < 5.0:
        status = "RECONCILED_EXACT"
        residual_value = 0.0
        residual_label = None
    elif error_pct <= 15.0:
        status = "RECONCILED_WITH_RESIDUAL"
        residual_value = total_revenue - segment_sum
        residual_label = "Corporate / Unallocated Revenue"
    else:
        status = "NEEDS_REVIEW"
        residual_value = total_revenue - segment_sum
        residual_label = None

    return ReconciliationResult(
        ticker=payload.ticker,
        fiscal_year=payload.fiscal_year,
        fiscal_period=payload.fiscal_period,
        total_revenue=total_revenue,
        segment_revenue_sum=segment_sum,
        reconciliation_error_pct=error_pct,
        status=status,
        residual_value=residual_value,
        residual_label=residual_label,
    )
