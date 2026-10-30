# Report guide

## Audience and question

Mobility planners and operations analysts. How does observed rental demand vary across operating hours, seasons and weather conditions?

## Reading the report

1. Start on the overview with all slicers cleared and compare KPIs with the snapshot totals in README.md.
2. Select a segment using the dropdown slicers. Hover over a rate chart to inspect its supporting counts.
3. Use the second page for segment comparisons and the third for coverage and interpretation constraints.
4. Clear visual selections before comparing a filtered view with the full-data snapshot.

## Design decisions

Navy masthead, consistent section spacing, white panels and one domain accent establish hierarchy. Color is supplementary: chart titles, axes, numeric formats and table labels communicate meaning without color alone. The native report includes visual alternative text and unique keyboard tab-order values. Keyboard behavior and screen-reader output still require application verification. Page size is 1360 × 880; use Fit to page in Desktop.

## Native acceptance checklist — pending

- Configure DataRoot and refresh all tables without M errors.
- Confirm all overview cards match the supplied summary under cleared filters.
- Verify each of the three dropdowns changes the intended measures; clear all selections between checks.
- Verify category tooltips show supporting counts and that chronologically ordered charts remain ordered.
- Check all three pages at Fit to page and 100% zoom for clipping, title overlap and table scroll behavior.
- Navigate with the keyboard and inspect alternative text with a screen reader.
- Save a PBIX only after these checks; do not claim a published Service dashboard before publication succeeds.

## Completed checks

Source-file hashes, cleaning totals, dimension-key uniqueness, foreign-key coverage, field references, JSON schema structure and canvas bounds were checked by Python. These do not execute the Power BI engines.
