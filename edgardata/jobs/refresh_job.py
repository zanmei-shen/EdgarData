"""Orchestration entrypoint for scheduled EDGAR refreshes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from edgardata.exports.sankey_exporter import export_to_sankey_json
from edgardata.models.schema import IncomeStatementPayload
from edgardata.pipeline.reconciliation import reconcile_revenue
from edgardata.storage.persistence import persist_partitioned_json, payload_to_record


def materialize_income_statement(
    payload: IncomeStatementPayload,
    output_dir: str | Path,
) -> dict[str, Any]:
    reconciliation = reconcile_revenue(payload)
    sankey_json = export_to_sankey_json(payload)
    persisted_path = persist_partitioned_json(payload, output_dir, reconciliation)

    return {
        "payload": payload_to_record(payload, reconciliation),
        "reconciliation": reconciliation,
        "sankey_json": sankey_json,
        "persisted_path": persisted_path,
    }
