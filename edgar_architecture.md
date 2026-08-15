System Architecture: SEC EDGAR Financial & Segment Data Extractor (edgar-parser-core)

Target Stack: Python 3.11+, SEC EDGAR REST API, edgartools, Polars/Pandas, DuckDB, Pydantic

Primary Goal: Programmatically fetch, normalize, and reconcile top-level income statement metrics and multidimensional segment breakdowns (Product Line / Business Unit) from free SEC EDGAR endpoints.

1. High-Level Architecture Overview
[ SEC EDGAR REST API / XBRL CompanyFacts ]
                   │
                   ▼
     ┌───────────────────────────┐
     │   Ingestion & Rate Limiter │  <-- 10 req/sec, User-Agent Header Compliance
     └─────────────┬─────────────┘
                   │
                   ▼
     ┌───────────────────────────┐
     │   XBRL Fact Resolution     │  <-- Standard Taxonomies + Dimensional Fact Parsing
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
     │ Reconciliation & Quality  │  <-- Sum(Segments) ~ Total Revenue Check
     └─────────────┬─────────────┘
                   │
                   ▼
     ┌───────────────────────────┐
     │ Storage & Export Layer    │  <-- DuckDB / Parquet / Sankey JSON Schema
     └───────────────────────────┘
2. Component Specifications
2.1 Ingestion & Compliance Layer (ingestion/edgar_client.py)
The SEC enforces strict rate limits (10 requests per second) and requires a custom User-Agent header (Sample Company Name AdminContact@domain.com).

Client Architecture: Built on httpx or requests wrapped with tenacity for exponential backoff retries.

Primary Endpoints Used:

CIK Ticker Mapping: [https://www.sec.gov/files/company_tickers.json](https://www.sec.gov/files/company_tickers.json)

Company Facts (XBRL Dump): [https://data.sec.gov/api/xbrl/companyfacts/CIK](https://data.sec.gov/api/xbrl/companyfacts/CIK){cik10}.json

Company Concept Time-Series: [https://data.sec.gov/api/xbrl/companyconcept/CIK](https://data.sec.gov/api/xbrl/companyconcept/CIK){cik10}/{taxonomy}/{concept}.json

2.2 Taxonomy & Fact Resolution Engine (parser/taxonomy_mapper.py)
Financial metrics are tagged using standard US-GAAP taxonomies. Because companies may use alternative concepts over time, the engine relies on ordered concept fallback chains.

Top-Level Metric Fallback Mapping
Metric	Primary Concept Tag (us-gaap)	Secondary / Fallback Concept Tags
Total Revenue	Revenues	SalesRevenueNet, RevenueFromContractWithCustomerExcludingAssessedTax
Cost of Revenue	CostOfGoodsAndServicesSold	CostOfRevenue, CostOfGoodsSold
Operating Expenses	OperatingExpenses	Calculated: GrossProfit−OperatingIncome
Net Profit	NetIncomeLoss	ProfitLoss, NetIncomeLossAvailableToCommonStockholdersBasic
Segment Extraction Logic
Segment breakdown data is stored in Inline XBRL using Explicit Member Dimensions.

Target Axes:

us-gaap:StatementBusinessSegmentsAxis (Operating Segments)

us-gaap:ProductOrServiceAxis (Product Lines)

Extraction Flow:

Filter facts under revenue tags containing a non-empty dimensions object.

Parse the axis namespace and extract the specific segment name from the member taxonomy (e.g., aapl:IPhoneMember → "iPhone").

Group facts by fiscal period (fy, fp, form="10-K" or "10-Q").

3. Data Pipeline Implementation Schema
Python
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import httpx
import time

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

class IncomeStatementPayload(BaseModel):
    ticker: str
    cik: str
    fiscal_year: int
    fiscal_period: str
    total_revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    operating_expenses: Optional[float] = None
    net_profit: Optional[float] = None
    segments: List[SegmentRevenue] = Field(default_factory=list)

class EdgarIngestionEngine:
    def __init__(self, user_agent: str):
        self.headers = {"User-Agent": user_agent}
        self.base_url = "https://data.sec.gov/api/xbrl/companyfacts"
        self.last_request_time = 0.0

    def _rate_limit(self):
        # Enforce 0.12s delay between calls (safe bound for 10 req/sec limit)
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.12:
            time.sleep(0.12 - elapsed)
        self.last_request_time = time.time()

    def fetch_company_facts(self, cik: str) -> Dict:
        self._rate_limit()
        padded_cik = str(cik).zfill(10)
        url = f"{self.base_url}/CIK{padded_cik}.json"
        
        with httpx.Client(headers=self.headers) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
4. Reconciliation & Data Quality Gate (pipeline/reconciliation.py)
Company segment breakdowns often include intersegment eliminations or non-standard groupings. The data pipeline executes tolerance checks before exporting:

Reconciliation Error (%)= (Total Revenue/Total Revenue−∑Segment Revenue) ×100
- Rule 1 (Segment Sum Validation): If Reconciliation Error <5%, label as RECONCILED_EXACT.

- Rule 2 (Unallocated/Corporate Residual): If 5%≤Error≤15%, insert a balancing synthetic node: "Corporate / Unallocated Revenue".

- Rule 3 (Accounting Identity Guard): Ensure Net Profit≤Total Revenue (excluding anomalous negative edge-cases).

5. Downstream Target Schema (Sankey Ready Output)
The data processor outputs normalized JSON structured directly for Sankey visualization nodes:

JSON
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
6. Execution & Deployment Strategy
Task Scheduling: Orchestrated using Celery or Prefetch Cron Jobs running nightly off peak hours to track new 10-K / 10-Q filings via SEC RSS feed ([https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent](https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent)).

Persistence: Raw JSON saved to local DuckDB (sec_facts.duckdb) or S3 bucket formatted as partitioned Parquet files (/year=YYYY/ticker=TICKER/data.parquet).

make this whole architecture document to a md file

[ SEC EDGAR REST API / XBRL CompanyFacts ]
│
▼
┌───────────────────────────┐
│   Ingestion & Rate Limiter │  <-- 10 req/sec, User-Agent Header Compliance
└─────────────┬─────────────┘
│
▼
┌───────────────────────────┐
│   XBRL Fact Resolution     │  <-- Standard Taxonomies + Dimensional Fact Parsing
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
│ Reconciliation & Quality  │  <-- Sum(Segments) ~ Total Revenue Check
└─────────────┬─────────────┘
│
▼
┌───────────────────────────┐
│ Storage & Export Layer    │  <-- DuckDB / Parquet / Sankey JSON Schema
└───────────────────────────┘


---

## 2. Component Specifications

### 2.1 Ingestion & Compliance Layer (`ingestion/edgar_client.py`)
The SEC enforces strict rate limits (**10 requests per second**) and requires a custom `User-Agent` header (`Sample Company Name AdminContact@domain.com`).

* **Client Architecture:** Built on `httpx` or `requests` wrapped with `tenacity` for exponential backoff retries.
* **Primary Endpoints Used:**
  * **CIK Ticker Mapping:** `https://www.sec.gov/files/company_tickers.json`
  * **Company Facts (XBRL Dump):** `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json`
  * **Company Concept Time-Series:** `https://data.sec.gov/api/xbrl/companyconcept/CIK{cik10}/{taxonomy}/{concept}.json`

---

### 2.2 Taxonomy & Fact Resolution Engine (`parser/taxonomy_mapper.py`)

Financial metrics are tagged using standard US-GAAP taxonomies. Because companies may use alternative concepts over time, the engine relies on ordered concept fallback chains.

#### Top-Level Metric Fallback Mapping
| Metric | Primary Concept Tag (`us-gaap`) | Secondary / Fallback Concept Tags |
| :--- | :--- | :--- |
| **Total Revenue** | `Revenues` | `SalesRevenueNet`, `RevenueFromContractWithCustomerExcludingAssessedTax` |
| **Cost of Revenue** | `CostOfGoodsAndServicesSold` | `CostOfRevenue`, `CostOfGoodsSold` |
| **Operating Expenses** | `OperatingExpenses` | Calculated: $\\text{GrossProfit} - \\text{OperatingIncome}$ |
| **Net Profit** | `NetIncomeLoss` | `ProfitLoss`, `NetIncomeLossAvailableToCommonStockholdersBasic` |

#### Segment Extraction Logic
Segment breakdown data is stored in Inline XBRL using **Explicit Member Dimensions**.
* **Target Axes:**
  * `us-gaap:StatementBusinessSegmentsAxis` (Operating Segments)
  * `us-gaap:ProductOrServiceAxis` (Product Lines)
* **Extraction Flow:**
  1. Filter facts under revenue tags containing a non-empty `dimensions` object.
  2. Parse the axis namespace and extract the specific segment name from the member taxonomy (e.g., `aapl:IPhoneMember` $\\rightarrow$ "iPhone").
  3. Group facts by fiscal period (`fy`, `fp`, `form="10-K"` or `"10-Q"`).

---

## 3. Data Pipeline Implementation Schema

```python
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import httpx
import time

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

class IncomeStatementPayload(BaseModel):
    ticker: str
    cik: str
    fiscal_year: int
    fiscal_period: str
    total_revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    operating_expenses: Optional[float] = None
    net_profit: Optional[float] = None
    segments: List[SegmentRevenue] = Field(default_factory=list)

class EdgarIngestionEngine:
    def __init__(self, user_agent: str):
        self.headers = {"User-Agent": user_agent}
        self.base_url = "[https://data.sec.gov/api/xbrl/companyfacts](https://data.sec.gov/api/xbrl/companyfacts)"
        self.last_request_time = 0.0

    def _rate_limit(self):
        # Enforce 0.12s delay between calls (safe bound for 10 req/sec limit)
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.12:
            time.sleep(0.12 - elapsed)
        self.last_request_time = time.time()

    def fetch_company_facts(self, cik: str) -> Dict:
        self._rate_limit()
        padded_cik = str(cik).zfill(10)
        url = f"{self.base_url}/CIK{padded_cik}.json"
        
        with httpx.Client(headers=self.headers) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
4. Reconciliation & Data Quality Gate (pipeline/reconciliation.py)
Company segment breakdowns often include intersegment eliminations or non-standard groupings. The data pipeline executes tolerance checks before exporting:

\text{Reconciliation Error (\\%)} = \left| \frac{\text{Total Revenue} - \sum \text{Segment Revenue}}{\text{Total Revenue}} \right| \times 100
Rule 1 (Segment Sum Validation): If Reconciliation Error <5
, label as RECONCILED_EXACT.

Rule 2 (Unallocated/Corporate Residual): If 5
, insert a balancing synthetic node: "Corporate / Unallocated Revenue".

Rule 3 (Accounting Identity Guard): Ensure Net Profit≤Total Revenue (excluding anomalous negative edge-cases).

5. Downstream Target Schema (Sankey Ready Output)
The data processor outputs normalized JSON structured directly for Sankey visualization nodes:

JSON
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
6. Execution & Deployment Strategy
Task Scheduling: Orchestrated using Celery or Prefetch Cron Jobs running nightly off peak hours to track new 10-K / 10-Q filings via SEC RSS feed (https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent).

Persistence: Raw JSON saved to local DuckDB (sec_facts.duckdb) or S3 bucket formatted as partitioned Parquet files (/year=YYYY/ticker=TICKER/data.parquet).
"""

file_name = "sec_edgar_architecture.md"
with open(file_name, "w", encoding="utf-8") as f:
f.write(markdown_content)

print(f"File created: {file_name}")


```text?code_stdout&code_event_index=1
File created: sec_edgar_architecture.md

Your Markdown file is ready

MD icon
sec_edgar_architecture
 MD 
Open
I have generated and saved the complete SEC EDGAR financial data extraction system architecture into the file sec_edgar_architecture.md. It includes all specifications, ASCII component diagrams, fallback maps, Pydantic schemas, validation formulas, and deployment strategies.




Gemini is AI and can make mistakes.

Analyzing
# System Architecture: SEC EDGAR Financial & Segment Data Extractor (`edgar-parser-core`)

**Author:** Principal Data Engineer / Financial Systems Architect  
**Target Stack:** Python 3.11+, SEC EDGAR REST API, `edgartools`, Polars/Pandas, DuckDB, Pydantic  
**Primary Goal:** Programmatically fetch, normalize, and reconcile top-level income statement metrics and multidimensional segment breakdowns (Product Line / Business Unit) from free SEC EDGAR endpoints.

---

## 1. High-Level Architecture Overview

```
[ SEC EDGAR REST API / XBRL CompanyFacts ]
                   │
                   ▼
     ┌───────────────────────────┐
     │   Ingestion & Rate Limiter │  <-- 10 req/sec, User-Agent Header Compliance
     └─────────────┬─────────────┘
                   │
                   ▼
     ┌───────────────────────────┐
     │   XBRL Fact Resolution     │  <-- Standard Taxonomies + Dimensional Fact Parsing
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
     │ Reconciliation & Quality  │  <-- Sum(Segments) ~ Total Revenue Check
     └─────────────┬─────────────┘
                   │
                   ▼
     ┌───────────────────────────┐
     │ Storage & Export Layer    │  <-- DuckDB / Parquet / Sankey JSON Schema
     └───────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 Ingestion & Compliance Layer (`ingestion/edgar_client.py`)
The SEC enforces strict rate limits (**10 requests per second**) and requires a custom `User-Agent` header (`Sample Company Name AdminContact@domain.com`).

* **Client Architecture:** Built on `httpx` or `requests` wrapped with `tenacity` for exponential backoff retries.
* **Primary Endpoints Used:**
  * **CIK Ticker Mapping:** `https://www.sec.gov/files/company_tickers.json`
  * **Company Facts (XBRL Dump):** `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json`
  * **Company Concept Time-Series:** `https://data.sec.gov/api/xbrl/companyconcept/CIK{cik10}/{taxonomy}/{concept}.json`

---

### 2.2 Taxonomy & Fact Resolution Engine (`parser/taxonomy_mapper.py`)

Financial metrics are tagged using standard US-GAAP taxonomies. Because companies may use alternative concepts over time, the engine relies on ordered concept fallback chains.

#### Top-Level Metric Fallback Mapping
| Metric | Primary Concept Tag (`us-gaap`) | Secondary / Fallback Concept Tags |
| :--- | :--- | :--- |
| **Total Revenue** | `Revenues` | `SalesRevenueNet`, `RevenueFromContractWithCustomerExcludingAssessedTax` |
| **Cost of Revenue** | `CostOfGoodsAndServicesSold` | `CostOfRevenue`, `CostOfGoodsSold` |
| **Operating Expenses** | `OperatingExpenses` | Calculated: $\text{GrossProfit} - \text{OperatingIncome}$ |
| **Net Profit** | `NetIncomeLoss` | `ProfitLoss`, `NetIncomeLossAvailableToCommonStockholdersBasic` |

#### Segment Extraction Logic
Segment breakdown data is stored in Inline XBRL using **Explicit Member Dimensions**.
* **Target Axes:**
  * `us-gaap:StatementBusinessSegmentsAxis` (Operating Segments)
  * `us-gaap:ProductOrServiceAxis` (Product Lines)
* **Extraction Flow:**
  1. Filter facts under revenue tags containing a non-empty `dimensions` object.
  2. Parse the axis namespace and extract the specific segment name from the member taxonomy (e.g., `aapl:IPhoneMember` $\rightarrow$ "iPhone").
  3. Group facts by fiscal period (`fy`, `fp`, `form="10-K"` or `"10-Q"`).

---

## 3. Data Pipeline Implementation Schema

```python
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import httpx
import time

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

class IncomeStatementPayload(BaseModel):
    ticker: str
    cik: str
    fiscal_year: int
    fiscal_period: str
    total_revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    operating_expenses: Optional[float] = None
    net_profit: Optional[float] = None
    segments: List[SegmentRevenue] = Field(default_factory=list)

class EdgarIngestionEngine:
    def __init__(self, user_agent: str):
        self.headers = {"User-Agent": user_agent}
        self.base_url = "https://data.sec.gov/api/xbrl/companyfacts"
        self.last_request_time = 0.0

    def _rate_limit(self):
        # Enforce 0.12s delay between calls (safe bound for 10 req/sec limit)
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.12:
            time.sleep(0.12 - elapsed)
        self.last_request_time = time.time()

    def fetch_company_facts(self, cik: str) -> Dict:
        self._rate_limit()
        padded_cik = str(cik).zfill(10)
        url = f"{self.base_url}/CIK{padded_cik}.json"
        
        with httpx.Client(headers=self.headers) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
```

---

## 4. Reconciliation & Data Quality Gate (`pipeline/reconciliation.py`)

Company segment breakdowns often include intersegment eliminations or non-standard groupings. The data pipeline executes tolerance checks before exporting:

$$\text{Reconciliation Error (\%)} = \left| \frac{\text{Total Revenue} - \sum \text{Segment Revenue}}{\text{Total Revenue}} \right| \times 100$$

* **Rule 1 (Segment Sum Validation):** If Reconciliation Error $< 5\%$, label as `RECONCILED_EXACT`.
* **Rule 2 (Unallocated/Corporate Residual):** If $5\% \le \text{Error} \le 15\%$, insert a balancing synthetic node: `"Corporate / Unallocated Revenue"`.
* **Rule 3 (Accounting Identity Guard):** Ensure $\text{Net Profit} \le \text{Total Revenue}$ (excluding anomalous negative edge-cases).

---

## 5. Downstream Target Schema (Sankey Ready Output)

The data processor outputs normalized JSON structured directly for Sankey visualization nodes:

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

## 6. Execution & Deployment Strategy

* **Task Scheduling:** Orchestrated using **Celery** or **Prefetch Cron Jobs** running nightly off peak hours to track new `10-K` / `10-Q` filings via SEC RSS feed (`https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent`).
* **Persistence:** Raw JSON saved to local DuckDB (`sec_facts.duckdb`) or S3 bucket formatted as partitioned Parquet files (`/year=YYYY/ticker=TICKER/data.parquet`).
sec_edgar_architecture.md
Displaying sec_edgar_architecture.md.
