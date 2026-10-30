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
    income_before_tax = payload.income_before_tax
    other_income_expense = payload.other_income_expense
    bridge_other_income_expense = (
        income_before_tax - operating_profit
        if income_before_tax is not None
        else other_income_expense
    )

    nodes = [
        *[
            SankeyNode(
                id=_segment_node_id(segment.segment_label),
                label=segment.segment_label,
                stage=1 if segment.parent_id else 0,
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
    ]

    bridge_links: list[SankeyLink] = []
    if income_before_tax is None:
        nodes.append(SankeyNode(id="net_profit", label="Net profit", stage=5, kind="final", value=net_profit))
        bridge_links.append(SankeyLink(source="operating_profit", target="net_profit", value=net_profit))
    else:
        pretax = float(income_before_tax)
        adjustment = pretax - operating_profit
        nodes.append(SankeyNode(id="income_before_tax", label="Income before tax", stage=6, kind="subtotal", value=pretax))
        nodes.append(SankeyNode(id="net_profit", label="Net profit", stage=8, kind="final", value=net_profit))
        if adjustment >= 0:
            nodes.append(SankeyNode(id="other_income", label="Other income", stage=5, kind="income", value=adjustment))
            bridge_links.extend(
                [
                    SankeyLink(source="operating_profit", target="income_before_tax", value=operating_profit),
                    SankeyLink(source="other_income", target="income_before_tax", value=adjustment),
                ]
            )
        else:
            nodes.append(SankeyNode(id="other_expense", label="Other expense", stage=5, kind="expense", value=abs(adjustment)))
            bridge_links.extend(
                [
                    SankeyLink(source="operating_profit", target="income_before_tax", value=pretax),
                    SankeyLink(source="operating_profit", target="other_expense", value=abs(adjustment)),
                ]
            )

        tax_adjustment = pretax - net_profit
        if tax_adjustment >= 0:
            nodes.append(SankeyNode(id="income_tax", label="Income tax", stage=7, kind="expense", value=tax_adjustment))
            bridge_links.extend(
                [
                    SankeyLink(source="income_before_tax", target="net_profit", value=net_profit),
                    SankeyLink(source="income_before_tax", target="income_tax", value=tax_adjustment),
                ]
            )
        else:
            nodes.append(SankeyNode(id="income_tax_benefit", label="Income tax benefit", stage=7, kind="income", value=abs(tax_adjustment)))
            bridge_links.extend(
                [
                    SankeyLink(source="income_before_tax", target="net_profit", value=pretax),
                    SankeyLink(source="income_tax_benefit", target="net_profit", value=abs(tax_adjustment)),
                ]
            )

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
            target=_resolve_segment_reference(segment.parent_id, nodes) if segment.parent_id else "revenue",
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
    links.extend(bridge_links)

    if income_before_tax is None and net_profit != operating_profit:
        below_operating_adjustment = net_profit - operating_profit
        adjustment_id = "below_operating_adjustment"
        adjustment_label = "Below-operating adjustment"
        nodes.append(
            SankeyNode(
                id=adjustment_id,
                label=adjustment_label,
                stage=5,
                kind="income" if below_operating_adjustment >= 0 else "expense",
                value=abs(below_operating_adjustment),
            )
        )
        links = [
            link
            for link in links
            if not (link.source == "operating_profit" and link.target == "net_profit")
        ]
        if below_operating_adjustment >= 0:
            links.extend(
                [
                    SankeyLink(source="operating_profit", target="net_profit", value=operating_profit),
                    SankeyLink(source=adjustment_id, target="net_profit", value=below_operating_adjustment),
                ]
            )
        else:
            links.extend(
                [
                    SankeyLink(source="operating_profit", target="net_profit", value=net_profit),
                    SankeyLink(source="operating_profit", target=adjustment_id, value=abs(below_operating_adjustment)),
                ]
            )

    top_level = {
        "total_revenue": total_revenue,
        "cost_of_revenue": cost_of_revenue,
        "gross_profit": gross_profit,
        "operating_expenses": operating_expenses,
        "operating_profit": operating_profit,
        "income_before_tax": income_before_tax,
        "other_income_expense": bridge_other_income_expense,
        "income_tax_expense": payload.income_tax_expense,
        "net_profit": net_profit,
    }

    node_labels = {node.id: node.label for node in nodes}
    segment_breakdown = [
        {
            "source": segment.segment_label,
            "target": node_labels.get(_resolve_segment_reference(segment.parent_id, nodes), "Revenue") if segment.parent_id else "Revenue",
            "value": float(segment.value),
        }
        for segment in payload.segments
    ]

    if any(link.value < 0 for link in links):
        raise ValueError("Sankey links must have non-negative values")

    return SankeyGraph(
        ticker=payload.ticker,
        period=_format_period_label(payload.fiscal_period, payload.fiscal_year),
        nodes=nodes,
        links=links,
        top_level=top_level,
        segment_breakdown=segment_breakdown,
    )


def _segment_node_id(label: str) -> str:
    return "segment_" + _slugify(label)


def _resolve_segment_reference(reference: str, nodes: list[SankeyNode]) -> str:
    node_ids = {node.id for node in nodes}
    if reference in node_ids:
        return reference

    reference_key = _compact_label(reference.removeprefix("segment_"))
    for node in nodes:
        if node.kind == "segment" and _compact_label(node.label) == reference_key:
            return node.id
    raise ValueError(f"Unknown segment parent: {reference}")


def _expense_node_id(label: str) -> str:
    return "expense_" + _slugify(label)


def _format_period_label(fiscal_period: str, fiscal_year: int) -> str:
    normalized_period = fiscal_period.upper().strip()
    if normalized_period not in {"FY", "Q1", "Q2", "Q3", "Q4"}:
        raise ValueError(f"Unsupported fiscal period: {fiscal_period!r}")
    if normalized_period.startswith("Q"):
        return f"{normalized_period}FY{fiscal_year}"
    return f"{normalized_period}{fiscal_year}"


def _slugify(label: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", label).strip("_")
    return slug.lower()


def _compact_label(label: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "", label).lower()
