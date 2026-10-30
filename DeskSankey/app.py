from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from edgardata.exports.sankey_exporter import build_tencent_style_sankey_graph
from edgardata.ingestion.edgar_client import EdgarIngestionEngine
from edgardata.models.schema import ExpenseDetail, IncomeStatementPayload, SegmentRevenue
from edgardata.parser.segment_parser import extract_filing_segment_revenues
from edgardata.parser.taxonomy_mapper import resolve_metric_fact
from edgardata.pipeline.reconciliation import reconcile_revenue

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
OUTPUT_PATH = DATA_DIR / "sankey_data.json"

DEFAULT_KIND_COLORS = {
    "segment": "#1f4e79",
    "group": "#9aa5b1",
    "subtotal": "#4f8cc9",
    "expense": "#b04f40",
    "expense_detail": "#d36b5e",
    "final": "#6ea84f",
}

st.set_page_config(page_title="DeskSankey", layout="wide")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 1.5rem;
            max-width: 1480px;
        }
        .desk-hero {
            padding: 1rem 1.25rem;
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(37, 99, 235, 0.92));
            color: white;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.20);
            margin-bottom: 1rem;
        }
        .desk-hero h1 {
            margin: 0;
            font-size: 2rem;
            line-height: 1.1;
        }
        .desk-hero p {
            margin: 0.35rem 0 0 0;
            opacity: 0.9;
            font-size: 0.98rem;
        }
        .desk-panel {
            padding: 0.75rem 0.9rem;
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 14px;
            background: rgba(248, 250, 252, 0.94);
        }
        .desk-small {
            font-size: 0.92rem;
            color: #475569;
        }
    </style>
    <div class="desk-hero">
        <h1>DeskSankey</h1>
        <p>Enter a ticker, generate a layered income flow graph, edit the numbers, and download the JSON.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("Generate and edit a Tencent-style Sankey diagram from normalized EDGAR income data.")

USER_AGENT = os.getenv("EDGAR_USER_AGENT", "DeskSankey desk@yourcompany.com")


@st.cache_data
def load_sample_payload(ticker: str, fiscal_year: int, fiscal_period: str) -> IncomeStatementPayload:
    ticker = ticker.upper().strip()
    sample_payloads = {
        "AAPL": IncomeStatementPayload(
            ticker="AAPL",
            cik="0000320193",
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            total_revenue=383_285_000_000,
            cost_of_revenue=214_137_000_000,
            operating_expenses=54_847_000_000,
            net_profit=96_995_000_000,
            segments=[
                SegmentRevenue(segment_axis="us-gaap:ProductOrServiceAxis", segment_member="IPhoneMember", segment_label="iPhone", value=200_583_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
                SegmentRevenue(segment_axis="us-gaap:ProductOrServiceAxis", segment_member="ServicesMember", segment_label="Services", value=85_200_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
                SegmentRevenue(segment_axis="us-gaap:ProductOrServiceAxis", segment_member="WearablesMember", segment_label="Wearables, Home & Accessories", value=39_845_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
                SegmentRevenue(segment_axis="us-gaap:ProductOrServiceAxis", segment_member="MacMember", segment_label="Mac", value=29_357_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
                SegmentRevenue(segment_axis="us-gaap:ProductOrServiceAxis", segment_member="IPadMember", segment_label="iPad", value=28_300_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
            ],
            operating_expense_details=[
                ExpenseDetail(expense_label="R&D", value=27_200_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
                ExpenseDetail(expense_label="Sales & marketing", value=11_900_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
                ExpenseDetail(expense_label="General & admin", value=11_500_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
            ],
        )
    }
    return sample_payloads.get(
        ticker,
        IncomeStatementPayload(
            ticker=ticker,
            cik="0000000000",
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            total_revenue=100_000_000_000,
            cost_of_revenue=40_000_000_000,
            operating_expenses=20_000_000_000,
            net_profit=30_000_000_000,
            segments=[
                SegmentRevenue(segment_axis="us-gaap:ProductOrServiceAxis", segment_member="SegmentAMember", segment_label="Segment A", value=60_000_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
                SegmentRevenue(segment_axis="us-gaap:ProductOrServiceAxis", segment_member="SegmentBMember", segment_label="Segment B", value=40_000_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
            ],
            operating_expense_details=[
                ExpenseDetail(expense_label="R&D", value=12_000_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
                ExpenseDetail(expense_label="Sales & marketing", value=8_000_000_000, fiscal_year=fiscal_year, fiscal_period=fiscal_period),
            ],
        ),
    )


@st.cache_data
def load_live_payload(ticker: str, fiscal_year: int, fiscal_period: str) -> IncomeStatementPayload | None:
    ticker = ticker.upper().strip()
    client = EdgarIngestionEngine(user_agent=USER_AGENT)
    company_tickers = client.fetch_company_tickers()
    company_record = lookup_company_record_for_ticker(ticker, company_tickers)
    if not company_record:
        return None

    cik = str(company_record["cik_str"]).zfill(10)

    company_facts = client.fetch_company_facts(cik)
    total_revenue = resolve_metric_fact(company_facts, "total_revenue", fiscal_year=fiscal_year, fiscal_period=fiscal_period)
    
    if total_revenue is None:
        return None

    resolved_fiscal_year = total_revenue.fiscal_year or fiscal_year
    resolved_fiscal_period = total_revenue.fiscal_period or fiscal_period

    cost_of_revenue = resolve_metric_fact(
        company_facts,
        "cost_of_revenue",
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        period_start=total_revenue.period_start or None,
        period_end=total_revenue.period_end or None,
    )
    operating_expenses = resolve_metric_fact(
        company_facts,
        "operating_expenses",
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        period_start=total_revenue.period_start or None,
        period_end=total_revenue.period_end or None,
    )
    net_profit = resolve_metric_fact(
        company_facts,
        "net_profit",
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        period_start=total_revenue.period_start or None,
        period_end=total_revenue.period_end or None,
    )

    segments = []
    if total_revenue.accession and total_revenue.period_start and total_revenue.period_end:
        submissions = client.fetch_submissions(cik)
        primary_document = lookup_primary_document_for_accession(submissions, total_revenue.accession)
        if primary_document:
            filing_xml = client.fetch_filing_xbrl_instance(cik, total_revenue.accession, primary_document)
            segments = extract_filing_segment_revenues(
                filing_xml,
                period_start=total_revenue.period_start,
                period_end=total_revenue.period_end,
                fiscal_year=resolved_fiscal_year,
                fiscal_period=resolved_fiscal_period,
            )
    return IncomeStatementPayload(
        ticker=ticker,
        cik=str(cik),
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        total_revenue=total_revenue.value,
        cost_of_revenue=cost_of_revenue.value if cost_of_revenue else None,
        operating_expenses=operating_expenses.value if operating_expenses else None,
        net_profit=net_profit.value if net_profit else None,
        segments=segments,
        operating_expense_details=[],
    )


def lookup_company_record_for_ticker(ticker: str, company_tickers: dict[str, Any]) -> dict[str, Any] | None:
    ticker = ticker.upper().strip()
    records = company_tickers.get("data")
    if isinstance(records, list):
        for record in records:
            if str(record.get("ticker", "")).upper().strip() == ticker:
                return record

    if isinstance(company_tickers, dict):
        for value in company_tickers.values():
            if isinstance(value, dict) and str(value.get("ticker", "")).upper().strip() == ticker:
                return value

    return None


def lookup_primary_document_for_accession(submissions: dict[str, Any], accession: str) -> str | None:
    recent = submissions.get("filings", {}).get("recent", {})
    accession = accession.strip()
    for index, candidate in enumerate(recent.get("accessionNumber", [])):
        if candidate == accession:
            documents = recent.get("primaryDocument", [])
            return documents[index] if index < len(documents) else None
    return None


def payload_to_tables(payload: IncomeStatementPayload) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    top_level = pd.DataFrame(
        [
            {
                "ticker": payload.ticker,
                "cik": payload.cik,
                "fiscal_year": payload.fiscal_year,
                "fiscal_period": payload.fiscal_period,
                "total_revenue": payload.total_revenue,
                "cost_of_revenue": payload.cost_of_revenue,
                "operating_expenses": payload.operating_expenses,
                "net_profit": payload.net_profit,
            }
        ]
    )
    segments = pd.DataFrame([segment.model_dump() for segment in payload.segments])
    expenses = pd.DataFrame([expense.model_dump() for expense in payload.operating_expense_details])
    return top_level, segments, expenses


def tables_to_payload(top_level_df: pd.DataFrame, segments_df: pd.DataFrame, expenses_df: pd.DataFrame) -> IncomeStatementPayload:
    top_level_row = top_level_df.iloc[0].to_dict()
    segments = [SegmentRevenue(**row) for row in segments_df.to_dict(orient="records") if row.get("segment_label")]
    expense_details = [ExpenseDetail(**row) for row in expenses_df.to_dict(orient="records") if row.get("expense_label")]
    return IncomeStatementPayload(
        ticker=str(top_level_row["ticker"]).upper().strip(),
        cik=str(top_level_row["cik"]),
        fiscal_year=int(top_level_row["fiscal_year"]),
        fiscal_period=str(top_level_row["fiscal_period"]),
        total_revenue=float(top_level_row["total_revenue"]) if pd.notna(top_level_row["total_revenue"]) else None,
        cost_of_revenue=float(top_level_row["cost_of_revenue"]) if pd.notna(top_level_row["cost_of_revenue"]) else None,
        operating_expenses=float(top_level_row["operating_expenses"]) if pd.notna(top_level_row["operating_expenses"]) else None,
        net_profit=float(top_level_row["net_profit"]) if pd.notna(top_level_row["net_profit"]) else None,
        segments=segments,
        operating_expense_details=expense_details,
    )


def sankey_figure(graph_data: dict[str, Any]) -> go.Figure:
    nodes = graph_data["nodes"]
    links = graph_data["links"]
    node_ids = [node["id"] for node in nodes]
    node_labels = [
        f"{node['label']}<br>${node['value'] / 1_000_000_000:.1f}B"
        for node in nodes
    ]
    node_index = {node_id: index for index, node_id in enumerate(node_ids)}
    node_colors = [node.get("color") or DEFAULT_KIND_COLORS.get(node.get("kind", ""), "#9aa5b1") for node in nodes]
    link_colors = [hex_to_rgba(nodes[node_index[link["source"]]].get("color") or DEFAULT_KIND_COLORS.get(nodes[node_index[link["source"]]].get("kind", ""), "#9aa5b1"), 0.28) for link in links]

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            valueformat=",.0f",
            textfont={
                    "family": "Georgia",
                    "size": 15,
                    "color": "#172033",
                    "shadow": "none",
            },
            node={
                "pad": 18,
                "thickness": 18,
                "line": {"color": "rgba(60,60,60,0.35)", "width": 0.6},
                "label": node_labels,
                "color": node_colors,
            },
            link={
                "source": [node_index[link["source"]] for link in links],
                "target": [node_index[link["target"]] for link in links],
                "value": [link["value"] for link in links],
                "color": link_colors,
            },
        )
    )
    fig.update_layout(
    margin={"l": 20, "r": 20, "t": 20, "b": 20},
    height=700,
    font={
        "family": "Trebuchet MS",
        "size": 13,
        "color": "#334155",
    },
)
    return fig


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def graph_with_colors(graph: Any, color_map: dict[str, str]) -> dict[str, Any]:
    graph_dict = graph.model_dump() if hasattr(graph, "model_dump") else dict(graph)
    for node in graph_dict.get("nodes", []):
        node["color"] = color_map.get(node["id"], DEFAULT_KIND_COLORS.get(node.get("kind", ""), "#9aa5b1"))
    return graph_dict


def build_color_controls(graph_data: dict[str, Any]) -> dict[str, str]:
    st.subheader("Color panel")
    st.markdown('<div class="desk-small">Choose the color for each segment and branch. These colors apply to the Sankey preview and the downloaded JSON.</div>', unsafe_allow_html=True)

    color_map: dict[str, str] = {}
    sections = [
        ("segments", "Segments", [node for node in graph_data["nodes"] if node["kind"] == "segment"]),
        ("branches", "Branches", [node for node in graph_data["nodes"] if node["kind"] in {"group", "subtotal", "expense", "expense_detail", "final"}]),
    ]

    for _, section_label, nodes in sections:
        with st.expander(section_label, expanded=(section_label == "Segments")):
            if not nodes:
                st.caption("No nodes available in this section.")
            for index, node in enumerate(nodes):
                default_color = node.get("color") or DEFAULT_KIND_COLORS.get(node.get("kind", ""), "#9aa5b1")
                picker_key = f"color_{node['id']}"
                if picker_key not in st.session_state:
                    st.session_state[picker_key] = default_color

                columns = st.columns([0.72, 0.28])
                columns[0].write(node["label"])
                selected_color = columns[1].color_picker(
                    label=f"Color for {node['label']}",
                    value=st.session_state[picker_key],
                    key=picker_key,
                    label_visibility="collapsed",
                )
                color_map[node["id"]] = selected_color

    return color_map


if "ticker_input" not in st.session_state:
    st.session_state.ticker_input = "AAPL"
if "payload" not in st.session_state:
    st.session_state.payload = load_sample_payload("AAPL", 2025, "FY")
if "source_mode" not in st.session_state:
    st.session_state.source_mode = "live"
if "company_info" not in st.session_state:
    st.session_state.company_info = {"name": "Sample payload", "ticker": "AAPL", "cik_str": "0000320193"}
if "fiscal_year_input" not in st.session_state:
    st.session_state.fiscal_year_input = 2025
if "period_kind" not in st.session_state:
    st.session_state.period_kind = "Year"
if "quarter_input" not in st.session_state:
    st.session_state.quarter_input = "Q2"

left_col, right_col = st.columns([0.32, 0.68], gap="large")

with left_col:
    st.subheader("Generate")
    ticker = st.text_input("Ticker", value=st.session_state.ticker_input, placeholder="AAPL")
    fiscal_year = st.number_input("Fiscal year", min_value=2000, max_value=2100, value=st.session_state.fiscal_year_input, step=1)
    period_kind = st.radio("Fiscal period type", ["Year", "Quarter"], horizontal=True, key="period_kind")
    if period_kind == "Quarter":
        fiscal_period = st.selectbox("Quarter", ["Q1", "Q2", "Q3", "Q4"], index=["Q1", "Q2", "Q3", "Q4"].index(st.session_state.quarter_input), key="quarter_input")
    else:
        fiscal_period = "FY"
    generate_clicked = st.button("Generate", type="primary", use_container_width=True)
    st.write("Use the editable tables below to refine the graph before downloading.")
    st.radio("Data source", ["live", "sample"], index=0 if st.session_state.source_mode == "live" else 1, horizontal=True, key="source_mode")
    st.markdown(
        '<div class="desk-panel"><div class="desk-small">Live mode resolves the ticker through SEC company facts. If live lookup fails, the app falls back to sample data so the workflow stays usable.</div></div>',
        unsafe_allow_html=True,
    )

if generate_clicked:
    st.session_state.ticker_input = ticker.upper().strip()
    st.session_state.fiscal_year_input = int(fiscal_year)
    if st.session_state.source_mode == "live":
        live_payload = load_live_payload(st.session_state.ticker_input, int(fiscal_year), fiscal_period)
        if live_payload is None:
            st.warning("Live EDGAR lookup failed for this ticker, falling back to sample data.")
            st.session_state.payload = load_sample_payload(st.session_state.ticker_input, int(fiscal_year), fiscal_period)
            st.session_state.company_info = {"name": "Sample fallback", "ticker": st.session_state.ticker_input, "cik_str": st.session_state.payload.cik}
        else:
            st.session_state.payload = live_payload
            client = EdgarIngestionEngine(user_agent=USER_AGENT)
            company_tickers = client.fetch_company_tickers()
            st.session_state.company_info = lookup_company_record_for_ticker(st.session_state.ticker_input, company_tickers) or {"name": "Unknown", "ticker": st.session_state.ticker_input, "cik_str": st.session_state.payload.cik}
    else:
        st.session_state.payload = load_sample_payload(st.session_state.ticker_input, int(fiscal_year), fiscal_period)
        st.session_state.company_info = {"name": "Sample payload", "ticker": st.session_state.ticker_input, "cik_str": st.session_state.payload.cik}

with right_col:
    top_level_df, segments_df, expenses_df = payload_to_tables(st.session_state.payload)
    reconciliation = reconcile_revenue(st.session_state.payload)
    st.subheader("Graph preview")
    graph = build_tencent_style_sankey_graph(st.session_state.payload)
    graph_data = graph.model_dump()
    color_map = build_color_controls(graph_data)
    graph_data = graph_with_colors(graph, color_map)
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    summary_col1.metric("Ticker", st.session_state.payload.ticker)
    summary_col2.metric("Fiscal period", f"{st.session_state.payload.fiscal_period} {st.session_state.payload.fiscal_year}")
    summary_col3.metric("Source", "Live EDGAR" if st.session_state.source_mode == "live" and st.session_state.payload.cik != "0000000000" else "Sample")
    st.markdown(
        f'<div class="desk-panel"><div class="desk-small"><strong>Matched company:</strong> {st.session_state.company_info.get("name", "Unknown")} | <strong>CIK:</strong> {str(st.session_state.company_info.get("cik_str", st.session_state.payload.cik)).zfill(10)}</div></div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(sankey_figure(graph_data), use_container_width=True)

st.divider()

st.subheader("Income statement editor")
st.markdown('<div class="desk-small">Edit the top-level fields, segment rows, and operating expense detail rows. Rebuild the graph to apply changes before downloading.</div>', unsafe_allow_html=True)
col_top, col_segments, col_expenses = st.columns(3, gap="large")

with col_top:
    st.markdown("##### Top level")
    edited_top_level = st.data_editor(top_level_df, num_rows="fixed", use_container_width=True, key="top_level_editor")

with col_segments:
    st.markdown("##### Revenue segments")
    edited_segments = st.data_editor(segments_df, num_rows="dynamic", use_container_width=True, key="segments_editor")

with col_expenses:
    st.markdown("##### Operating expense details")
    edited_expenses = st.data_editor(expenses_df, num_rows="dynamic", use_container_width=True, key="expenses_editor")

if st.button("Rebuild graph", use_container_width=True):
    st.session_state.payload = tables_to_payload(edited_top_level, edited_segments, edited_expenses)
    reconciliation = reconcile_revenue(st.session_state.payload)
    graph = build_tencent_style_sankey_graph(st.session_state.payload)
    st.success("Graph rebuilt from the edited tables.")

st.subheader("Reconciliation")
reconciliation = reconcile_revenue(st.session_state.payload)
st.metric("Status", reconciliation.status)
st.metric("Segment revenue sum", f"{reconciliation.segment_revenue_sum:,.0f}")
st.metric("Reconciliation error %", f"{reconciliation.reconciliation_error_pct:.2f}")
if reconciliation.residual_label:
    st.warning(f"Residual node: {reconciliation.residual_label} ({reconciliation.residual_value:,.0f})")

final_graph = build_tencent_style_sankey_graph(st.session_state.payload)
final_graph_json = graph_with_colors(final_graph, {node.get("id"): node.get("color") for node in graph_data.get("nodes", [])})
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(json.dumps(final_graph_json, indent=2), encoding="utf-8")

st.subheader("Download")
st.download_button(
    label="Download Sankey JSON",
    data=json.dumps(final_graph_json, indent=2),
    file_name="sankey_data.json",
    mime="application/json",
    use_container_width=True,
)

st.caption(f"Latest export saved to: {OUTPUT_PATH}")
