
Conversation with Gemini
I want to parse edgar financial data. Is there already existig edgar data parser?

Yes, several popular, actively maintained open-source libraries and APIs specialize in parsing SEC EDGAR financial disclosures. Depending on whether you need raw financial statement numbers (XBRL/iXBRL) or narrative sections (HTML text), different tools excel in specific areas.

Popular Open-Source Python Parsers
sec-parser  
Read the Docs

Best For: Qualitative narrative extraction (10-K, 10-Q, 8-K).  
GitHub

How it works: Uses semantic HTML segmentation to convert raw SEC filings into a structured semantic tree. Excellent for extracting specific sections like Risk Factors or MD&A for LLM/RAG pipelines.  
Read the Docs
+ 1

Install: pip install sec-parser

edgar-tools (edgartools)

Best For: High-level object-oriented access to SEC filings, financial statements, and company disclosures.

How it works: Provides easy, Pythonic access to download and parse 10-K, 10-Q, 8-K, Form 4 insider trading, and proxy statements into Pandas DataFrames or text chunks.

Install: pip install edgartools

edgar-parser  
GitHub

Best For: Self-hosted local extraction of XBRL financial facts and period matching.  
GitHub

How it works: Resolves XBRL namespaces, handles fiscal period comparisons, and normalizes line items across 10-K/10-Q filings.  
GitHub

Install: pip install edgar-parser  
GitHub

sec-edgar-downloader

Best For: Batch-downloading raw SEC filings (HTML, TXT, XML) to local disk before running custom parsers.

Install: pip install sec-edgar-downloader

Official SEC EDGAR APIs (No Third-Party Library Needed)
If you only need structured numerical facts (Balance Sheet, Income Statement, Cash Flow), the SEC offers a free REST API that returns clean JSON:  
Apify

Company Facts API: [https://data.sec.gov/api/xbrl/companyfacts/CIK](https://data.sec.gov/api/xbrl/companyfacts/CIK){cik.zfill(10)}.json

Returns all XBRL concepts filed by a company (GAAP, IFRS, DEI taxonomy) formatted in JSON.  
Reddit

Company Concept API: [https://data.sec.gov/api/xbrl/companyconcept/CIK](https://data.sec.gov/api/xbrl/companyconcept/CIK){cik}/us-gaap/{concept}.json

Pulls a specific financial metric across time (e.g., Revenues or Assets).

Note on SEC Rate Limits: When fetching data directly from sec.gov, you must declare a user-agent header formatted as User-Agent: Sample Company Name AdminContact@domain.com. The SEC enforces a maximum rate limit of 10 requests per second.  
SEC.gov
+ 1

I want to generate income sankey diagram like this, how do I get data?

To build an income statement Sankey diagram like this, you need two distinct types of data: top-level financial metrics (Total Revenue, Cost of Revenue, Operating Expenses, Net Profit) and segment breakdown data (Revenue by Business Segment/Product Line).

Here is where to source the exact data and how to extract it.

Primary Data Sources
SEC Filings (For US-listed companies):

Top-Level Metrics: Form 10-K (Annual) or 10-Q (Quarterly) under Item 8: Financial Statements and Supplementary Data (Consolidated Statements of Operations / Income Statement).

Segment Revenue: Found in the Notes to Consolidated Financial Statements (specifically the Segment Reporting note).

Investor Relations (IR) Presentations & Earnings Releases:

Companies routinely release quarterly Earnings Presentations (PDF) or supplemental data tables alongside their financial reports. These slides are often the cleanest source for revenue breakdowns by product, division, or geography.

HKEX / International Filings (For foreign firms like Tencent):

Annual and quarterly interim announcements available on the HKEXnews portal or the company's IR site under financial reports.

Methods to Extract and Structure the Data
Using Open-Source Python Parsers:

edgartools / sec-parser: Query the company's CIK to extract income statement line items directly into Pandas DataFrames.

sec-api / SEC XBRL JSON API: Fetch standard US-GAAP income statement metrics automatically via structured JSON endpoints.

Financial Data APIs (Pre-parsed):

If you want to bypass manual parsing, paid or freemium financial APIs provide pre-structured segment data:

Financial Modeling Prep (FMP): Offers endpoints for Revenue Product Segmentation and Income Statement.

QuickFS / Yahoo Finance / Alpha Vantage: Good for standard income statement metrics.

Structuring Data for Sankey Generators
Sankey diagrams rely on a Source → Target → Value flow format. You can map an income statement into three main stages:

Stage	Source Node	Target Node	Value Example
Stage 1: Revenue Inflow	Gaming	Revenue	65.9B
Social Networks	Revenue	32.5B
Marketing Services	Revenue	43.6B
FinTech & Business Services	Revenue	60.3B
Stage 2: Gross Split	Revenue	Cost of Revenue	86.4B
Revenue	Gross Profit	118.4B
Stage 3: Operating Split	Gross Profit	Operating Expenses	51.1B
Gross Profit	Operating Profit	67.3B
Stage 4: Net Profit Split	Operating Profit	Net Profit	58.0B
Operating Profit	Tax	11.7B
Operating Profit	R&D / SG&A / Other	...
Diagram Creation Tools
Code/Libraries: plotly.graph_objects.Sankey (Python), d3-sankey (JavaScript), or ggsankey (R).

No-Code Web Tools: SankeyMATIC or Flourish (paste the Source-Target-Value text directly to render).

can top-level financial metrics (Total Revenue, Cost of Revenue, Operating Expenses, Net Profit) get from edgartools or sec-api, how and where can I get segment breakdown data (Revenue by Business Segment/Product Line).

1. How to Get Top-Level Financial Metrics
Both edgartools and sec-api allow you to fetch standard financial statements (Income Statement, Balance Sheet, Cash Flow Statement) programmatically.

Option A: Using edgartools (Free & Open Source)
edgartools parses XBRL data directly from EDGAR filings and formats financial statements into standard pandas DataFrames.

Python
from edgar import Company, set_identity

# Required by SEC: set user agent
set_identity("YourName name@domain.com")

# Fetch company by ticker or CIK
company = Company("AAPL")

# Get latest 10-K filing
filing = company.get_filings(form="10-K").latest(1)

# Extract Financial Statements
financials = filing.obj().financials

# Access the Income Statement
income_statement = financials.income_statement.to_dataframe()
print(income_statement)
Option B: Using sec-api (Paid Service with Free Tier)
sec-api.io provides a pre-parsed FinancialStatements API endpoint that extracts income statement line items directly in JSON:

Python
from sec_api import FinancialDataApi

api = FinancialDataApi("YOUR_API_KEY")

# Extract Income Statement for Apple
income_stmt = api.get_income_statement(
    ticker="AAPL", 
    form_type="10-K", 
    period="FY"
)
# Returns keys like 'TotalRevenue', 'CostOfRevenue', 'OperatingExpenses', 'NetIncomeLoss'
2. How and Where to Get Segment Breakdown Data
Segment data (revenue by business division, product line, or geography) is slightly trickier because SEC rules (FASB ASC 280) require companies to report segment information in the footnotes rather than the main face of the income statement.

Here are the primary ways to retrieve segment data:

Method 1: Using edgartools (Parsing Footnotes or XBRL Fact Sets)
edgartools allows you to inspect the XBRL facts directly or search the Note disclosures in 10-K filings.

Extracting XBRL Segment Dimensions:
Segment breakdowns are tagged in Inline XBRL using custom or standard dimensions (e.g., us-gaap:StatementBusinessSegmentsAxis or us-gaap:ProductOrServiceAxis).

Python
from edgar import Company, set_identity

set_identity("YourName name@domain.com")
company = Company("AAPL")
filing = company.get_filings(form="10-K").latest(1)

# Access all XBRL facts in the filing
facts = filing.obj().xbrl.facts

# Filter facts matching revenue by segment or product axis
segment_facts = [
    fact for fact in facts 
    if "Revenue" in fact.concept and fact.dimensions
]
Parsing Segment Footnote Text:
You can extract the full Segment Reporting footnote using sec-parser or edgartools to view structured tables:

Python
doc = filing.obj()
# Access specific document sections or tables under Segment Reporting
Method 2: Financial Modeling Prep (FMP) API (Easiest Method)
If you prefer a ready-to-use API that normalizes segment revenue into structured JSON without parsing XBRL dimensions manually, Financial Modeling Prep (FMP) provides dedicated segment endpoints:

Product/Business Segment Endpoint:
[https://financialmodelingprep.com/api/v4/revenue-product-segmentation?symbol=AAPL&structure=flat&apikey=YOUR_KEY](https://financialmodelingprep.com/api/v4/revenue-product-segmentation?symbol=AAPL&structure=flat&apikey=YOUR_KEY)

Geographic Segment Endpoint:
[https://financialmodelingprep.com/api/v4/revenue-geographic-segmentation?symbol=AAPL&structure=flat&apikey=YOUR_KEY](https://financialmodelingprep.com/api/v4/revenue-geographic-segmentation?symbol=AAPL&structure=flat&apikey=YOUR_KEY)

Example Response:

JSON
{
  "2023-09-30": {
    "iPhone": 200583000000,
    "Mac": 29357000000,
    "iPad": 28300000000,
    "Wearables, Home and Accessories": 39845000000,
    "Services": 85200000000
  }
}
Method 3: SEC Company Facts REST API (Free Official Source)
The SEC provides a free public JSON API containing all XBRL facts reported by a company.

Endpoint: [https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json](https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json)

How it works: Under facts -> us-gaap -> RevenueFromContractWithCustomerExcludingAssessedTax -> units -> USD, items containing segment tags will include a frame or segment key detailing the specific product line or operating segment.

you are 10 years experienced software engineer focus on stock data process, write an architecture of python system md file to parse extract data for top-level financial metrics (Total Revenue, Cost of Revenue, Operating Expenses, Net Profit) and segment breakdown data (Revenue by Business Segment/Product Line). using free data api

System Architecture: SEC EDGAR Financial & Segment Data Extractor (edgar-parser-core)
Author: Principal Data Engineer / Financial Systems Architect

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

Reconciliation Error (%)= 

​
  
Total Revenue
Total Revenue−∑Segment Revenue
​
  

​
 ×100
Rule 1 (Segment Sum Validation): If Reconciliation Error <5%, label as RECONCILED_EXACT.

Rule 2 (Unallocated/Corporate Residual): If 5%≤Error≤15%, insert a balancing synthetic node: "Corporate / Unallocated Revenue".

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
