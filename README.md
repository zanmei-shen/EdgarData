# edgar-parser-core

A high-throughput, SEC-compliant Python library and data pipeline designed to parse top-level income statement metrics (Total Revenue, Cost of Revenue, Operating Expenses, Net Profit) and multidimensional segment breakdowns (Product Lines, Business Units) directly from free SEC EDGAR XBRL endpoints.

Outputs normalized, reconciled data structured specifically for **Sankey diagrams** and quantitative financial modeling.

---

## 💡 Key Features

* **SEC Rate-Limit Compliant:** Built-in throttle handling (max 10 requests/sec) and enforced user-agent headers.
* **Taxonomy Fallback Engine:** Handles variations in US-GAAP reporting tags across historical 10-K and 10-Q filings using ordered concept resolution chains.
* **Dimensional Segment Extraction:** Unpacks Inline XBRL explicit member dimensions (`StatementBusinessSegmentsAxis`, `ProductOrServiceAxis`) to isolate revenue by product line or division.
* **Automated Data Quality Gate:** Reconciles the sum of segment revenues against reported top-level revenue with automatic residual calculation for corporate/unallocated line items.
* **Sankey-Ready Export:** Generates standardized JSON flows (`Source -> Target -> Value`) ready for Plotly, D3.js, or SankeyMATIC.

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
│   └── schema.py            # Pydantic data models for financial metrics
├── exports/
│   └── sankey_exporter.py   # Converts normalized data to Sankey JSON format
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
from exports.sankey_exporter import export_to_sankey_json

# 1. Initialize client with compliant User-Agent
client = EdgarIngestionEngine(user_agent="MyDataCorp admin@mydatacorp.com")

# 2. Fetch company facts (e.g., Apple CIK: 0000320193)
raw_facts = client.fetch_company_facts(cik="0000320193")

# 3. Parse financial statements & segments
parser = FinancialTaxonomyParser(raw_facts)
financial_data = parser.extract_income_statement(fiscal_year=2025, fiscal_period="FY")

# 4. Generate Sankey-ready JSON output
sankey_json = export_to_sankey_json(financial_data)
print(sankey_json)
```

---

## 📊 Sample Sankey Output Schema

```json
{
  "ticker": "AAPL",
  "period": "FY2025",
  "currency": "USD",
  "top_level": {
    "total_revenue": 383285000000,
    "cost_of_revenue": 214137000000,
    "operating_expenses": 54847000000,
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
