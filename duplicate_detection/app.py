"""
Streamlit web application for duplicate detection in product catalogs.

Run with:  streamlit run app.py
"""
import io
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
import find_duplicates as fd

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Duplicate Detection",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Duplicate Detection in Product Catalog Data")
st.caption(
    "Find near-duplicate items using TF-IDF similarity and within-group verification. "
    "Recommended for catalogs up to ~5 000 rows per run. "
    "For larger catalogs, filter by product group first."
)

# ── Sidebar — settings ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙ Settings")

    uploaded_file = st.file_uploader("Upload Excel file (.xlsx)", type=["xlsx", "xls"])

    if uploaded_file is None:
        st.info("Upload an Excel file to get started.")
        st.stop()

    # Read sheet names
    try:
        xf = pd.ExcelFile(uploaded_file)
        sheet_names = xf.sheet_names
    except Exception as e:
        st.error(f"Could not open file: {e}")
        st.stop()

    sheet = st.selectbox("Sheet", sheet_names)
    header_row = st.number_input("Header row (0 = first row is header)", 0, 20, 0)

    # Read column names from the selected sheet
    uploaded_file.seek(0)
    try:
        df_preview = pd.read_excel(
            uploaded_file, sheet_name=sheet, header=int(header_row), nrows=0
        )
        all_cols = list(df_preview.columns)
    except Exception as e:
        st.error(f"Could not read columns: {e}")
        st.stop()

    st.divider()
    st.subheader("Columns")

    id_col = st.selectbox(
        "ID column",
        all_cols,
        index=all_cols.index("item_id") if "item_id" in all_cols else 0,
        help="Column that uniquely identifies each row.",
    )

    # Default comparison column: prefer 'specification' or 'Specification'
    default_spec = next(
        (c for c in all_cols if c.lower() == "specification"), all_cols[0]
    )
    compare_cols = st.multiselect(
        "Comparison columns",
        all_cols,
        default=[default_spec],
        help=(
            "Columns combined and compared to find duplicates. "
            "Specification alone works well when it is well-filled. "
            "Add Name or Description if Specification is often empty."
        ),
    )

    disc_options = ["(none)"] + all_cols
    disc_selection = st.selectbox(
        "Discriminator column (optional)",
        disc_options,
        help=(
            "Items with different values in this column are never grouped as duplicates, "
            "even if their specification is identical. "
            "Example: 'Standard' for screws prevents mixing DIN 931 and DIN 933. "
            "Try this with the sample file spare_parts_screws.xlsx using the Standard column."
        ),
    )
    discriminator_col = None if disc_selection == "(none)" else disc_selection

    # Default context columns
    preferred_context = ["name", "Name", "description_en", "Description (English)",
                         "description_fi", "Description (Finnish)", "specification",
                         "Specification", "category", "manufacturer", "Standard"]
    default_context = [c for c in preferred_context if c in all_cols][:6]
    context_cols = st.multiselect(
        "Context columns (shown in results)",
        all_cols,
        default=default_context,
        help="Original columns shown alongside duplicate groups to help with review.",
    )

    st.divider()
    st.subheader("Thresholds")
    st.caption("Higher values = stricter matching, fewer but more accurate groups.")

    candidate_threshold = st.slider(
        "Candidate search threshold",
        0.50, 1.00, 0.70, 0.05,
        help="Stage 2: TF-IDF similarity to collect candidate pairs.",
    )
    verify_threshold = st.slider(
        "Within-group verification threshold",
        0.30, 1.00, 0.60, 0.05,
        help="Stage 3: similarity re-computed within each candidate group.",
    )

    if not compare_cols:
        st.warning("Select at least one comparison column.")
        st.stop()

    st.divider()
    run_button = st.button("▶ Find duplicates", type="primary", use_container_width=True)

# ── Welcome screen ────────────────────────────────────────────────────────────
if not run_button and "results" not in st.session_state:
    st.info("👈 Configure settings in the sidebar and click **Find duplicates**.")

    with st.expander("How it works"):
        st.markdown(
            """
**Stage 1 — Normalise**
Text is converted to uppercase, abbreviations are expanded
(`BRG` → `BEARING`, `HYD` → `HYDRAULIC`), and measurement formats are unified
(`M8 X 30` → `M8X30`).

**Stage 2 — Candidate search (TF-IDF)**
Rare terms like product codes get higher weight than common words like `GRADE` or `ISO`.
Items that share rare terms score high and become candidate pairs.

**Stage 3 — Within-group verification**
TF-IDF is re-computed using only the members of each candidate group.
Within the group, size codes that appear only once get high weight — different-size
items score low and are removed. Genuine duplicates share the same codes and score high.

**Stage 4 — Discriminator filter (optional)**
Items with different values in the discriminator column are never grouped as duplicates.
For screws: `Standard = DIN 931` (partial thread) ≠ `Standard = DIN 933` (full thread).
"""
        )
    st.stop()

# ── Run analysis ──────────────────────────────────────────────────────────────
if run_button:
    uploaded_file.seek(0)

    with st.spinner("Loading data…"):
        df = pd.read_excel(uploaded_file, sheet_name=sheet, header=int(header_row))

    n_rows = len(df)

    if n_rows > 10_000:
        st.warning(
            f"⚠ File has {n_rows:,} rows. "
            "For best performance, filter to one product group before running. "
            "Processing may take several minutes."
        )

    # Build comparison series: combine selected columns into one normalised text per row
    with st.spinner("Normalising text…"):
        compare_series = df.set_index(id_col).apply(
            lambda row: " ".join(
                fd.normalize(row[c])
                for c in compare_cols
                if c in row.index and pd.notna(row[c]) and str(row[c]).strip()
            ),
            axis=1,
        )

    progress = st.progress(0, "Stage 2 — TF-IDF candidate search…")

    candidates = fd.find_candidates(compare_series, threshold=candidate_threshold)
    progress.progress(35, f"Found {len(candidates):,} candidate pairs — verifying…")

    verified = fd.verify_groups(candidates, compare_series, threshold=verify_threshold)
    progress.progress(65, f"Kept {len(verified):,} verified pairs…")

    if discriminator_col:
        before = len(verified)
        verified = fd.apply_discriminator(
            verified, df, id_col=id_col, disc_col=discriminator_col
        )
        removed = before - len(verified)
        progress.progress(85, f"Discriminator removed {removed:,} pairs…")

    progress.progress(90, "Building results…")
    result_df = fd.build_results(verified, df, id_col=id_col)
    progress.progress(100, "Done!")
    progress.empty()

    if result_df.empty:
        st.warning("No duplicate groups found. Try lowering the thresholds.")
        st.stop()

    # Add comparison_data: the normalised text that was actually used for comparison
    result_df["comparison_data"] = result_df[id_col].map(compare_series)

    st.session_state.update(
        results=result_df,
        original_df=df,
        source_filename=uploaded_file.name,
        n_rows=n_rows,
        id_col=id_col,
        context_cols=context_cols,
        discriminator_col=discriminator_col,
    )

# ── Display results ───────────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.stop()

result_df       = st.session_state["results"]
original_df     = st.session_state["original_df"]
source_filename = st.session_state["source_filename"]
n_rows          = st.session_state["n_rows"]
id_col_d        = st.session_state["id_col"]
context_cols_d  = st.session_state["context_cols"]
discriminator_d = st.session_state["discriminator_col"]

n_groups  = result_df["duplicate_group"].nunique()
n_flagged = len(result_df)

tab_summary, tab_groups, tab_download = st.tabs(
    ["📊 Summary", "🔁 Duplicate Groups", "⬇ Download"]
)

# ── Tab 1: Summary ────────────────────────────────────────────────────────────
with tab_summary:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total rows", f"{n_rows:,}")
    c2.metric("Duplicate groups", n_groups)
    c3.metric("Rows flagged", n_flagged)
    c4.metric("% of catalog", f"{n_flagged / n_rows:.0%}")

    if discriminator_d:
        st.info(
            f"ℹ Discriminator column **'{discriminator_d}'** was applied — "
            "pairs with different values were excluded."
        )

    st.divider()

    # Similarity distribution bar chart
    groups_df = result_df.drop_duplicates("duplicate_group")[
        ["duplicate_group", "similarity_pct"]
    ].copy()

    bins = pd.cut(
        groups_df["similarity_pct"],
        bins=[0, 69, 89, 100],
        labels=["60–69 %", "70–89 %", "90–100 %"],
    )
    label_order = ["90–100 %", "70–89 %", "60–69 %"]
    chart_data = (
        bins.value_counts()
        .rename_axis("range")
        .reset_index(name="groups")
    )
    chart_data["range"] = pd.Categorical(
        chart_data["range"], categories=label_order, ordered=True
    )
    chart_data = chart_data.sort_values("range")

    color_map = {
        "60–69 %":  "#fd7e14",
        "70–89 %":  "#ffc107",
        "90–100 %": "#28a745",
    }
    fig = px.bar(
        chart_data,
        x="range", y="groups",
        color="range",
        color_discrete_map=color_map,
        labels={"range": "Similarity", "groups": "Number of groups"},
        title="Duplicate groups by similarity level",
        text="groups",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "🟢 90–100 % — high confidence  "
        "🟡 70–89 % — review specification  "
        "🟠 60–69 % — uncertain, review carefully"
    )

# ── Tab 2: Duplicate Groups ───────────────────────────────────────────────────
with tab_groups:
    min_sim = st.slider(
        "Show groups with similarity ≥", 60, 100, 60, 5, key="filter_slider"
    )
    filtered = result_df[result_df["similarity_pct"] >= min_sim]

    st.caption(
        f"Showing **{filtered['duplicate_group'].nunique()}** groups, "
        f"**{len(filtered)}** rows"
    )

    # Columns to display
    display_cols = [id_col_d, "duplicate_group", "similarity_pct", "comparison_data"]
    for c in context_cols_d:
        if c in filtered.columns and c not in display_cols:
            display_cols.append(c)
    if discriminator_d and discriminator_d in filtered.columns and discriminator_d not in display_cols:
        display_cols.append(discriminator_d)
    display_cols = [c for c in display_cols if c in filtered.columns]

    # Colour rows by similarity
    def highlight_row(row):
        pct = row.get("similarity_pct", 0)
        colour = (
            "#d4edda" if pct >= 90
            else "#fff3cd" if pct >= 70
            else "#fde8d8"
        )
        return [f"background-color: {colour}"] * len(row)

    styled = filtered[display_cols].style.apply(highlight_row, axis=1)
    st.dataframe(styled, use_container_width=True, height=520)

# ── Tab 3: Download ───────────────────────────────────────────────────────────
with tab_download:
    out_cols = [id_col_d, "duplicate_group", "similarity_pct", "comparison_data"]
    for c in context_cols_d:
        if c in result_df.columns and c not in out_cols:
            out_cols.append(c)
    if discriminator_d and discriminator_d in result_df.columns and discriminator_d not in out_cols:
        out_cols.append(discriminator_d)

    output_df = result_df[[c for c in out_cols if c in result_df.columns]]

    base_name = os.path.splitext(source_filename)[0]
    download_name = f"{base_name}_duplicates.xlsx"

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        original_df.to_excel(writer, sheet_name="Data", index=False)
        output_df.to_excel(writer, sheet_name="Duplicates", index=False)

    st.download_button(
        label="⬇ Download results as Excel",
        data=buf.getvalue(),
        file_name=download_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.caption(
        f"The file contains **{n_groups}** duplicate groups with "
        f"**{n_flagged}** flagged rows."
    )
