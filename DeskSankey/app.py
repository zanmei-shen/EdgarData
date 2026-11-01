from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from edgardata.exports.sankey_exporter import build_tencent_style_sankey_graph
from edgardata.ingestion.edgar_client import EdgarIngestionEngine
from edgardata.ingestion.company_lookup import (
    company_record_label,
    company_records,
    lookup_company_records,
)
from edgardata.models.schema import ExpenseDetail, IncomeStatementPayload, SegmentRevenue
from edgardata.parser.segment_parser import extract_filing_product_revenues, extract_filing_segment_revenues
from edgardata.parser.taxonomy_mapper import resolve_metric_fact
from edgardata.pipeline.financials import resolve_operating_expenses
from edgardata.pipeline.reconciliation import reconcile_revenue

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
OUTPUT_PATH = DATA_DIR / "sankey_data.json"


def most_recent_completed_quarter(today: date | None = None) -> str:
    current_date = today or date.today()
    current_quarter = (current_date.month - 1) // 3 + 1
    completed_quarter = current_quarter - 1 or 4
    return f"Q{completed_quarter}"


DEFAULT_KIND_COLORS = {
    "segment": "#4E73DF",
    "group": "#555555",
    "subtotal": "#4C9A2A",
    "expense": "#C82814",
    "expense_detail": "#C82814",
    "final": "#3D8F22",
}

PALETTE = {
    "background": "#F5F5F5",
    "search_blue": "#4E73DF",
    "youtube_blue": "#7D9BE8",
    "cloud_gold": "#E8B62A",
    "subscription_gold": "#EDC441",
    "gross_green": "#4C9A2A",
    "operating_green": "#46962A",
    "net_green": "#3D8F22",
    "expense_red": "#C82814",
    "title_blue": "#214B84",
    "secondary_gray": "#555555",
}

st.set_page_config(page_title="Sankey", layout="wide")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.75rem;
            padding-bottom: 1.5rem;
            max-width: 1480px;
        }
        .desk-hero {
            padding: 1rem 1.25rem;
            border-radius: 18px;
            background: #B7D7F0;
            color: #214B84;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.20);
            margin-bottom: 1rem;
            text-align: center;
        }
        .desk-hero h1 {
            margin: 0;
            font-size: 2rem;
            line-height: 1.1;
            text-align: center;
        }
        .desk-hero p {
            margin: 0.35rem 0 0 0;
            color: #365B7D;
            font-size: 0.98rem;
            text-align: center;
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
        <h1>Sankey</h1>
        <p>Enter a ticker, generate a layered income flow graph, edit the numbers, and download the JSON.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("Generate and edit a Sankey diagram from normalized EDGAR income data.")

USER_AGENT = os.getenv("EDGAR_USER_AGENT", "DeskSankey desk@yourcompany.com")


@st.cache_data(show_spinner=False)
def load_company_tickers() -> dict[str, Any]:
    client = EdgarIngestionEngine(user_agent=USER_AGENT)
    return client.fetch_company_tickers()


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
    operating_income = resolve_metric_fact(
        company_facts,
        "operating_income",
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        period_start=total_revenue.period_start or None,
        period_end=total_revenue.period_end or None,
    )
    reported_operating_expenses = resolve_metric_fact(
        company_facts,
        "operating_expenses",
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        period_start=total_revenue.period_start or None,
        period_end=total_revenue.period_end or None,
    )
    operating_expenses, expense_details = resolve_operating_expenses(
        company_facts,
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        period_start=total_revenue.period_start or None,
        period_end=total_revenue.period_end or None,
        reported_operating_expenses=reported_operating_expenses,
        total_revenue=total_revenue.value,
        cost_of_revenue=cost_of_revenue.value if cost_of_revenue else None,
        operating_income=operating_income.value if operating_income else None,
    )
    net_profit = resolve_metric_fact(
        company_facts,
        "net_profit",
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        period_start=total_revenue.period_start or None,
        period_end=total_revenue.period_end or None,
    )
    income_before_tax = resolve_metric_fact(
        company_facts,
        "income_before_tax",
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        period_start=total_revenue.period_start or None,
        period_end=total_revenue.period_end or None,
    )
    other_income_expense = resolve_metric_fact(
        company_facts,
        "other_income_expense",
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        period_start=total_revenue.period_start or None,
        period_end=total_revenue.period_end or None,
    )
    income_tax_expense = resolve_metric_fact(
        company_facts,
        "income_tax_expense",
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
            filing_html = client.fetch_filing_document(cik, total_revenue.accession, primary_document)
            product_segments = extract_filing_product_revenues(
                filing_html,
                filing_xml,
                period_start=total_revenue.period_start,
                period_end=total_revenue.period_end,
                fiscal_year=resolved_fiscal_year,
                fiscal_period=resolved_fiscal_period,
            )
            if product_segments:
                segments.extend(product_segments)
    return IncomeStatementPayload(
        ticker=ticker,
        cik=str(cik),
        fiscal_year=resolved_fiscal_year,
        fiscal_period=resolved_fiscal_period,
        total_revenue=total_revenue.value,
        cost_of_revenue=cost_of_revenue.value if cost_of_revenue else None,
        operating_expenses=operating_expenses,
        income_before_tax=income_before_tax.value if income_before_tax else None,
        other_income_expense=other_income_expense.value if other_income_expense else None,
        income_tax_expense=income_tax_expense.value if income_tax_expense else None,
        net_profit=net_profit.value if net_profit else None,
        segments=segments,
        operating_expense_details=expense_details,
    )


def lookup_company_record_for_ticker(ticker: str, company_tickers: dict[str, Any]) -> dict[str, Any] | None:
    matches = lookup_company_records(ticker, company_tickers)
    return matches[0] if matches else None


def lookup_primary_document_for_accession(submissions: dict[str, Any], accession: str) -> str | None:
    recent = submissions.get("filings", {}).get("recent", {})
    accession = accession.strip()
    for index, candidate in enumerate(recent.get("accessionNumber", [])):
        if candidate == accession:
            documents = recent.get("primaryDocument", [])
            return documents[index] if index < len(documents) else None
    return None
def combine_small_segments(payload: IncomeStatementPayload, threshold: float = 5_000_000_000) -> IncomeStatementPayload:
    """Combine all revenue segments under the threshold into a single 'Other' segment."""

    small_segments = []
    large_segments = []

    for seg in payload.segments:
        if seg.value < threshold:
            small_segments.append(seg)
        else:
            large_segments.append(seg)

    # If no small segments, return unchanged
    if not small_segments:
        return payload

    # Aggregate small segments
    other_total = sum(seg.value for seg in small_segments)

    other_segment = SegmentRevenue(
        segment_axis="us-gaap:ProductOrServiceAxis",
        segment_member="OtherMember",
        segment_label="Other",
        value=other_total,
        fiscal_year=payload.fiscal_year,
        fiscal_period=payload.fiscal_period,
    )

    # Replace segments list
    payload.segments = large_segments + [other_segment]

    return payload


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


def sankey_figure(graph_data: dict[str, Any], height: int = 780) -> go.Figure:
    nodes = graph_data["nodes"]
    links = graph_data["links"]
    node_ids = [node["id"] for node in nodes]
    node_index = {node_id: index for index, node_id in enumerate(node_ids)}
    node_colors = []
    for node in nodes:
        node_colors.append(
            node.get("color")
            or DEFAULT_KIND_COLORS.get(node.get("kind", ""), "#9aa5b1")
        )
    for target_index, target in enumerate(nodes):
        if target.get("kind") != "segment":
            continue
        incoming = [
            link for link in links
            if link["target"] == target["id"] and nodes[node_index[link["source"]]].get("kind") == "segment"
        ]
        if incoming:
            largest_source = max(incoming, key=lambda link: link["value"])
            merge_color = node_colors[node_index[largest_source["source"]]]
            if not nodes[target_index].get("color"):
                node_colors[target_index] = merge_color
            for link in incoming:
                if not nodes[node_index[link["source"]]].get("color"):
                    node_colors[node_index[link["source"]]] = merge_color
    revenue_index = node_index.get("revenue")
    if revenue_index is not None:
        revenue_sources = [
            link for link in links
            if link["target"] == "revenue"
            and nodes[node_index[link["source"]]].get("kind") == "segment"
        ]
        if revenue_sources:
            largest_revenue_source = max(revenue_sources, key=lambda link: link["value"])
            node_colors[revenue_index] = node_colors[
                node_index[largest_revenue_source["source"]]
            ]
    top_level = graph_data.get("top_level", {})
    revenue = float(top_level.get("total_revenue") or 0)
    gross_profit = float(top_level.get("gross_profit") or 0)
    operating_profit = float(top_level.get("operating_profit") or 0)
    net_profit = float(top_level.get("net_profit") or 0)

    def metric_text(node: dict[str, Any]) -> str:
        value = float(node.get("value") or 0)
        label = node["label"]
        if node["id"] in {"gross_profit", "operating_profit", "net_profit"}:
            label = label.replace(" ", "<br>", 1)
        elif node["id"] == "income_before_tax":
            label = "Income before<br>tax"
        if node["id"] == "revenue":
            secondary = "100% of revenue"
        elif node["id"] == "gross_profit":
            secondary = f"{gross_profit / revenue:.0%} margin" if revenue else ""
        elif node["id"] == "operating_profit":
            secondary = f"{operating_profit / revenue:.0%} margin" if revenue else ""
        elif node["id"] == "net_profit":
            secondary = f"{net_profit / revenue:.0%} margin" if revenue else ""
        elif node.get("kind") in {"expense", "expense_detail"}:
            secondary = f"{value / revenue:.0%} of revenue" if revenue else ""
        elif node.get("kind") == "segment":
            secondary = f"{value / revenue:.0%} of revenue" if revenue else ""
        else:
            secondary = ""
        value_text = f"${value / 1_000_000_000:.1f}B"
        return f"{label}<br>{value_text}<br>{secondary}" if secondary else f"{label}<br>{value_text}"

    # Keep the financial story horizontal and reserve a bounded lower band for
    # expenses so Plotly cannot push downstream nodes outside the chart.
    segment_nodes = [node for node in nodes if node.get("kind") == "segment"]
    segment_y = [
        0.15 + index * (0.67 / max(len(segment_nodes) - 1, 1))
        for index in range(len(segment_nodes))
    ]
    positions: dict[str, tuple[float, float]] = {
        node["id"]: (0.26, 0.30) for node in nodes
    }
    for index, node in enumerate(segment_nodes):
        positions[node["id"]] = (0.05, segment_y[index])
    for node_id, x, y in (
        ("revenue", 0.20, 0.30),
        ("gross_profit", 0.38, 0.30),
        ("operating_profit", 0.56, 0.30),
        ("income_before_tax", 0.73, 0.30),
        ("net_profit", 0.89, 0.30),
        ("cost_of_revenue", 0.38, 0.67),
        ("operating_expenses", 0.56, 0.67),
    ):
        if node_id in node_index:
            positions[node_id] = (x, y)

    expense_nodes = [
        node for node in nodes
        if node.get("kind") in {"expense_detail", "income", "expense"}
        and node["id"] not in {"cost_of_revenue", "operating_expenses"}
    ]
    for index, node in enumerate(expense_nodes):
        positions[node["id"]] = (
            0.72 + (index % 2) * 0.12,
            0.58 + (index // 2) * 0.12,
        )

    node_x = [positions[node["id"]][0] for node in nodes]
    node_y = [positions[node["id"]][1] for node in nodes]

    link_colors = []
    for link in links:
        source = nodes[node_index[link["source"]]]
        target = nodes[node_index[link["target"]]]
        source_kind = source.get("kind")
        target_kind = target.get("kind")
        if source_kind == "segment":
            color = node_colors[node_index[link["source"]]]
        else:
            color = node_colors[node_index[link["target"]]]
        link_colors.append(hex_to_rgba(color, 0.48))

    node_labels = [metric_text(node) for node in nodes]
    fig = go.Figure(
        go.Sankey(
            arrangement="freeform",
            valueformat=",.0f",
            textfont={
                "family": "Inter, Segoe UI, sans-serif",
                "size": 13,
                "color": PALETTE["secondary_gray"],
                "shadow": "none",
                "weight": 700,
            },
            node={
                "pad": 26,
                "thickness": 20,
                "line": {"color": "rgba(0,0,0,0)", "width": 0},
                "label": node_labels,
                "color": node_colors,
                "x": node_x,
                "y": node_y,
                "hovertemplate": "%{label}<extra></extra>",
            },
            link={
                "source": [node_index[link["source"]] for link in links],
                "target": [node_index[link["target"]] for link in links],
                "value": [link["value"] for link in links],
                "color": link_colors,
                "hovertemplate": "%{value:,.0f}<extra></extra>",
            },
        )
    )
    annotations = [
        {
            "x": 0.5,
            "y": 1.10,
            "xref": "paper",
            "yref": "paper",
            "text": f"<b>{graph_data.get('ticker', '')} {graph_data.get('period', '')} Income Statement</b>",
            "showarrow": False,
            "font": {"family": "Inter, Segoe UI, sans-serif", "size": 30, "color": PALETTE["title_blue"]},
        },
        {
            "x": 0.5,
            "y": 1.035,
            "xref": "paper",
            "yref": "paper",
            "text": "Revenue sources → profit conversion → expenses and tax",
            "showarrow": False,
            "font": {"family": "Inter, Segoe UI, sans-serif", "size": 12, "color": PALETTE["secondary_gray"]},
        },
    ]
    fig.update_layout(
        margin={"l": 35, "r": 55, "t": 105, "b": 30},
        height=height,
        plot_bgcolor=PALETTE["background"],
        paper_bgcolor=PALETTE["background"],
        annotations=annotations,
        font={
            "family": "Inter, Segoe UI, sans-serif",
            "size": 13,
            "color": PALETTE["secondary_gray"],
        },
        hoverlabel={
            "font": {"family": "Inter, Segoe UI, sans-serif", "size": 15},
            "bgcolor": "#ffffff",
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
                picker_key = f"color_{node['id']}_{index}"
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
    st.session_state.payload = None
if "source_mode" not in st.session_state:
    st.session_state.source_mode = "live"
if "company_info" not in st.session_state:
    st.session_state.company_info = {"name": "Sample payload", "ticker": "AAPL", "cik_str": "0000320193"}
if "fiscal_year_input" not in st.session_state:
    st.session_state.fiscal_year_input = date.today().year
if "period_kind" not in st.session_state:
    st.session_state.period_kind = "Quarter"
if "quarter_input" not in st.session_state:
    st.session_state.quarter_input = most_recent_completed_quarter()
if "ticker_input_changed" not in st.session_state:
    st.session_state.ticker_input_changed = False
if "ticker_input_widget" not in st.session_state:
    st.session_state.ticker_input_widget = st.session_state.ticker_input
if "company_suggestion" not in st.session_state:
    st.session_state.company_suggestion = None


def request_ticker_generation() -> None:
    """Run the same workflow when the ticker input is committed with Enter."""

    st.session_state.company_suggestion = None
    st.session_state.ticker_input_changed = True


def apply_company_suggestion() -> None:
    suggestion = st.session_state.company_suggestion
    if suggestion:
        st.session_state.ticker_input_widget = suggestion
        st.session_state.ticker_input_changed = False


left_col, right_col = st.columns([0.32, 0.68], gap="large")

with left_col:
    st.subheader("Generate")
    company_matches: list[dict[str, Any]] = []
    selected_company = None
    if st.session_state.source_mode == "live":
        try:
            company_tickers = load_company_tickers()
            company_matches = company_records(company_tickers)
        except (httpx.HTTPError, TimeoutError, RuntimeError) as exc:
            st.warning(f"Unable to load the SEC company directory: {exc}")
            company_tickers = None
            company_matches = []

        ticker_options = [company_record_label(record) for record in company_matches]
        current_ticker = st.session_state.ticker_input.upper().strip()
        current_index = next(
            (
                index
                for index, record in enumerate(company_matches)
                if str(record.get("ticker", "")).upper().strip() == current_ticker
            ),
            0,
        )
        selected_label = st.selectbox(
            "Ticker",
            options=ticker_options,
            index=current_index if ticker_options else None,
            key="ticker_company_option",
            help="Click to browse companies or type a ticker or company name to filter.",
        )
        selected_index = ticker_options.index(selected_label) if selected_label else None
        selected_company = (
            company_matches[selected_index] if selected_index is not None else None
        )
        ticker = (
            str(selected_company.get("ticker", "")).strip().upper()
            if selected_company
            else ""
        )
    else:
        ticker = st.text_input(
            "Ticker",
            placeholder="AAPL",
            key="ticker_input_widget",
            on_change=request_ticker_generation,
        )
        if ticker.strip():
            try:
                company_tickers = load_company_tickers()
                company_matches = lookup_company_records(ticker, company_tickers)
            except (httpx.HTTPError, TimeoutError, RuntimeError) as exc:
                st.warning(f"Unable to load the SEC company directory: {exc}")
        if len(company_matches) == 1:
            selected_company = company_matches[0]

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

auto_generate_requested = st.session_state.ticker_input_changed
generate_requested = generate_clicked or auto_generate_requested
st.session_state.ticker_input_changed = False

if generate_requested:
    if st.session_state.source_mode == "live":
        if not company_matches:
            st.error(f"Could not identify company or ticker: {ticker.strip() or '(empty input)'}.")
            st.stop()
        if len(company_matches) > 1 and auto_generate_requested and not generate_clicked:
            st.info("Select the matching company, then click Generate.")
            st.stop()
        resolved_ticker = str(
            (selected_company or company_matches[0]).get("ticker", "")
        ).strip().upper()
    else:
        resolved_ticker = ticker.upper().strip()

    st.session_state.ticker_input = resolved_ticker
    st.session_state.fiscal_year_input = int(fiscal_year)
    if st.session_state.source_mode == "live":
        try:
            live_payload = load_live_payload(
                st.session_state.ticker_input,
                int(fiscal_year),
                fiscal_period,
            )
        except Exception as exc:
            st.session_state.payload = None
            st.session_state.company_info = {}
            st.error(f"Unable to fetch data: {exc}")
            st.stop()
        if live_payload is None:
            st.session_state.payload = None
            st.session_state.company_info = {}
            st.error(
                f"No live data found for {st.session_state.ticker_input} "
                f"{fiscal_period} FY{int(fiscal_year)}."
            )
            st.stop()
        else:
            st.session_state.payload = live_payload
            st.session_state.payload = combine_small_segments(st.session_state.payload)
            client = EdgarIngestionEngine(user_agent=USER_AGENT)
            company_tickers = client.fetch_company_tickers()
            st.session_state.company_info = (
                lookup_company_record_for_ticker(
                    st.session_state.ticker_input,
                    company_tickers,
                )
                or {
                    "name": "Unknown",
                    "ticker": st.session_state.ticker_input,
                    "cik_str": st.session_state.payload.cik,
                }
            )
    else:
        st.session_state.payload = load_sample_payload(st.session_state.ticker_input, int(fiscal_year), fiscal_period)
        #st.session_state.payload = combine_small_segments(st.session_state.payload)
        st.session_state.company_info = {"name": "Sample payload", "ticker": st.session_state.ticker_input, "cik_str": st.session_state.payload.cik}
    st.session_state.payload = combine_small_segments(st.session_state.payload)
if st.session_state.payload is None:
    st.info("No data found. Enter a valid ticker and reporting period.")
    st.stop()

with right_col:
    top_level_df, segments_df, expenses_df = payload_to_tables(st.session_state.payload)
    reconciliation = reconcile_revenue(st.session_state.payload)
    st.subheader("Graph preview")
    graph = build_tencent_style_sankey_graph(st.session_state.payload)
    graph_data = graph.model_dump()
    chart_height = st.slider(
        "Sankey frame height",
        min_value=520,
        max_value=1200,
        value=780,
        step=20,
        help="Resize the visualization frame without changing the draggable node layout.",
    )
    graph_placeholder = st.empty()
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
    graph_placeholder.plotly_chart(
        sankey_figure(graph_data, height=chart_height),
        width="stretch",
    )

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
    st.session_state.payload = combine_small_segments(st.session_state.payload)
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
