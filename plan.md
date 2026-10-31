# Plan: Match Live EDGAR Sankey Data

## Progress

- Corrected operating-expense derivation to prefer aligned revenue, cost-of-revenue, and operating-income facts.
- Preserved reconciled R&D, Sales & Marketing, and General & Administrative details.
- Added optional `parent_id` metadata for nested revenue segments.
- Added validation for invalid fiscal periods such as `NONE2026`.
- Added protection against negative Sankey link values.
- Added regression tests. Current result: 26 tests passing.
- Added a dependency-free Inline XBRL filing-table fallback for Google Search, YouTube ads, Google Network, and subscriptions/platforms/devices.
- Live validation confirmed those four values sum exactly to Google Services revenue: $96.302B.
- Current result: 27 tests passing.
- Remaining work: regenerate the app export after these changes and finish any visual positioning refinements.

## Implementation Plan

1. Define the Google Q3 FY2026 reference contract from `goog.jpg`:
   - Revenue: approximately $127.6B
   - Cost of revenue: approximately $51.4B
   - Gross profit: approximately $76.2B
   - Operating expenses: approximately $35.6B
   - Operating profit: approximately $40.6B
   - Net income: approximately $26.5B

2. Enforce graph invariants:
   - Sankey links must be non-negative.
   - Subtotal flows must balance within tolerance.
   - Revenue segments must reconcile to total revenue, with an explicit residual when necessary.

3. Strengthen live fact resolution:
   - Keep all metrics aligned to the same accession, period, fiscal year, and filing form.
   - Prefer calculated operating expenses when revenue, cost, and operating income are available.
   - Use aggregate operating expenses only as a fallback.
   - Reject invalid fiscal periods such as `NONE`.

4. Extend segment extraction:
   - Preserve parent-child relationships.
   - Support Google-specific/custom revenue concepts.
   - Deduplicate overlapping parent facts, child facts, and multidimensional intersections.
   - Add residual or unallocated revenue when disclosed segments do not sum to reported revenue.
   - Add fixtures for Google Services, Search, YouTube, Network/AdMob, Google Play, Cloud, and Other.

5. Extend the data model with backward-compatible hierarchy metadata.

6. Update the Sankey exporter:
   - Detailed revenue nodes flow into parent groups.
   - Parent groups flow into Revenue.
   - Revenue splits into cost of revenue and gross profit.
   - Operating expenses split into R&D, S&M, and G&A when available.
   - Adjustments use separate positive-valued income or expense nodes.

7. Improve Plotly layout to match `goog.jpg`:
   - Detailed revenue on the left.
   - Revenue and gross profit in the center.
   - Cost and operating expenses as downward branches.
   - Operating profit, tax, and net income on the right.
   - Use stable stage ordering or explicit positions where needed.

8. Add tests for:
   - Google operating-expense reconciliation.
   - Period consistency.
   - Nested revenue segments.
   - Residual revenue.
   - Balanced subtotal flows.
   - Non-negative links.
   - Correct period formatting.

9. Run the full test suite and a mocked Google Q3 FY2026 export.

10. Run the app against live EDGAR, compare the exported JSON and rendering with `goog.jpg`, and regenerate `DeskSankey/data/sankey_data.json` only from verified live data.

## Relevant Files

- `DeskSankey/app.py`
- `edgardata/pipeline/financials.py`
- `edgardata/parser/taxonomy_mapper.py`
- `edgardata/parser/segment_parser.py`
- `edgardata/models/schema.py`
- `edgardata/exports/sankey_exporter.py`
- `tests/test_taxonomy_mapper.py`
- `tests/test_segment_parser.py`
- `tests/test_sankey_graph.py`
- `goog.jpg`
- `DeskSankey/data/sankey_data.json`

## Verification

- Run `pytest` from the repository root.
- Confirm all link values are greater than or equal to zero.
- Confirm subtotal incoming and outgoing values balance.
- Run Streamlit with a valid SEC User-Agent.
- Compare desktop and narrow viewport renderings against `goog.jpg`.
