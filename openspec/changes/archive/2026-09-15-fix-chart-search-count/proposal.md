## Why

The **Find in chart** counter under the search field (`#search-count`) can report more lines than the chart shows. `applyFilters()` in `src/main.js` counts a line as a hit whenever its text matches, so two kinds of hidden lines still get counted:
- lines from a source hidden by the **Show** filter (e.g. MIC lines while "SYS only" is selected);
- lines in the Live and File transcripts together, including the tab that isn't showing.

The number is meant to tell the user how many matching lines they can see, so a wrong number misleads.

## What Changes

- **Count only what's visible:** the counter counts only lines that match the search, pass the **Show** filter, and belong to the chart currently shown.
- **Recount on tab switch:** switching between Live and File re-runs the filter, so the count follows the visible chart. New transcript lines already trigger a recount.
- **Unchanged:** which lines are hidden or highlighted, and the "1 line" / "N lines" wording.
- **No layout or visual change:** only the number's value changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `desktop-gui`: adds a requirement that the chart search counter reports the number of matching lines visible in the shown chart. No existing requirement covers chart search.

## Impact

- **`src/main.js`:** `applyFilters()` counts hits from the active chart's list only, and requires the line to pass the **Show** filter. `selectTab()` calls `applyFilters()`.
- **`tests/test_gui.py`:** a new scenario for the counter.
- **Unaffected:** no Rust, engine, dependency or layout changes.
