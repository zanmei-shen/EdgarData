"""Convert reconciled payloads into Sankey-ready JSON."""

from __future__ import annotations

from edgardata.models.schema import IncomeStatementPayload


def export_to_sankey_json(payload: IncomeStatementPayload) -> dict[str, object]:
    return {
        "ticker": payload.ticker,
        "period": f"FY{payload.fiscal_year}",
        "currency": "USD",
        "top_level": {
            "total_revenue": payload.total_revenue,
            "cost_of_revenue": payload.cost_of_revenue,
            "operating_expenses": payload.operating_expenses,
            "net_profit": payload.net_profit,
        },
        "segment_breakdown": [
            {
                "source": segment.segment_label,
                "target": "Revenue",
                "value": segment.value,
            }
            for segment in payload.segments
        ],
    }
