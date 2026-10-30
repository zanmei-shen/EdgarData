# DeskSankey

DeskSankey is a small local UI app for generating and editing Sankey diagrams from the shared `edgar-parser-core` Sankey graph contract.

## What it does

- Accepts a stock ticker in a graphical interface
- Lets the user choose a fiscal period type such as year or quarter
- Resolves the ticker to a SEC company record when live mode is enabled
- Loads a normalized income statement payload
- Displays editable income and expense tables
- Generates a Tencent-style Sankey preview
- Includes a color panel so the user can customize each segment and branch in the Sankey diagram
- Lets the user modify values before export
- Saves the final graph JSON to `DeskSankey/data/sankey_data.json`
- Provides a download button for the generated JSON

## Stack

- Streamlit for the UI
- Plotly for Sankey rendering
- Pandas for table editing and data handling
- The shared `edgar-parser-core` exporter and schema for graph generation

## Project layout

```text
DeskSankey/
├── data/
│   └── sankey_data.json
├── app.py
├── requirements.txt
└── README.md
```

## Run locally

From the repository root:

```bash
pip install -r DeskSankey/requirements.txt -e .
streamlit run DeskSankey/app.py
```

If you want to use the UI against the local EDGAR extractor package, install the workspace in editable mode so `DeskSankey` can import `edgardata` directly.

## Input and output

The app currently expects a ticker and a normalized income statement payload. In v1 it can use a sample payload when live ticker resolution is not available, but the design supports wiring in the EDGAR pipeline later.

Before generating, the user can choose a fiscal year and either an annual period (`FY`) or a quarter (`Q1`, `Q2`, `Q3`, `Q4`). The selected period is passed through to the payload and the Sankey graph label.

When live mode is selected, the app will resolve the ticker against SEC company tickers, fetch company facts, and show the matched company name and CIK in the interface before rendering the Sankey preview. If live lookup fails, it falls back to sample data so the editing workflow remains usable.

The output JSON follows the layered Sankey contract:

- `ticker`
- `period`
- `currency`
- `nodes`
- `links`
- `top_level`
- `segment_breakdown`

## UI behavior

The user flow is:

1. Enter ticker
2. Click Generate
3. Review income table
4. Adjust values if needed
5. Pick colors for individual segments and branches if desired
6. Preview Sankey diagram
7. Download JSON

## Notes

This app is intentionally thin. All graph logic should stay in `edgar-parser-core`, and DeskSankey should only handle UI, editing, preview, and export actions.
