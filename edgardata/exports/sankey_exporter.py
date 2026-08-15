"""Convert reconciled payloads into Sankey-ready JSON."""

from __future__ import annotations

import re

from edgardata.models.schema import IncomeStatementPayload, SankeyGraph, SankeyLink, SankeyNode


def export_to_sankey_json(payload: IncomeStatementPayload) -> dict[str, object]:
    return build_tencent_style_sankey_graph(payload).model_dump()


def build_tencent_style_sankey_graph(payload: IncomeStatementPayload) -> SankeyGraph:
    total_revenue = float(payload.total_revenue or 0.0)
    cost_of_revenue = float(payload.cost_of_revenue or 0.0)
    operating_expenses = float(payload.operating_expenses or 0.0)
    gross_profit = total_revenue - cost_of_revenue
    operating_profit = gross_profit - operating_expenses
    net_profit = float(payload.net_profit or 0.0)

    nodes = [
        SankeyNode(id="segments", label="Revenue segments", stage=0, kind="group", value=total_revenue),
        *[
            SankeyNode(
                id=_segment_node_id(segment.segment_label),
                label=segment.segment_label,
                stage=0,
                kind="segment",
                value=segment.value,
            )
            for segment in payload.segments
        ],
        SankeyNode(id="revenue", label="Revenue", stage=1, kind="subtotal", value=total_revenue),
        SankeyNode(id="cost_of_revenue", label="Cost of revenue", stage=2, kind="expense", value=cost_of_revenue),
        SankeyNode(id="gross_profit", label="Gross profit", stage=2, kind="subtotal", value=gross_profit),
        SankeyNode(id="operating_expenses", label="Operating expenses", stage=3, kind="expense", value=operating_expenses),
        SankeyNode(id="operating_profit", label="Operating profit", stage=4, kind="subtotal", value=operating_profit),
        SankeyNode(id="net_profit", label="Net profit", stage=5, kind="final", value=net_profit),
    ]

    expense_detail_nodes = [
        SankeyNode(
            id=_expense_node_id(expense.expense_label),
            label=expense.expense_label,
            stage=4,
            kind="expense_detail",
            value=float(expense.value),
        )
        for expense in payload.operating_expense_details
    ]
    nodes.extend(expense_detail_nodes)

    links: list[SankeyLink] = []
    links.extend(
        SankeyLink(
            source=_segment_node_id(segment.segment_label),
            target="revenue",
            value=float(segment.value),
        )
        for segment in payload.segments
    )
    links.append(SankeyLink(source="revenue", target="gross_profit", value=gross_profit))
    links.append(SankeyLink(source="revenue", target="cost_of_revenue", value=cost_of_revenue))
    links.append(SankeyLink(source="gross_profit", target="operating_profit", value=operating_profit))
    links.append(SankeyLink(source="gross_profit", target="operating_expenses", value=operating_expenses))
    links.extend(
        SankeyLink(
            source="operating_expenses",
            target=_expense_node_id(expense.expense_label),
            value=float(expense.value),
        )
        for expense in payload.operating_expense_details
    )
    links.append(SankeyLink(source="operating_profit", target="net_profit", value=net_profit))

    top_level = {
        "total_revenue": total_revenue,
        "cost_of_revenue": cost_of_revenue,
        "gross_profit": gross_profit,
        "operating_expenses": operating_expenses,
        "operating_profit": operating_profit,
        "net_profit": net_profit,
    }

    segment_breakdown = [
        {
            "source": segment.segment_label,
            "target": "Revenue",
            "value": float(segment.value),
        }
        for segment in payload.segments
    ]

    return SankeyGraph(
        ticker=payload.ticker,
        period=f"FY{payload.fiscal_year}",
        nodes=nodes,
        links=links,
        top_level=top_level,
        segment_breakdown=segment_breakdown,
    )


def _segment_node_id(label: str) -> str:
    return "segment_" + _slugify(label)


def _expense_node_id(label: str) -> str:
    return "expense_" + _slugify(label)


def _slugify(label: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", label).strip("_")
    return slug.lower()
