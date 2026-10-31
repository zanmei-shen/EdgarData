Ticker Search & Fiscal Period UX Enhancements Requirements
Overview

This document summarizes the requested enhancements and bug fixes for the Ticker Search experience and Fiscal Period defaults.

1. Ticker Field Company Name Resolution
Requirement

Allow users to enter either a ticker symbol or a company name in the Ticker field.

Expected Behavior
If a valid ticker is entered, retain the ticker value.
If a company name is entered, automatically resolve it to the corresponding ticker symbol.
Convert the displayed/stored value to the official ticker symbol.
Support both ticker-based and company-name-based searches.
Examples
User Input	ResultMicrosoft	MSFT
Apple	AAPL
Alphabet	GOOGL
Tesla	TSLA
MSFT	MSFT
2. Enhanced Company Matching
Requirement

Improve company name resolution accuracy.

Features
Implement punctuation-normalized matching.
Ignore punctuation, special characters, and formatting differences during lookup.
Support legacy company aliases and alternate names.
Examples
Input	ResultFacebook	META
Google	GOOGL
Alphabet	GOOGL
3. Ticker Search Autocomplete
Requirement

Provide real-time suggestions while users type.

Expected Behavior
Display matching companies and ticker symbols as soon as the user begins typing.
Update suggestions dynamically with every keystroke.
Allow searching by:
Ticker symbol
Company name
Allow users to click a suggestion to populate the ticker field.
Example Suggestions

Input: m

MSFT – Microsoft
META – Meta Platforms
MU – Micron Technology

Input: mic

MSFT – Microsoft
MU – Micron Technology
4. Ticker Field Suggestion Consistency
Issue

The Company field currently displays a suggestion list when focused or clicked, but the Ticker field does not appear to provide similar behavior.

Requirement

Align the Ticker field behavior with the Company field.

Expected Behavior
Show a suggestion dropdown when:
The field gains focus
The user clicks into the field
The user begins typing
Display both ticker symbols and company names.
Dynamically refine suggestions as the user types.
5. Enter Key Processing Bug
Issue

The Ticker field occasionally does not process input after the first Enter key press.

Observations
Users sometimes need to press Enter twice before the field value updates.
This behavior existed before the company-name-to-ticker resolution feature was implemented.
The root cause may be related to Enter-key event handling rather than ticker resolution logic.
Expected Behavior
A single Enter key press should:
Process the input.
Trigger company-name resolution when applicable.
Update the field value immediately.
6. Fiscal Year Default Value
Current Behavior

The Fiscal Year field defaults to a hardcoded value of 2025.

Requirement

Set the default value dynamically based on the current calendar year.

Examples
Current Year	Default Fiscal Year2026	2026
2027	2027
7. Fiscal Period Type Default
Current Behavior

The Fiscal Period Type defaults to Year.

Requirement

Change the default Fiscal Period Type to Quarter.

Expected Behavior
Default Period Type = Quarter.
Default Fiscal Quarter = Previous completed quarter.
Examples
Current Quarter	Default SelectionQ1 2027	Q4 2026
Q2 2027	Q1 2027
Q3 2027	Q2 2027
Q4 2027	Q3 2027
Acceptance Criteria
Users can enter either a company name or ticker symbol in the Ticker field.
Company names are automatically resolved to ticker symbols.
Legacy company names and aliases are supported.
Punctuation-normalized matching is implemented.
Real-time autocomplete suggestions appear while typing.
Ticker field displays suggestions when focused, clicked, or typed into.
Pressing Enter once consistently processes the value.
Fiscal Year defaults to the current year.
Fiscal Period Type defaults to Quarter.
The default quarter automatically selects the most recently completed quarter.