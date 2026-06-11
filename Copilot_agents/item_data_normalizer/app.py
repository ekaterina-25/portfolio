"""Fastener Normalizer — Streamlit simulation of the Copilot Studio agent."""

from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Fastener Normalizer",
    page_icon="🔧",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# Demo data
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = Path(__file__).parent / "demo_data"
    df_in = pd.read_excel(base / "demo_input.xlsx", dtype=str).fillna("")
    df_out = pd.read_excel(base / "demo_output.xlsx", dtype=str).fillna("")
    return df_in, df_out


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

if "normalized_indices" not in st.session_state:
    st.session_state.normalized_indices = []
if "scroll_to_results" not in st.session_state:
    st.session_state.scroll_to_results = False


# ─────────────────────────────────────────────────────────────────────────────
# Layout
# ─────────────────────────────────────────────────────────────────────────────

st.title("Fastener Normalizer")
st.markdown(
    "A Microsoft Copilot Studio agent that reads fastener item data from Excel, "
    "harmonizes names and descriptions against internal naming rules, "
    "and writes the cleaned result back to Excel via Power Automate and Office Scripts."
)
st.markdown(
    "_This page is a simplified simulation of the agent, not the agent itself. "
    "The real agent runs inside Microsoft Copilot Studio connected to Excel Online._"
)

with st.expander("How this works"):
    st.markdown(
        """
### What the real agent does

The agent reads a batch of item rows from an Excel table, applies the internal naming
rules, and writes the harmonized output back to a separate Excel file. The key rules:

**Standard selection** — if both ISO and DIN are present, ISO is kept; if only one
standard is present, it is used as-is.

| Input standards | Output |
|---|---|
| DIN 912, ISO 4762 | ISO 4762 |
| DIN 603, ISO 8677 | ISO 8677 |
| DIN 916 only | DIN 916 |
| INT-2019 only | INT-2019 |

**Description mapping** — the resolved standard determines the canonical English/Finnish
type label (e.g. ISO 4762 → *Hexagon socket head cap screw* / *Kuusiokoloruuvi*).

**Specification format** — `[Standard] [Coating] [Class] [Size]`, with `×` as the size
separator. Coating and material tokens (`Zn`, `A4-70`, `8.8`) must not be lost.

**Name format** — `[Description EN] [Standard] [Coating] [Class] [Size]`

**Text normalization** — sentence case throughout; all-caps names are lowercased.

### This simulation

Click rows in the input table to select them, then press **Normalize**. The app shows
a before/after comparison for each selected row. No API call is made — the output
comes from the pre-built demo file.
"""
    )

df_in, df_out = load_data()

# Column widths sized to fit all 6 input columns in a wide layout without horizontal scroll
col_cfg = {
    "Item Code": st.column_config.TextColumn(width="small"),
    "Name": st.column_config.TextColumn(width="medium"),
    "Description (English)": st.column_config.TextColumn("Desc (EN)", width="medium"),
    "Description (Finnish)": st.column_config.TextColumn("Desc (FI)", width="small"),
    "Specification": st.column_config.TextColumn(width="small"),
    "Standard": st.column_config.TextColumn(width="medium"),
}

# ── Input table with row selection ────────────────────────────────────────────

st.subheader("Input data — 15 rows")
st.caption(
    "15 synthetic screw items with typical data quality issues. "
    "Click rows to select (Ctrl/Shift for multiple), then press **Normalize**."
)

event = st.dataframe(
    df_in,
    on_select="rerun",
    selection_mode="multi-row",
    hide_index=True,
    use_container_width=True,
    column_config=col_cfg,
    height=580,
)
selected_indices = event.selection.rows

if st.button(
    "Normalize",
    type="primary",
    disabled=not selected_indices,
):
    st.session_state.normalized_indices = list(selected_indices)
    st.session_state.scroll_to_results = True

# ── Results: two side-by-side tables ─────────────────────────────────────────

st.markdown('<div id="results-anchor"></div>', unsafe_allow_html=True)

if st.session_state.normalized_indices:
    if st.session_state.scroll_to_results:
        st.session_state.scroll_to_results = False
        components.html(
            "<script>window.parent.document.getElementById('results-anchor')"
            ".scrollIntoView({behavior:'smooth'});</script>",
            height=0,
        )
    indices = st.session_state.normalized_indices
    sel_in = df_in.iloc[indices].reset_index(drop=True)

    # Match output rows in the same order as the selection
    codes = sel_in["Item Code"].tolist()
    sel_out = (
        df_out[df_out["Item Code"].isin(codes)]
        .set_index("Item Code")
        .loc[codes]
        .reset_index()
    )

    st.divider()
    n = len(indices)
    st.subheader(f"Result — {n} row{'s' if n != 1 else ''}")

    # CSS to darken the column header text inside Streamlit's dataframe component
    st.markdown(
        "<style>[data-testid='stDataFrame'] th span {color:#0e1117!important;"
        "font-weight:700!important;}</style>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            '<p style="font-size:1.1rem;font-weight:600;color:#0e1117;margin:0 0 4px 0;">'
            "Raw data</p>",
            unsafe_allow_html=True,
        )
        st.dataframe(sel_in, hide_index=True, use_container_width=True, column_config=col_cfg)
    with col2:
        st.markdown(
            '<p style="font-size:1.1rem;font-weight:600;color:#0e1117;margin:0 0 4px 0;">'
            "Harmonized data</p>",
            unsafe_allow_html=True,
        )
        st.dataframe(sel_out, hide_index=True, use_container_width=True, column_config=col_cfg)
