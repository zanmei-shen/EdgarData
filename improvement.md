Redesign the current Sankey income-statement visualization to resemble a polished financial infographic similar to the provided goog.jpg example.

#Visual Hierarchy

Current issues:

Labels are small and difficult to read.
All nodes have similar importance.
No obvious focal point.

Requirements:

Create a large title at top center.
Use 2-4x larger fonts than current version.
Emphasize key metrics:
Revenue
Gross Profit
Operating Profit
Net Profit

Example:

Revenue
$127.6B
+25% YoY


should appear as large stacked text.

#Color Narrative
Revenue Sources

Blue / Gold

Search = Blue
YouTube = Blue
Cloud = Gold
Subscriptions = Gold

Profits

Green

Gross Profit
Operating Profit
Net Profit

Expenses

Red

Cost of Revenue
R&D
Sales & Marketing
Tax
Other Expenses


Requirements:

Link color must match category.
Profit flows green.
Expense flows red.
Revenue streams blue/gold.
Transparency 40-60%.

#Improve Layout

Current:

Nodes are evenly distributed.
Lots of empty space.

Target:

Create a storytelling pipeline:

Revenue Source
     ↓
Revenue
     ↓
Gross Profit
     ↓
Operating Profit
     ↓
Net Profit


Requirements:

Arrange important nodes in a nearly straight horizontal path.
Place expense nodes underneath the profit path.
Place final profit node at far right.

#Rich Labels

Current:

Revenue
$127.6B


Target:

Revenue
$127.6B
+25% YoY


Additional examples:

Gross Profit
$76.2B
60% Margin

Operating Profit
$40.6B
32% Margin


Requirements:

Each node supports:

Primary label
Value
Secondary metric
Margin %
Growth %

#Typography

Requirements:

Font

Use modern sans-serif:

Inter
Roboto
Google Sans
Segoe UI

Sizes

Title: 60–100px

Major node: 28–42px

Value: 24–36px

Annotation: 16–22px

Current font is too small.

#Remove Generic Sankey Appearance

Current chart appears generated directly from Plotly/ECharts/D3 defaults.

Requirements:

Hide chart-library styling.
Round node corners.
Add subtle shadows.
Increase node width.

Example:

border-radius: 4px
shadow blur: 6px


Nodes should look like infographic blocks, not thin bars.

#Link Styling

Requirements:

Smooth Bezier curves.
Higher opacity near source.
Softer fade toward destination.

Link widths should visually dominate the design.

Current links feel secondary.

Target:

Links = major visual element.
Nodes = anchors.

#Add Explanatory Subtitles

Examples:

Google Cloud
$30.7B
+106% YoY

R&D
$20.6B
16% of Revenue

Sales & Marketing
$8.8B
7% of Revenue


Requirements:

Support multi-line annotations under each node.

#Spacing

Requirements:

Increase:

node spacing vertically by 30-50%
annotation spacing by 20-30%
title spacing from chart by 40-60px

Avoid label overlap.

#Financial Storytelling Rules

Priority order:

Revenue Sources
      ↓
Revenue
      ↓
Gross Profit
      ↓
Operating Profit
      ↓
Net Profit


Everything else should visually support this story.

Expenses should not compete visually with profit metrics.
