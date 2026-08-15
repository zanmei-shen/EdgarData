# edgar-parser-core

A high-throughput, SEC-compliant Python library and data pipeline designed to parse top-level income statement metrics (Total Revenue, Cost of Revenue, Operating Expenses, Net Profit) and multidimensional segment breakdowns (Product Lines, Business Units) directly from free SEC EDGAR XBRL endpoints.

Outputs normalized, reconciled data structured specifically for **Sankey diagrams** and quantitative financial modeling.
The exporter now emits a layered graph model with explicit `nodes` and `links`, suitable for Tencent-style financial flow diagrams.

---

## 💡 Key Features

* **SEC Rate-Limit Compliant:** Built-in throttle handling (max 10 requests/sec) and enforced user-agent headers.
* **Taxonomy Fallback Engine:** Handles variations in US-GAAP reporting tags across historical 10-K and 10-Q filings using ordered concept resolution chains.
* **Dimensional Segment Extraction:** Unpacks Inline XBRL explicit member dimensions (`StatementBusinessSegmentsAxis`, `ProductOrServiceAxis`) to isolate revenue by product line or division.
* **Automated Data Quality Gate:** Reconciles the sum of segment revenues against reported top-level revenue with automatic residual calculation for corporate/unallocated line items.
* **Tencent-Style Sankey Export:** Generates explicit graph output with `nodes`, `links`, `top_level`, and `segment_breakdown` sections for layered flow visualizations.

---

## 🏗 System Architecture

```
[ SEC EDGAR REST API / XBRL CompanyFacts ]
                   │
                   ▼
     ┌───────────────────────────┐
     │ Ingestion & Rate Limiter  │  <-- 10 req/sec Throttle Guard
     └─────────────┬─────────────┘
                   │
                   ▼
     ┌───────────────────────────┐
     │   XBRL Fact Resolution    │  <-- Fallback Chains & Dimension Parsing
     └─────────────┬─────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌───────────────────┐ ┌────────────────────────┐
│ Top-Level Parser  │ │ Segment Dimension      │
│ (US-GAAP Tags)    │ │ Parser (Axis/Member)   │
└────────┬──────────┘ └──────────┬─────────────┘
         │                       │
         └─────────┬─────────────┘
                   ▼
     ┌───────────────────────────┐
     │ Reconciliation & Quality  │  <-- Segment Sum vs. Total Revenue Gate
     └─────────────┬─────────────┘
                   │
                   ▼
     ┌───────────────────────────┐
     │ Storage & Export Layer    │  <-- DuckDB / Parquet / Sankey JSON
     └───────────────────────────┘
```

---

## 📦 Project Structure

```text
edgardata/
├── config/
│   └── settings.py          # Enforces User-Agent and global rate limits
├── ingestion/
│   └── edgar_client.py      # Async HTTP client for SEC EDGAR endpoints
├── parser/
│   ├── taxonomy_mapper.py   # US-GAAP concept mapping & fallback logic
│   └── segment_parser.py    # Axis/Member dimension parser for product segments
├── pipeline/
│   └── reconciliation.py    # Quality check & tolerance validation module
├── models/
│   └── schema.py            # Pydantic data models for metrics, Sankey nodes, and graph output
├── exports/
│   └── sankey_exporter.py   # Converts normalized data to layered Sankey graph output
├── tests/                   # Unit & integration tests
├── README.md
└── requirements.txt
```

---

## 🚀 Quick Start

### 1. Prerequisites
Python 3.11 or higher is required.

### 2. Installation
```bash
git clone https://github.com/zanmei-shen/edgardata.git
cd edgar-parser-core
pip install -r requirements.txt
```

### 3. Usage Example

```python
from ingestion.edgar_client import EdgarIngestionEngine
from parser.taxonomy_mapper import FinancialTaxonomyParser
from exports.sankey_exporter import build_tencent_style_sankey_graph

# 1. Initialize client with compliant User-Agent
client = EdgarIngestionEngine(user_agent="MyDataCorp admin@mydatacorp.com")

# 2. Fetch company facts (e.g., Apple CIK: 0000320193)
raw_facts = client.fetch_company_facts(cik="0000320193")

# 3. Parse financial statements & segments
parser = FinancialTaxonomyParser(raw_facts)
financial_data = parser.extract_income_statement(fiscal_year=2025, fiscal_period="FY")

# 4. Generate Sankey-ready JSON output
graph = build_tencent_style_sankey_graph(financial_data)
print(graph.model_dump())
```

---

## 📊 Sankey Graph Schema

The exporter returns a layered graph that can be rendered directly by Plotly, D3.js, or any Sankey-compatible frontend.

### Node model

Each node includes:

* `id`: stable identifier used by links
* `label`: display text shown in the diagram
* `stage`: layout layer in the flow graph
* `kind`: semantic category such as `segment`, `subtotal`, `expense`, `expense_detail`, or `final`
* `value`: node magnitude used for sizing

### Link model

Each link includes:

* `source`: upstream node id
* `target`: downstream node id
* `value`: flow amount
* `kind`: flow classification

### Example output

```json
{
  "ticker": "AAPL",
  "period": "FY2025",
  "currency": "USD",
  "nodes": [
    { "id": "segment_iphone", "label": "iPhone", "stage": 0, "kind": "segment", "value": 200583000000 },
    { "id": "revenue", "label": "Revenue", "stage": 1, "kind": "subtotal", "value": 383285000000 },
    { "id": "gross_profit", "label": "Gross profit", "stage": 2, "kind": "subtotal", "value": 169148000000 },
    { "id": "operating_expenses", "label": "Operating expenses", "stage": 3, "kind": "expense", "value": 54847000000 },
    { "id": "operating_profit", "label": "Operating profit", "stage": 4, "kind": "subtotal", "value": 114301000000 },
    { "id": "net_profit", "label": "Net profit", "stage": 5, "kind": "final", "value": 96995000000 }
  ],
  "links": [
    { "source": "segment_iphone", "target": "revenue", "value": 200583000000, "kind": "flow" },
    { "source": "revenue", "target": "gross_profit", "value": 169148000000, "kind": "flow" },
    { "source": "gross_profit", "target": "operating_profit", "value": 114301000000, "kind": "flow" },
    { "source": "operating_profit", "target": "net_profit", "value": 96995000000, "kind": "flow" }
  ],
  "top_level": {
    "total_revenue": 383285000000,
    "cost_of_revenue": 214137000000,
    "gross_profit": 169148000000,
    "operating_expenses": 54847000000,
    "operating_profit": 114301000000,
    "net_profit": 96995000000
  },
  "segment_breakdown": [
    { "source": "iPhone", "target": "Revenue", "value": 200583000000 },
    { "source": "Services", "target": "Revenue", "value": 85200000000 },
    { "source": "Wearables, Home & Accessories", "target": "Revenue", "value": 39845000000 },
    { "source": "Mac", "target": "Revenue", "value": 29357000000 },
    { "source": "iPad", "target": "Revenue", "value": 28300000000 }
  ]
}
```

If operating expense detail facts are available, the exporter can also add optional `expense_detail` nodes under `operating_expenses` for branches like `R&D`, `Sales & marketing`, and `General & admin`.

### Graph schema reference

**`SankeyNode`**

* `id`: stable node identifier used by links
* `label`: text shown on the diagram
* `stage`: layout layer in the flow graph
* `kind`: semantic type such as `segment`, `subtotal`, `expense`, `expense_detail`, or `final`
* `value`: magnitude used for node sizing
* `color`: optional display color

**`SankeyLink`**

* `source`: upstream node id
* `target`: downstream node id
* `value`: flow amount
* `kind`: link classification, defaulting to `flow`

**`ExpenseDetail`**

* `expense_label`: branch label such as `R&D` or `Sales & marketing`
* `value`: expense amount
* `fiscal_year`: fiscal year of the filing
* `fiscal_period`: fiscal period such as `FY` or `Q2`

---

## 🛠 Quality Check & Reconciliation Rules

The reconciliation module calculates segment variance against reported revenue:

$$\text{Reconciliation Error (\%)} = \left| \frac{\text{Total Revenue} - \sum \text{Segment Revenue}}{\text{Total Revenue}} \right| \times 100$$

* **`< 5% Error`**: Tagged as `RECONCILED_EXACT`.
* **`5% - 15% Error`**: Synthetic `"Corporate / Unallocated Revenue"` node is added to account for intersegment eliminations.
* **`> 15% Error`**: Flagged for manual review due to missing/custom taxonomy tags.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
