"""
Cross-file duplicate detection — compare items between two source systems.

Finds candidate pairs where an item in file 1 likely describes the same
physical product as an item in file 2.

Key difference from find_duplicates.py (within-file):
  - TF-IDF is fit on the COMBINED corpus of both files so IDF weights reflect
    global term rarity across both systems.
  - Similarity is computed only for cross-file pairs (m × n matrix).
  - No within-group verification step — the output IS the candidate list
    for human review.

Input:  two Excel files with product catalog data
Output: Excel with three sheets — File1 (original), File2 (original), Duplicates (results)
"""
import os
import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, os.path.dirname(__file__))
from find_duplicates import normalize   # reuse normalisation: uppercase, abbrevs, M8 X 30 → M8X30

# ── Configuration ─────────────────────────────────────────────────────────────
FILE1   = os.path.join(os.path.dirname(__file__), "data", "spare_parts_system1.xlsx")
FILE2   = os.path.join(os.path.dirname(__file__), "data", "spare_parts_system2.xlsx")
SHEET1  = "Items"
SHEET2  = "Items"
ID_COL1 = "item_id"    # unique row identifier in file 1
ID_COL2 = "item_id"    # unique row identifier in file 2

# Comparison columns — defined separately per file because the two source systems
# may use different field names for the same kind of data.
# All listed columns are normalised and concatenated into one text string per item.
# If a column is empty for a row it is skipped, so listing "name" as fallback
# ensures items without a specification still get compared via their name.
COMPARE_COLS1 = ["specification", "name"]
COMPARE_COLS2 = ["specification", "name"]

# Similarity threshold: pairs below this value are not included in the output.
# 0.70 was chosen after testing: it removes all noisy low-similarity pairs
# without losing any genuine matches on the demo data.
# Lower (e.g. 0.60) = more candidates but more false positives.
# Higher (e.g. 0.80) = fewer but more certain matches.
THRESHOLD = 0.70

# Reference columns added to the output sheet so the reviewer can read the
# full item context without opening the source files.
# Defined separately per file — use the actual column names from each file.
CONTEXT_COLS1 = ["name", "description_en", "specification", "category"]
CONTEXT_COLS2 = ["name", "description_en", "specification", "category"]

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "cross_file_candidates.xlsx")


# ── Step 1: Build normalised comparison text ──────────────────────────────────

def build_compare_series(df: pd.DataFrame, id_col: str,
                         compare_cols: list) -> pd.Series:
    """
    Normalise and combine comparison columns into one text string per item.

    For each row the function:
      1. Takes each column listed in compare_cols in order
      2. Skips the column if the value is empty or NaN
      3. Normalises the value (uppercase, expand abbreviations, unify M8 X 30 → M8X30)
      4. Joins the results with a space

    Example with compare_cols = ["specification", "name"]:
      specification = "M16X150 ZINC PLATED HILTI"
      name          = "Anchor Bolt M16X150"
      → "M16X150 ZINC PLATED HILTI ANCHOR BOLT M16X150"

    Returns a pd.Series indexed by id_col.
    """
    return df.set_index(id_col).apply(
        lambda row: " ".join(
            normalize(row[c])
            for c in compare_cols
            if c in row.index and pd.notna(row[c]) and str(row[c]).strip()
        ),
        axis=1,
    )


# ── Step 2: Cross-file candidate search ──────────────────────────────────────

def find_cross_candidates(series1: pd.Series, series2: pd.Series,
                          threshold: float = THRESHOLD) -> pd.DataFrame:
    """
    Find all item pairs (one from each file) whose normalised texts are
    sufficiently similar according to TF-IDF cosine similarity.

    How it works:

    1. COMBINED CORPUS
       All texts from both files are combined into one list and fed to
       TfidfVectorizer together. This is important: IDF (Inverse Document
       Frequency) weights are calculated globally across both files.
       A product code like "6206" that appears in only 2 items across both
       systems gets a high weight — it is a strong identifier.
       A generic word like "ISO" that appears in hundreds of items gets a
       low weight — it does not help distinguish products.

    2. TF-IDF WITH CHARACTER N-GRAMS (3-5 characters)
       The vectorizer splits each text into overlapping character sequences
       of 3 to 5 characters ("char_wb" mode).
       Example: "M8X30" → ["M8X", "8X3", "X30", "M8X3", "8X30", "M8X30"]
       This handles partial matches well: "6205-2RS1" and "6205 2RS" share
       the sequence "6205" even though the full tokens differ.
       Each n-gram gets a TF-IDF weight; together they form a numeric vector.

    3. SPLIT THE MATRIX BACK INTO TWO PARTS
       After fitting, the combined matrix is sliced: the first len(ids1) rows
       belong to file1, the rest to file2.

    4. CROSS-FILE SIMILARITY MATRIX (n1 × n2)
       cosine_similarity(mat1, mat2) produces a matrix where
       row i = file1 item i, column j = file2 item j, value = similarity 0–1.
       Only cross-file pairs are computed — no file1 vs file1 comparisons.

    5. EXTRACT PAIRS ABOVE THRESHOLD
       The matrix is scanned and all (i, j) pairs where similarity >= threshold
       are collected, sorted by similarity descending, and returned.

    Returns a DataFrame with columns [id1, id2, similarity].
    """
    ids1  = series1.index.tolist()
    ids2  = series2.index.tolist()

    # Combine both corpora — system1 texts first, system2 texts second.
    # The order matters only for slicing the matrix back apart afterwards.
    texts = series1.fillna("").tolist() + series2.fillna("").tolist()

    try:
        vec    = TfidfVectorizer(min_df=1, analyzer="char_wb", ngram_range=(3, 5))
        matrix = vec.fit_transform(texts)   # sparse matrix, shape (n1+n2, n_features)
    except ValueError:
        return pd.DataFrame(columns=["id1", "id2", "similarity"])

    mat1 = matrix[:len(ids1)]   # file1 rows — shape (n1, n_features)
    mat2 = matrix[len(ids1):]   # file2 rows — shape (n2, n_features)

    # Cosine similarity: measures the angle between two vectors.
    # A short text ("M16X60") and a long text ("HEXAGON BOLT M16X60 GRADE 8.8")
    # can still score high because they share the same rare n-grams — the
    # difference in text length does not penalise the match.
    sim_matrix = cosine_similarity(mat1, mat2)   # shape (n1, n2)

    # Collect all pairs that exceed the threshold
    rows = [
        {"id1": ids1[i], "id2": ids2[j], "similarity": float(sim_matrix[i, j])}
        for i in range(len(ids1))
        for j in range(len(ids2))
        if sim_matrix[i, j] >= threshold
    ]

    return (pd.DataFrame(rows)
            .sort_values("similarity", ascending=False)
            .reset_index(drop=True))


# ── Step 3: Build result table ────────────────────────────────────────────────

def build_results(candidates: pd.DataFrame,
                  df1: pd.DataFrame, df2: pd.DataFrame,
                  series1: pd.Series, series2: pd.Series,
                  id_col1: str = ID_COL1, id_col2: str = ID_COL2,
                  context_cols1: list = CONTEXT_COLS1,
                  context_cols2: list = CONTEXT_COLS2) -> pd.DataFrame:
    """
    Attach context columns from both files to each candidate pair.

    Column order in output:
      similarity_pct
      s1_<id_col1>  |  s1_comparison_data
      s2_<id_col2>  |  s2_comparison_data
      s1_<context_cols1[0]>, s2_<context_cols2[0]>,   ← same field side by side
      s1_<context_cols1[1]>, s2_<context_cols2[1]>,   ← easy visual comparison
      ...

    Context columns are interleaved (s1_name, s2_name, s1_specification, s2_specification...)
    so the reviewer can compare the same field across both systems without
    scrolling left/right between distant columns.

    Rows are sorted by s1 item ID first, then similarity descending — so all
    potential matches for one file1 item appear together, best match on top.
    """
    if candidates.empty:
        return pd.DataFrame()

    # Index both DataFrames by their ID column for fast row lookup
    lkp1 = df1.set_index(id_col1)
    lkp2 = df2.set_index(id_col2)

    result_rows = []
    for _, pair in candidates.iterrows():
        id1, id2 = pair["id1"], pair["id2"]

        # Fetch the original rows — fall back to empty Series if ID not found
        r1 = lkp1.loc[id1] if id1 in lkp1.index else pd.Series(dtype=object)
        r2 = lkp2.loc[id2] if id2 in lkp2.index else pd.Series(dtype=object)

        rec: dict = {}

        # Core comparison columns — always first in the output
        rec["similarity_pct"]     = round(pair["similarity"] * 100)
        rec[f"s1_{id_col1}"]      = id1
        rec["s1_comparison_data"] = series1.get(id1, "")
        rec[f"s2_{id_col2}"]      = id2
        rec["s2_comparison_data"] = series2.get(id2, "")

        # Reference columns — both files stored flat first, then reordered below
        for c in context_cols1:
            rec[f"s1_{c}"] = r1.get(c, "") if len(r1) else ""
        for c in context_cols2:
            rec[f"s2_{c}"] = r2.get(c, "") if len(r2) else ""

        result_rows.append(rec)

    result = pd.DataFrame(result_rows)

    # Reorder columns: interleave context pairs so s1_name sits next to s2_name, etc.
    # If the two lists have different lengths the unpaired columns are appended at the end.
    core = ["similarity_pct", f"s1_{id_col1}", "s1_comparison_data",
            f"s2_{id_col2}", "s2_comparison_data"]
    interleaved = []
    for i in range(max(len(context_cols1), len(context_cols2))):
        if i < len(context_cols1):
            interleaved.append(f"s1_{context_cols1[i]}")
        if i < len(context_cols2):
            interleaved.append(f"s2_{context_cols2[i]}")
    result = result[core + interleaved]

    # Sort: group all matches for the same s1 item together,
    # highest similarity first within each group
    result = (result
              .sort_values([f"s1_{id_col1}", "similarity_pct"], ascending=[True, False])
              .reset_index(drop=True))

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Loading {os.path.basename(FILE1)} ...")
    df1 = pd.read_excel(FILE1, sheet_name=SHEET1)
    print(f"  {len(df1)} rows")

    print(f"Loading {os.path.basename(FILE2)} ...")
    df2 = pd.read_excel(FILE2, sheet_name=SHEET2)
    print(f"  {len(df2)} rows")
    print()

    print(f"Normalising — file1: {COMPARE_COLS1}, file2: {COMPARE_COLS2} ...")
    series1 = build_compare_series(df1, ID_COL1, COMPARE_COLS1)
    series2 = build_compare_series(df2, ID_COL2, COMPARE_COLS2)

    # Warn if any items have no text to compare (all selected columns empty)
    empty1 = (series1 == "").sum()
    empty2 = (series2 == "").sum()
    if empty1:
        print(f"  Warning: {empty1} items in file1 have no comparison text")
    if empty2:
        print(f"  Warning: {empty2} items in file2 have no comparison text")
    print()

    print(f"TF-IDF cross-file search (threshold {THRESHOLD}) ...")
    print(f"  Comparing {len(series1)} x {len(series2)} = "
          f"{len(series1) * len(series2):,} possible pairs ...")
    candidates = find_cross_candidates(series1, series2, threshold=THRESHOLD)
    print(f"  Candidate pairs found: {len(candidates)}")
    print()

    result_df = build_results(candidates, df1, df2, series1, series2)

    if result_df.empty:
        print("No candidate pairs found. Try lowering THRESHOLD.")
        return

    # Print similarity distribution
    print("Similarity distribution:")
    for lo, hi, label in [(90, 101, "90-100 %"), (70, 90, "70-89 %")]:
        n = ((result_df["similarity_pct"] >= lo) & (result_df["similarity_pct"] < hi)).sum()
        print(f"  {label} : {n} pairs")
    print()

    # Print a sample of the best matches
    print("Sample pairs (highest similarity first):")
    id1_col = f"s1_{ID_COL1}"
    id2_col = f"s2_{ID_COL2}"
    for _, row in result_df.head(8).iterrows():
        spec1 = str(row.get("s1_specification", row.get("s1_comparison_data", "")))[:35]
        spec2 = str(row.get("s2_specification", row.get("s2_comparison_data", "")))[:35]
        print(f"  {row['similarity_pct']:>3} %  {row[id1_col]} | {spec1:<35}  <->  {row[id2_col]} | {spec2}")
    print()

    # Save to Excel with three sheets:
    #   File1     — full original data from file 1
    #   File2     — full original data from file 2
    #   Duplicates — candidate pairs with similarity and context columns
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name="File1", index=False)
        df2.to_excel(writer, sheet_name="File2", index=False)
        result_df.to_excel(writer, sheet_name="Duplicates", index=False)

    print(f"Saved -> {os.path.basename(OUTPUT_FILE)}")
    print(f"  File1: {len(df1)} rows  |  File2: {len(df2)} rows  |  Duplicates: {len(result_df)} pairs")


if __name__ == "__main__":
    main()
