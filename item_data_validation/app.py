import io
import os
import pandas as pd
import streamlit as st

from validate_items import (
    CHECK_COLS, CHECK_LABELS, bad_data_cells, is_pass, load_reference, run_checks, summary
)

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
DEMO_ITEMS = os.path.join(DATA_DIR, "validation_data.xlsx")
DEMO_REF   = os.path.join(DATA_DIR, "reference_data.xlsx")

# Bootstrap colours borrowed from Bootstrap alert classes so the palette
# is immediately recognisable without a legend.
PASS_COLOR = "#d4edda"   # green — Bootstrap .alert-success
FAIL_COLOR = "#f8d7da"   # red   — Bootstrap .alert-danger

st.set_page_config(page_title="Item Data Validation", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar — data source selection
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("Data sources")

    data_source = st.radio(
        "Data source",
        ["Demo data", "Upload own data"],
        index=0,
        horizontal=True,
    )

    if data_source == "Demo data":
        items_file = DEMO_ITEMS
        ref_file   = DEMO_REF
    else:
        items_file = st.file_uploader("Item data (.xlsx)", type="xlsx")
        ref_file   = st.file_uploader("Reference data (.xlsx)", type="xlsx")

    st.divider()
    # Column requirements shown here so the user can check their file before
    # uploading, rather than getting a cryptic KeyError after upload.
    st.markdown(
        "**Reference data** must contain columns: "
        "`product_group_id`, `description_en`, `basic_name`."
    )
    st.markdown(
        "**Item data** must contain columns: "
        "`item_id`, `product_group`, `basic_name`, `specification`, "
        "`description_en`, `description_fi`, `description_de`, `product_code`, `status`."
    )
    st.caption(
        "Column names are fixed in this demo version. "
        "A production implementation would support configurable column mapping."
    )

# ---------------------------------------------------------------------------
# Load and validate
# ---------------------------------------------------------------------------
st.title("Item Data Validation")
st.markdown(
    "Example of automated data validation against item master data standardisation rules. "
    "Each item is checked across four categories:"
)
st.markdown(
    "- **Reference catalogue** — product group codes and basic names must match approved values\n"
    "- **Field content** — forbidden symbols, uppercase convention, no extra spaces\n"
    "- **Field length** — ERP import limits (descriptions max 40 chars, part numbers max 30)\n"
    "- **Cross-field consistency** — specification and basic name must appear in all language descriptions"
)

if not items_file or not ref_file:
    st.info("Upload item data and reference data, or enable demo data in the sidebar.")
    st.stop()

try:
    items = pd.read_excel(items_file)
    ref   = load_reference(ref_file)
except Exception as e:
    st.error(f"Could not read files: {e}")
    st.stop()

# run_checks appends one result column per check to a copy of items.
results = run_checks(items, ref)
summ    = summary(results)

# ---------------------------------------------------------------------------
# KPI row — three headline numbers at the top
# ---------------------------------------------------------------------------
total     = len(results)
# A row is "failed" if at least one check did not pass.
any_fail  = results.apply(
    lambda row: any(not is_pass(c, row[c]) for c in CHECK_COLS), axis=1
)
items_fail = any_fail.sum()
pass_rate  = (total - items_fail) / total

col1, col2, col3 = st.columns(3)
col1.metric("Total items",       total)
col2.metric("Items with errors", items_fail)
col3.metric("Overall pass rate", f"{pass_rate:.0%}")

st.divider()

# ---------------------------------------------------------------------------
# Check summary table — one row per check, colour-coded pass rate
# ---------------------------------------------------------------------------
st.subheader("Check summary")

def colour_pass_rate(val):
    """
    Green  = 100 %  (no errors at all)
    Yellow = 90–99 % (minor issues, worth a look)
    Red    < 90 %  (systematic problem that needs attention)
    """
    pct = int(val.strip("%"))
    if pct == 100:
        return f"background-color: {PASS_COLOR}"
    if pct >= 90:
        return "background-color: #fff3cd"   # Bootstrap .alert-warning
    return f"background-color: {FAIL_COLOR}"

styled = summ.style.map(colour_pass_rate, subset=["Pass rate"])
st.dataframe(styled, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Item-level results table with filters
# ---------------------------------------------------------------------------
st.subheader("Item-level results")

filter_option = st.radio(
    "Show",
    ["All items", "Items with errors only"],
    horizontal=True,
)

# Multiselect lets the user drill into one specific check (e.g. "show me
# everything that failed the uppercase check") without writing any queries.
selected_checks = st.multiselect(
    "Filter by failed check",
    options=list(CHECK_LABELS.values()),
    default=[],
    placeholder="All checks",
)

view = results.copy()

if filter_option == "Items with errors only":
    mask = view.apply(lambda row: any(not is_pass(c, row[c]) for c in CHECK_COLS), axis=1)
    view = view[mask]

if selected_checks:
    # Invert CHECK_LABELS to map display name → column name for filtering.
    col_map = {v: k for k, v in CHECK_LABELS.items()}
    selected_cols = [col_map[s] for s in selected_checks]
    mask2 = view.apply(lambda row: any(not is_pass(c, row[c]) for c in selected_cols), axis=1)
    view = view[mask2]

st.caption(f"Showing {len(view)} of {total} items")

# Show only the most diagnostic item columns alongside the check results.
# Description_fi and _de are omitted here to keep the table readable;
# they are available in the downloaded Excel.
display_cols = ["item_id", "product_group", "basic_name", "specification",
                "description_en", "product_code", "status"]
display_cols = [c for c in display_cols if c in view.columns]
check_display = view[display_cols + CHECK_COLS].rename(columns=CHECK_LABELS)

# Compute which data cells are implicated in failed checks.
bad = bad_data_cells(view)


def _colour_data_cells(df):
    """Highlight data cells that are implicated in at least one failed check."""
    result = pd.DataFrame("", index=df.index, columns=df.columns)
    for col in display_cols:
        if col in bad.columns:
            result[col] = bad[col].map(
                lambda x: f"background-color: {FAIL_COLOR}" if x else ""
            )
    return result


def colour_cell(val):
    """
    Colour individual check-result cells.

    Boolean checks (product_group, basic_name, name_in_desc) arrive as
    Python bool. String checks arrive as "ok" or an error description.
    "specification empty" gets warning yellow rather than red because
    it may be intentional (some item types have no model designator).
    """
    if isinstance(val, bool):
        return f"background-color: {PASS_COLOR if val else FAIL_COLOR}"
    s = str(val).strip().lower()
    if s in ("ok", "true"):
        return f"background-color: {PASS_COLOR}"
    if s == "false":
        return f"background-color: {FAIL_COLOR}"
    if s == "specification empty":
        return "background-color: #fff3cd"
    if s:   # any other non-empty string = a list of offending columns
        return f"background-color: {FAIL_COLOR}"
    return ""


check_label_cols = list(CHECK_LABELS.values())
styled_detail = (
    check_display.style
    .apply(_colour_data_cells, axis=None)   # red on bad data cells
    .map(colour_cell, subset=check_label_cols)   # green/red/yellow on check columns
)
st.dataframe(styled_detail, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Download — three sheets: coloured results, summary, original data
# ---------------------------------------------------------------------------
st.divider()


def _apply_excel_colours(ws, df):
    """
    Colour cells in the Excel results worksheet after writing.

    openpyxl uses 1-based indexing; row 1 is the header, data starts at row 2.
    Two passes:
      1. Data cells — red where a check implicates that column.
      2. Check columns — green / yellow / red based on pass/fail/warning.
    Doing data cells first means check columns always win if they overlap.
    """
    from openpyxl.styles import PatternFill

    pass_fill = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
    fail_fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
    warn_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")

    col_index = {name: i + 1 for i, name in enumerate(df.columns)}

    # Pass 1 — highlight data cells that are implicated in a failed check
    bad = bad_data_cells(df)
    for col_name, series in bad.items():
        if col_name not in col_index:
            continue
        excel_col = col_index[col_name]
        for row_idx, is_bad in enumerate(series, start=2):
            if is_bad:
                ws.cell(row=row_idx, column=excel_col).fill = fail_fill

    # Pass 2 — colour each check-result column green / yellow / red
    for check_col in CHECK_COLS:
        if check_col not in col_index:
            continue
        excel_col = col_index[check_col]
        for row_idx, val in enumerate(df[check_col], start=2):
            if str(val).strip().lower() == "specification empty":
                fill = warn_fill
            elif is_pass(check_col, val):
                fill = pass_fill
            else:
                fill = fail_fill
            ws.cell(row=row_idx, column=excel_col).fill = fill


buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    results.to_excel(writer, sheet_name="results", index=False)
    summ.to_excel(writer, sheet_name="summary", index=False)
    # Original item data without check columns — useful for side-by-side comparison
    items.to_excel(writer, sheet_name="original_data", index=False)

    _apply_excel_colours(writer.sheets["results"], results)

st.download_button(
    label="Download results (.xlsx)",
    data=buf.getvalue(),
    file_name="validation_results.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
