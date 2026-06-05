"""
Streamlit web application for duplicate detection in product catalogs.

Two modes:
  Within-file  — find duplicate items inside one Excel file
  Cross-file   — find matching items between two Excel files from different systems

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
import find_duplicates_cross_file as cf

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Duplicate Detection",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Duplicate Detection in Product Catalog Data")

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_sheet_names(file):
    try:
        return pd.ExcelFile(file).sheet_names
    except Exception as e:
        st.error(f"Could not open file: {e}")
        st.stop()

def read_col_names(file, sheet, header_row):
    file.seek(0)
    try:
        return list(pd.read_excel(
            file, sheet_name=sheet, header=int(header_row), nrows=0
        ).columns)
    except Exception as e:
        st.error(f"Could not read columns: {e}")
        st.stop()

def demo_cols(filename):
    """Return column list from a demo file without consuming a file handle."""
    return list(pd.read_excel(os.path.join(DATA_DIR, filename), nrows=0).columns)

def default_cols(all_cols, preferred):
    """Return the subset of preferred that exist in all_cols, in order."""
    return [c for c in preferred if c in all_cols]

PREFERRED_SPEC    = ["specification", "Specification"]
PREFERRED_COMPARE = ["name", "specification", "Name", "Specification"]
PREFERRED_CONTEXT = ["name", "Name", "description_en", "Description (English)",
                     "description_fi", "Description (Finnish)",
                     "specification", "Specification", "category", "manufacturer", "standard", "Standard"]

def similarity_chart(sim_series, y_label):
    """Bar chart of pairs/groups by similarity band — green first.
    Only shows bands that actually contain data."""
    bins = pd.cut(sim_series, bins=[0, 59, 69, 89, 100],
                  labels=["50–59 %", "60–69 %", "70–89 %", "90–100 %"])
    label_order = ["90–100 %", "70–89 %", "60–69 %", "50–59 %"]
    chart_data = bins.value_counts().rename_axis("range").reset_index(name=y_label)
    chart_data = chart_data[chart_data[y_label] > 0]
    chart_data["range"] = pd.Categorical(
        chart_data["range"], categories=label_order, ordered=True
    )
    chart_data = chart_data.sort_values("range")
    color_map = {"50–59 %": "#dc3545", "60–69 %": "#fd7e14",
                 "70–89 %": "#ffc107", "90–100 %": "#28a745"}
    fig = px.bar(chart_data, x="range", y=y_label, color="range",
                 color_discrete_map=color_map,
                 labels={"range": "Similarity"},
                 title=f"{y_label.capitalize()} by similarity level",
                 text=y_label)
    fig.update_traces(textposition="outside")
    max_val = int(chart_data[y_label].max()) if not chart_data.empty else 1
    fig.update_layout(showlegend=False, height=350,
                      yaxis=dict(range=[0, max_val * 1.25]))
    return fig

def highlight_row(row):
    pct = row.get("similarity_pct", 0)
    colour = "#d4edda" if pct >= 90 else "#fff3cd" if pct >= 70 else "#fde8d8"
    return [f"background-color: {colour}"] * len(row)

def compare_label(cols):
    """Human-readable label for the combined comparison columns."""
    return " + ".join(cols)


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙ Settings")
    st.caption(
        "**Within-file** — finds duplicate items inside a single catalog file. "
        "Use when the same product might present more than once in a system.  \n"
        "**Cross-file** — finds matching items between two different files. "
        "Use when merging catalogs from different sources "
        "e.g. in system migration projects."
    )

    mode = st.radio("Mode", ["Within-file", "Cross-file"], horizontal=True)
    st.divider()

    # ── WITHIN-FILE sidebar ───────────────────────────────────────────────────
    if mode == "Within-file":

        wf_source = st.radio(
            "Data source", ["Demo data", "Upload own data"],
            index=0, horizontal=True, key="wf_source",
        )
        st.divider()

        # Demo presets — file and id_col are fixed, columns are editable with smart defaults
        WF_DEMOS = {
            "General spare parts": {
                "file":    "spare_parts_system1.xlsx",
                "id_col":  "item_id",
                "compare": ["specification"],
                "disc":    None,
                "context": ["name", "description_en", "specification"],
                "info":    "204 mixed spare parts — no discriminator",
            },
            "Screws (Standard discriminator)": {
                "file":    "spare_parts_screws.xlsx",
                "id_col":  "item_id",
                "compare": ["specification"],
                "disc":    "standard",
                "context": ["name", "Description (English)", "specification", "standard"],
                "info":    "218 screws — Standard column separates DIN 931 from DIN 933",
            },
        }

        if wf_source == "Demo data":
            preset_name = st.radio(
                "Demo dataset", list(WF_DEMOS.keys()), key="wf_preset",
            )
            cfg = WF_DEMOS[preset_name]
            _cols = demo_cols(cfg["file"])

            with open(os.path.join(DATA_DIR, cfg["file"]), "rb") as _f:
                uploaded_file = io.BytesIO(_f.read())
            upload_name = cfg["file"]
            sheet, header_row = 0, 0
            id_col = cfg["id_col"]

            st.info(f"**{cfg['file']}** — {cfg['info']}")

        else:
            uploaded_file = st.file_uploader("Upload Excel file (.xlsx)",
                                             type=["xlsx", "xls"], key="wf_file")
            if uploaded_file is None:
                st.info("Upload an Excel file to get started.")
                st.stop()
            upload_name = uploaded_file.name
            preset_name = None
            cfg = {}

            sheet_names = read_sheet_names(uploaded_file)
            sheet = st.selectbox("Sheet", sheet_names, key="wf_sheet")
            header_row = st.number_input("Header row (0 = first row is header)",
                                         0, 20, 0, key="wf_header")
            _cols = read_col_names(uploaded_file, sheet, header_row)
            id_col = st.selectbox(
                "ID column", _cols, key="wf_id",
                index=_cols.index("item_id") if "item_id" in _cols else 0,
                help="Column that uniquely identifies each row.",
            )

        # Column selectors shown for both demo and own data
        st.divider()
        st.subheader("Columns")

        compare_cols = st.multiselect(
            "Comparison columns", _cols, key="wf_compare",
            default=default_cols(_cols, cfg.get("compare", PREFERRED_COMPARE[:2]))
                    or default_cols(_cols, PREFERRED_COMPARE)[:1]
                    or _cols[:1],
            help="Columns combined into one text and compared to find duplicates. "
                 "Name + Specification works well for most catalogs.",
        )
        disc_options = ["(none)"] + _cols
        disc_default = cfg.get("disc") or "(none)"
        # Key includes the preset/source so switching presets resets the widget
        # and Streamlit picks up the new index instead of the cached session value.
        _disc_key = f"wf_disc_{preset_name or 'upload'}"
        disc_selection = st.selectbox(
            "Discriminator column (optional)", disc_options, key=_disc_key,
            index=disc_options.index(disc_default) if disc_default in disc_options else 0,
            help="Items with different values in this column are never grouped as duplicates. "
                 "Example: 'Standard' for screws prevents mixing DIN 931 and DIN 933.",
        )
        discriminator_col = None if disc_selection == "(none)" else disc_selection

        context_cols = st.multiselect(
            "Context columns (shown in results)", _cols, key="wf_context",
            default=default_cols(_cols, cfg.get("context", PREFERRED_CONTEXT))[:5],
            help="Original columns shown alongside duplicate groups to help with review.",
        )

        st.divider()
        st.subheader("Thresholds")
        st.caption("Higher values = stricter matching, fewer but more accurate groups.")
        candidate_threshold = st.slider("Candidate search threshold",
                                        0.50, 1.00, 0.70, 0.05, key="wf_cand",
                                        help="Stage 2: TF-IDF similarity to collect candidate pairs.")
        verify_threshold = st.slider("Within-group verification threshold",
                                     0.30, 1.00, 0.60, 0.05, key="wf_verify",
                                     help="Stage 3: similarity re-computed within each candidate group.")
        if not compare_cols:
            st.warning("Select at least one comparison column.")
            st.stop()

        st.divider()
        run_button = st.button("▶ Find duplicates", type="primary",
                               use_container_width=True, key="wf_run")

    # ── CROSS-FILE sidebar ────────────────────────────────────────────────────
    else:
        cf_source = st.radio(
            "Data source", ["Demo data", "Upload own data"],
            index=0, horizontal=True, key="cf_source",
        )
        st.divider()

        CF_DEMO = {
            "file1":   "spare_parts_system1.xlsx",
            "file2":   "spare_parts_system2.xlsx",
            "id_col":  "item_id",
            "compare": ["name", "specification"],
            "context": ["name", "description_en", "specification", "category"],
        }

        if cf_source == "Demo data":
            with open(os.path.join(DATA_DIR, CF_DEMO["file1"]), "rb") as _f:
                file1 = io.BytesIO(_f.read())
            with open(os.path.join(DATA_DIR, CF_DEMO["file2"]), "rb") as _f:
                file2 = io.BytesIO(_f.read())
            cf_name1, cf_name2 = CF_DEMO["file1"], CF_DEMO["file2"]
            sheet1, header1 = 0, 0
            sheet2, header2 = 0, 0
            id_col1 = id_col2 = CF_DEMO["id_col"]
            _cols1 = demo_cols(CF_DEMO["file1"])
            _cols2 = demo_cols(CF_DEMO["file2"])

            st.info(
                f"**{CF_DEMO['file1']}** (204 items) vs "
                f"**{CF_DEMO['file2']}** (165 items)  \n"
                "Simulates matching items between two source systems "
                "during a catalog migration."
            )

        else:
            st.subheader("File 1")
            file1 = st.file_uploader("Upload file 1 (.xlsx)", type=["xlsx", "xls"],
                                      key="cf_file1")
            if file1 is None:
                st.info("Upload both files to continue.")
                st.stop()
            cf_name1 = file1.name
            sheets1 = read_sheet_names(file1)
            sheet1 = st.selectbox("Sheet", sheets1, key="cf_sheet1")
            header1 = st.number_input("Header row", 0, 20, 0, key="cf_header1")
            _cols1 = read_col_names(file1, sheet1, header1)
            id_col1 = st.selectbox(
                "ID column", _cols1, key="cf_id1",
                index=_cols1.index("item_id") if "item_id" in _cols1 else 0,
            )

            st.divider()
            st.subheader("File 2")
            file2 = st.file_uploader("Upload file 2 (.xlsx)", type=["xlsx", "xls"],
                                      key="cf_file2")
            if file2 is None:
                st.info("Upload file 2 to continue.")
                st.stop()
            cf_name2 = file2.name
            sheets2 = read_sheet_names(file2)
            sheet2 = st.selectbox("Sheet", sheets2, key="cf_sheet2")
            header2 = st.number_input("Header row", 0, 20, 0, key="cf_header2")
            _cols2 = read_col_names(file2, sheet2, header2)
            id_col2 = st.selectbox(
                "ID column", _cols2, key="cf_id2",
                index=_cols2.index("item_id") if "item_id" in _cols2 else 0,
            )

        # Comparison and reference columns editable for both demo and own data
        st.divider()
        st.subheader("Comparison columns")
        st.caption("Columns combined into one text per item and compared between files.")
        _cf_compare_default = CF_DEMO["compare"] if cf_source == "Demo data" else PREFERRED_COMPARE[:2]
        compare1 = st.multiselect(
            "File 1 comparison columns", _cols1, key="cf_compare1",
            default=default_cols(_cols1, _cf_compare_default) or _cols1[:1],
        )
        compare2 = st.multiselect(
            "File 2 comparison columns", _cols2, key="cf_compare2",
            default=default_cols(_cols2, _cf_compare_default) or _cols2[:1],
        )

        st.subheader("Reference columns (shown in results)")
        st.caption("Original columns added to the results table for human review.")
        _cf_context_default = CF_DEMO["context"] if cf_source == "Demo data" else PREFERRED_CONTEXT
        context1 = st.multiselect(
            "File 1 reference columns", _cols1, key="cf_context1",
            default=default_cols(_cols1, _cf_context_default)[:4],
        )
        context2 = st.multiselect(
            "File 2 reference columns", _cols2, key="cf_context2",
            default=default_cols(_cols2, _cf_context_default)[:4],
        )

        st.divider()
        st.subheader("Threshold")
        cf_threshold = st.slider(
            "Similarity threshold", 0.50, 1.00, 0.70, 0.05, key="cf_thresh",
            help="Pairs below this value are not shown.",
        )

        if not compare1 or not compare2:
            st.warning("Select at least one comparison column for each file.")
            st.stop()

        st.divider()
        run_cf = st.button("▶ Find cross-file matches", type="primary",
                           use_container_width=True, key="cf_run")


# ════════════════════════════════════════════════════════════════════════════
# WITHIN-FILE — run analysis
# ════════════════════════════════════════════════════════════════════════════
if mode == "Within-file":

    # Always show description and how-it-works — even after running
    st.caption("Find near-duplicate items using TF-IDF similarity and within-group verification. "
               "Recommended for catalogs up to ~5 000 rows per run.")
    with st.expander("How it works"):
        st.markdown("""
**Stage 1 — Normalise**
Text is converted to uppercase, abbreviations are expanded
(`BRG` → `BEARING`, `HYD` → `HYDRAULIC`), and measurement formats are unified (`M8 X 30` → `M8X30`).

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
""")

    # Clear stale results when settings change so old visualisations don't persist
    _wf_sig = f"{upload_name}|{'|'.join(compare_cols)}|{discriminator_col}|{candidate_threshold}|{verify_threshold}"
    if st.session_state.get("wf_sig") != _wf_sig:
        st.session_state.pop("wf_results", None)
        st.session_state["wf_sig"] = _wf_sig

    if not run_button and "wf_results" not in st.session_state:
        st.stop()

    if run_button:
        uploaded_file.seek(0)
        with st.spinner("Loading data…"):
            df = pd.read_excel(uploaded_file, sheet_name=sheet, header=int(header_row))
        n_rows = len(df)

        if n_rows > 10_000:
            st.warning(f"⚠ File has {n_rows:,} rows. "
                       "For best performance, filter to one product group before running.")

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
            verified = fd.apply_discriminator(verified, df,
                                              id_col=id_col, disc_col=discriminator_col)
            removed = before - len(verified)
            progress.progress(85, f"Discriminator removed {removed:,} pairs…")

        progress.progress(90, "Building results…")
        result_df = fd.build_results(verified, df, id_col=id_col)
        progress.progress(100, "Done!")
        progress.empty()

        if result_df.empty:
            st.warning("No duplicate groups found. Try lowering the thresholds.")
            st.stop()

        result_df["comparison_data"] = result_df[id_col].map(compare_series)

        st.session_state.update(
            wf_results=result_df,
            wf_original_df=df,
            wf_filename=upload_name,
            wf_n_rows=n_rows,
            wf_id_col=id_col,
            wf_context_cols=context_cols,
            wf_discriminator=discriminator_col,
            wf_compare_cols=compare_cols,
        )

    if "wf_results" not in st.session_state:
        st.stop()

    result_df   = st.session_state["wf_results"]
    original_df = st.session_state["wf_original_df"]
    wf_filename = st.session_state["wf_filename"]
    n_rows      = st.session_state["wf_n_rows"]
    id_col_d    = st.session_state["wf_id_col"]
    ctx_cols    = st.session_state["wf_context_cols"]
    disc_col    = st.session_state["wf_discriminator"]
    wf_cmp_cols = st.session_state.get("wf_compare_cols", compare_cols)

    # Label the comparison_data column with the columns that were combined
    cmp_label      = compare_label(wf_cmp_cols)
    cmp_col_name   = f"comparison_data ({cmp_label})"
    result_display = result_df.rename(columns={"comparison_data": cmp_col_name})

    n_groups  = result_df["duplicate_group"].nunique()
    n_flagged = len(result_df)

    tab_summary, tab_groups, tab_download = st.tabs(
        ["📊 Summary", "🔁 Duplicate Groups", "⬇ Download"]
    )

    with tab_summary:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total rows", f"{n_rows:,}")
        c2.metric("Duplicate groups", n_groups)
        c3.metric("Rows flagged", n_flagged)
        c4.metric("% of catalog", f"{n_flagged / n_rows:.0%}")
        if disc_col:
            st.info(f"ℹ Discriminator **'{disc_col}'** was applied — "
                    "pairs with different values were excluded.")
        st.divider()
        groups_df = result_df.drop_duplicates("duplicate_group")[["similarity_pct"]].copy()
        st.plotly_chart(similarity_chart(groups_df["similarity_pct"], "groups"),
                        use_container_width=True)
        st.caption("🟢 90–100 % — high confidence  "
                   "🟡 70–89 % — review needed  "
                   "🟠 60–69 % — uncertain  "
                   "🔴 50–59 % — low confidence, review carefully")

    with tab_groups:
        min_sim = st.slider("Show groups with similarity ≥", 60, 100, 60, 5,
                            key="wf_filter")
        filtered = result_display[result_display["similarity_pct"] >= min_sim]
        st.caption(f"Showing **{filtered['duplicate_group'].nunique()}** groups, "
                   f"**{len(filtered)}** rows")
        display_cols = [id_col_d, "duplicate_group", "similarity_pct", cmp_col_name]
        for c in ctx_cols:
            if c in filtered.columns and c not in display_cols:
                display_cols.append(c)
        if disc_col and disc_col in filtered.columns and disc_col not in display_cols:
            display_cols.append(disc_col)
        display_cols = [c for c in display_cols if c in filtered.columns]
        styled = filtered[display_cols].style.apply(highlight_row, axis=1)
        st.dataframe(styled, use_container_width=True, height=520)

    with tab_download:
        out_cols = [id_col_d, "duplicate_group", "similarity_pct", cmp_col_name]
        for c in ctx_cols:
            if c in result_display.columns and c not in out_cols:
                out_cols.append(c)
        if disc_col and disc_col in result_display.columns and disc_col not in out_cols:
            out_cols.append(disc_col)
        output_df = result_display[[c for c in out_cols if c in result_display.columns]]
        base_name = os.path.splitext(wf_filename)[0]
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            original_df.to_excel(writer, sheet_name="Data", index=False)
            output_df.to_excel(writer, sheet_name="Duplicates", index=False)
        st.download_button(
            label="⬇ Download results as Excel",
            data=buf.getvalue(),
            file_name=f"{base_name}_duplicates.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption(f"The file contains **{n_groups}** duplicate groups "
                   f"with **{n_flagged}** flagged rows.")


# ════════════════════════════════════════════════════════════════════════════
# CROSS-FILE — run analysis
# ════════════════════════════════════════════════════════════════════════════
else:

    # Always show description and how-it-works
    st.caption("Find matching items between two files from different source systems "
               "using TF-IDF similarity on the combined vocabulary of both files.")
    with st.expander("How it works"):
        st.markdown("""
**Step 1 — Normalise**
Selected comparison columns from each file are normalised and combined into one text per item
(`M8 X 30` → `M8X30`, abbreviations expanded).

**Step 2 — TF-IDF on combined corpus**
All texts from both files are fed to TF-IDF together so term weights reflect rarity
across *both* systems. A product code rare in both systems gets a high weight;
a generic word common in both gets a low weight.

**Step 3 — Cross-file similarity matrix**
Cosine similarity is computed between every File 1 item and every File 2 item.
Only cross-file pairs are checked — File 1 vs File 1 comparisons are skipped.

**Step 4 — Filter by threshold**
Pairs below the threshold are discarded. The output is a flat list of candidate pairs
for human review, sorted by File 1 item ID and then similarity descending.
""")

    # Clear stale results when settings change
    _cf_sig = f"{cf_name1}|{cf_name2}|{'|'.join(compare1)}|{'|'.join(compare2)}|{cf_threshold}"
    if st.session_state.get("cf_sig") != _cf_sig:
        st.session_state.pop("cf_results", None)
        st.session_state["cf_sig"] = _cf_sig

    if not run_cf and "cf_results" not in st.session_state:
        st.stop()

    if run_cf:
        file1.seek(0)
        file2.seek(0)
        with st.spinner("Loading files…"):
            df1 = pd.read_excel(file1, sheet_name=sheet1, header=int(header1))
            df2 = pd.read_excel(file2, sheet_name=sheet2, header=int(header2))

        progress = st.progress(0, "Normalising text…")
        series1 = cf.build_compare_series(df1, id_col1, compare1)
        series2 = cf.build_compare_series(df2, id_col2, compare2)
        progress.progress(30, f"Comparing {len(series1)} × {len(series2)} pairs…")

        candidates = cf.find_cross_candidates(series1, series2, threshold=cf_threshold)
        progress.progress(80, f"Found {len(candidates):,} candidate pairs — building results…")

        result_df = cf.build_results(
            candidates, df1, df2, series1, series2,
            id_col1=id_col1, id_col2=id_col2,
            context_cols1=context1, context_cols2=context2,
        )
        progress.progress(100, "Done!")
        progress.empty()

        if result_df.empty:
            st.warning("No matches found. Try lowering the threshold.")
            st.stop()

        st.session_state.update(
            cf_results=result_df,
            cf_df1=df1, cf_df2=df2,
            cf_filename1=cf_name1, cf_filename2=cf_name2,
            cf_n1=len(df1), cf_n2=len(df2),
            # Use _used suffix to avoid conflict with the widget keys cf_compare1/cf_compare2
            cf_compare1_used=compare1, cf_compare2_used=compare2,
        )

    if "cf_results" not in st.session_state:
        st.stop()

    result_df  = st.session_state["cf_results"]
    df1        = st.session_state["cf_df1"]
    df2        = st.session_state["cf_df2"]
    filename1  = st.session_state["cf_filename1"]
    filename2  = st.session_state["cf_filename2"]
    n1         = st.session_state["cf_n1"]
    n2         = st.session_state["cf_n2"]
    cf_cmp1    = st.session_state.get("cf_compare1_used", compare1)
    cf_cmp2    = st.session_state.get("cf_compare2_used", compare2)
    n_pairs    = len(result_df)

    # Label comparison_data columns with the columns that were combined
    lbl1 = compare_label(cf_cmp1)
    lbl2 = compare_label(cf_cmp2)
    result_display = result_df.rename(columns={
        "s1_comparison_data": f"s1_comparison_data ({lbl1})",
        "s2_comparison_data": f"s2_comparison_data ({lbl2})",
    })

    tab_summary, tab_pairs, tab_download = st.tabs(
        ["📊 Summary", "🔁 Candidate Pairs", "⬇ Download"]
    )

    with tab_summary:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("File 1 rows", f"{n1:,}")
        c2.metric("File 2 rows", f"{n2:,}")
        c3.metric("Candidate pairs", n_pairs)
        c4.metric("% of smaller file", f"{n_pairs / min(n1, n2):.0%}")
        st.divider()
        st.plotly_chart(similarity_chart(result_df["similarity_pct"], "pairs"),
                        use_container_width=True)
        st.caption("🟢 90–100 % — high confidence  "
                   "🟡 70–89 % — review needed  "
                   "🟠 60–69 % — uncertain  "
                   "🔴 50–59 % — low confidence, review carefully")

    with tab_pairs:
        min_sim = st.slider("Show pairs with similarity ≥", 60, 100, 70, 5,
                            key="cf_filter")
        filtered = result_display[result_display["similarity_pct"] >= min_sim]
        st.caption(f"Showing **{len(filtered)}** pairs")
        styled = filtered.style.apply(highlight_row, axis=1)
        st.dataframe(styled, use_container_width=True, height=520)

    with tab_download:
        base1 = os.path.splitext(filename1)[0]
        base2 = os.path.splitext(filename2)[0]
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df1.to_excel(writer, sheet_name="File1", index=False)
            df2.to_excel(writer, sheet_name="File2", index=False)
            result_display.to_excel(writer, sheet_name="Duplicates", index=False)
        st.download_button(
            label="⬇ Download results as Excel",
            data=buf.getvalue(),
            file_name=f"{base1}_vs_{base2}_duplicates.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption(f"The file contains **{n_pairs}** candidate pairs. "
                   f"Sheets: File1 ({n1} rows), File2 ({n2} rows), Duplicates ({n_pairs} pairs).")
