"""Canonical schemas for EDGAR extraction payloads."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FinancialMetric(BaseModel):
    concept: str
    value: float
    unit: str
    period_start: str
    period_end: str
    fiscal_year: int
    fiscal_period: str
    form: str


class SegmentRevenue(BaseModel):
    segment_axis: str
    segment_member: str
    segment_label: str
    value: float
    fiscal_year: int
    fiscal_period: str


class ExpenseDetail(BaseModel):
    expense_label: str
    value: float
    fiscal_year: int
    fiscal_period: str


class IncomeStatementPayload(BaseModel):
    ticker: str
    cik: str
    fiscal_year: int
    fiscal_period: str
    total_revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    operating_expenses: Optional[float] = None
    net_profit: Optional[float] = None
    segments: list[SegmentRevenue] = Field(default_factory=list)
    operating_expense_details: list[ExpenseDetail] = Field(default_factory=list)


class ReconciliationResult(BaseModel):
    ticker: str
    fiscal_year: int
    fiscal_period: str
    total_revenue: float
    segment_revenue_sum: float
    reconciliation_error_pct: float
    status: str
    residual_value: float = 0.0
    residual_label: Optional[str] = None


class SankeyNode(BaseModel):
    id: str
    label: str
    stage: int
    kind: str
    value: float = 0.0
    color: Optional[str] = None


class SankeyLink(BaseModel):
    source: str
    target: str
    value: float
    kind: str = "flow"


class SankeyGraph(BaseModel):
    ticker: str
    period: str
    currency: str = "USD"
    nodes: list[SankeyNode] = Field(default_factory=list)
    links: list[SankeyLink] = Field(default_factory=list)
    top_level: dict[str, Optional[float]] = Field(default_factory=dict)
    segment_breakdown: list[dict[str, object]] = Field(default_factory=list)
