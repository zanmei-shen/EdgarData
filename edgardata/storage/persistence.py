"""Persistence helpers for normalized EDGAR payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from edgardata.models.schema import IncomeStatementPayload, ReconciliationResult

try:  # pragma: no cover - optional dependency
    import duckdb  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    duckdb = None


class PersistenceError(RuntimeError):
    pass


def payload_to_record(payload: IncomeStatementPayload, reconciliation: ReconciliationResult | None = None) -> dict[str, Any]:
    record = payload.model_dump()
    if reconciliation is not None:
        record["reconciliation"] = reconciliation.model_dump()
    return record


def persist_partitioned_json(
    payload: IncomeStatementPayload,
    base_dir: str | Path,
    reconciliation: ReconciliationResult | None = None,
) -> Path:
    base_path = Path(base_dir)
    target_dir = base_path / f"year={payload.fiscal_year}" / f"ticker={payload.ticker}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "data.json"
    target_file.write_text(json.dumps(payload_to_record(payload, reconciliation), indent=2), encoding="utf-8")
    return target_file


def persist_to_duckdb(
    payload: IncomeStatementPayload,
    database_path: str | Path,
    table_name: str = "sec_facts",
    reconciliation: ReconciliationResult | None = None,
) -> None:
    if duckdb is None:
        raise PersistenceError("duckdb is not installed")

    record = payload_to_record(payload, reconciliation)
    db_path = str(database_path)
    con = duckdb.connect(db_path)
    try:
        con.execute(
            f"""
            create table if not exists {table_name} (
                ticker varchar,
                cik varchar,
                fiscal_year integer,
                fiscal_period varchar,
                payload_json varchar
            )
            """
        )
        con.execute(
            f"insert into {table_name} values (?, ?, ?, ?, ?)",
            [
                payload.ticker,
                payload.cik,
                payload.fiscal_year,
                payload.fiscal_period,
                json.dumps(record),
            ],
        )
    finally:
        con.close()
