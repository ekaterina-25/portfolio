"""
Comparison of three duplicate detection methods on the same product catalog.

Runs three methods on the combined text (Name + Description EN + Description FI +
Specification) and reports how many duplicate candidates each method finds.
Results are saved as separate sheets in the source Excel file.

Methods:
  A — Numeric codes   : extracts number sequences, groups items sharing the same codes
  B — Fuzzy matching  : token-sort string similarity (fuzzywuzzy)
  C — Semantic NLP    : sentence-transformer embeddings + cosine similarity

When to use each:
  A  Best for electrical components, bearings, spare parts with unique catalog numbers.
     Fast and precise — ignores word order and descriptions, focuses on numeric IDs.
  B  Best for items described in natural language where product numbers are short or
     absent. Handles word order variations but is sensitive to abbreviations.
  C  Best for multilingual data or items where meaning matters more than exact words.
     Slowest but most flexible.
"""
import os
import re
import pandas as pd
import numpy as np
from collections import defaultdict

# ── Configuration ─────────────────────────────────────────────────────────────
INPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "spare_parts_system1.xlsx")
SHEET_NAME = "Items"

# Columns combined to form the text used for comparison
TEXT_COLS = ["name", "description_en", "description_fi", "specification"]

# Method A — Numeric codes
MIN_NUMBER_LENGTH = 4    # minimum digits to count as a product code (filters out "8", "16", etc.)
NUMERIC_THRESHOLD = 1.0  # fraction of codes that must match (1.0 = all codes must be shared)

# Method B — Fuzzy matching
FUZZY_THRESHOLD = 85     # 0–100; 85 means texts must be ≥ 85 % similar

# Method C — Semantic NLP
SEMANTIC_MODEL     = "paraphrase-MiniLM-L6-v2"
SEMANTIC_THRESHOLD = 0.92


# ── Text helpers ──────────────────────────────────────────────────────────────

def combine_text(row) -> str:
    """Join all non-empty text columns into one string for comparison."""
    parts = [str(row[col]).strip() for col in TEXT_COLS
             if pd.notna(row[col]) and str(row[col]).strip()]
    return " ".join(parts)


# ── Method A: Numeric code matching ──────────────────────────────────────────

def method_a_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract numeric sequences from the combined text and group items that share
    the same significant numbers (length >= MIN_NUMBER_LENGTH).

    Why it works: product identifiers like '6205', '3RT2015', '102030' are unique
    to a specific product. If two rows share these numbers, they likely describe
    the same item even if the surrounding text is completely different.

    Inspired by the approach used in the author's thesis work on electrical
    component duplicate detection.
    """
    number_pattern = re.compile(r'\d+')
    results = []

    texts  = df["combined_text"].fillna("").tolist()
    ids    = df["item_id"].tolist()
    indices = list(range(len(texts)))

    for i in indices:
        # Extract numbers long enough to be product codes
        nums_i = {int(m) for m in number_pattern.findall(texts[i])
                  if len(m) >= MIN_NUMBER_LENGTH}
        if not nums_i:
            continue
        for j in range(i + 1, len(indices)):
            nums_j = {int(m) for m in number_pattern.findall(texts[j])
                      if len(m) >= MIN_NUMBER_LENGTH}
            if not nums_j:
                continue
            intersection = nums_i & nums_j
            if intersection:
                score = len(intersection) / max(len(nums_i), len(nums_j))
                if score >= NUMERIC_THRESHOLD:
                    results.append((ids[i], ids[j], str(intersection), round(score, 3)))

    if not results:
        return pd.DataFrame(columns=["item_id_1", "item_id_2", "matching_codes", "score"])

    pairs_df = pd.DataFrame(results, columns=["item_id_1", "item_id_2", "matching_codes", "score"])
    pairs_df = pairs_df.drop_duplicates(subset=["item_id_1", "item_id_2"])

    # Convert pairs to groups using union-find
    return _pairs_to_groups(pairs_df, df)


# ── Method B: Fuzzy string matching ──────────────────────────────────────────

def method_b_fuzzy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare combined texts using fuzzywuzzy token_sort_ratio.

    token_sort_ratio sorts the words alphabetically before comparing, so
    'BALL BEARING 6205' and 'BEARING BALL 6205' both become '6205 BALL BEARING'
    and score 100. This handles word order variations common in product data.

    Limitation: sensitive to abbreviations — 'BRG' and 'BEARING' score low
    because the characters differ, even though they mean the same thing.
    """
    try:
        from fuzzywuzzy import fuzz
    except ImportError:
        print("  fuzzywuzzy not installed — run: pip install fuzzywuzzy python-Levenshtein")
        return pd.DataFrame()

    texts = df["combined_text"].fillna("").tolist()
    ids   = df["item_id"].tolist()
    results = []

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            score = fuzz.token_sort_ratio(texts[i], texts[j])
            if score >= FUZZY_THRESHOLD:
                results.append((ids[i], ids[j], score))

    if not results:
        return pd.DataFrame(columns=["item_id_1", "item_id_2", "score"])

    pairs_df = pd.DataFrame(results, columns=["item_id_1", "item_id_2", "score"])
    return _pairs_to_groups(pairs_df, df)


# ── Method C: Semantic NLP ────────────────────────────────────────────────────

def method_c_semantic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode combined texts as sentence-transformer embeddings and compute
    pairwise cosine similarity.

    The model understands meaning rather than exact words, so 'BRG' and 'BEARING'
    are handled better than with fuzzy matching. Also works across languages —
    if description_fi is present, it adds context that helps with matching.
    """
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = df["combined_text"].fillna("").tolist()
    ids   = df["item_id"].tolist()

    model      = SentenceTransformer(SEMANTIC_MODEL)
    embeddings = model.encode(texts, show_progress_bar=False)
    sim_matrix = cosine_similarity(embeddings)

    results = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if sim_matrix[i][j] >= SEMANTIC_THRESHOLD:
                results.append((ids[i], ids[j], round(float(sim_matrix[i][j]), 3)))

    if not results:
        return pd.DataFrame(columns=["item_id_1", "item_id_2", "score"])

    pairs_df = pd.DataFrame(results, columns=["item_id_1", "item_id_2", "score"])
    return _pairs_to_groups(pairs_df, df)


# ── Shared helper: pairs → groups ─────────────────────────────────────────────

def _pairs_to_groups(pairs_df: pd.DataFrame, source_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert a list of similar pairs into a grouped result DataFrame.
    Uses union-find so each item appears in exactly one group.
    """
    all_ids = source_df["item_id"].tolist()
    parent  = {i: i for i in all_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for _, row in pairs_df.iterrows():
        union(row["item_id_1"], row["item_id_2"])

    clusters: dict = defaultdict(list)
    for item_id in all_ids:
        clusters[find(item_id)].append(item_id)

    dup_ids = {item_id: root for root, members in clusters.items()
               if len(members) > 1 for item_id in members}

    if not dup_ids:
        return pd.DataFrame()

    result = source_df[source_df["item_id"].isin(dup_ids)].copy()
    result.insert(1, "duplicate_group", result["item_id"].map(dup_ids))

    # Re-number groups 1, 2, 3 ...
    gmap = {old: new for new, old in enumerate(sorted(result["duplicate_group"].unique()), 1)}
    result["duplicate_group"] = result["duplicate_group"].map(gmap)
    result = result.sort_values("duplicate_group").reset_index(drop=True)

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load data and build combined text
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
    df["combined_text"] = df.apply(combine_text, axis=1)
    print(f"Loaded {len(df)} rows\n")

    results = {}

    # Run Method A
    print("Method A — Numeric code matching ...")
    results["A_Numeric"] = method_a_numeric(df)
    n = results["A_Numeric"]["duplicate_group"].nunique() if not results["A_Numeric"].empty else 0
    print(f"  Groups found: {n}  |  Rows flagged: {len(results['A_Numeric'])}\n")

    # Run Method B
    print("Method B — Fuzzy string matching ...")
    results["B_Fuzzy"] = method_b_fuzzy(df)
    n = results["B_Fuzzy"]["duplicate_group"].nunique() if not results["B_Fuzzy"].empty else 0
    print(f"  Groups found: {n}  |  Rows flagged: {len(results['B_Fuzzy'])}\n")

    # Run Method C
    print(f"Method C — Semantic NLP ({SEMANTIC_MODEL}) ...")
    results["C_Semantic"] = method_c_semantic(df)
    n = results["C_Semantic"]["duplicate_group"].nunique() if not results["C_Semantic"].empty else 0
    print(f"  Groups found: {n}  |  Rows flagged: {len(results['C_Semantic'])}\n")

    # Save all results as sheets in the source file
    output_cols = ["item_id", "duplicate_group", "combined_text"] + TEXT_COLS + ["category", "manufacturer", "unit"]
    with pd.ExcelWriter(INPUT_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        for sheet_name, result_df in results.items():
            if result_df.empty:
                pd.DataFrame({"message": ["No duplicates found"]}).to_excel(
                    writer, sheet_name=sheet_name, index=False)
            else:
                available = [c for c in output_cols if c in result_df.columns]
                result_df[available].to_excel(writer, sheet_name=sheet_name, index=False)

    # Print comparison summary
    print("=" * 55)
    print(f"{'Method':<25} {'Groups':>7} {'Rows flagged':>13} {'% of catalog':>13}")
    print("-" * 55)
    for name, rdf in results.items():
        if rdf.empty:
            print(f"{name:<25} {'—':>7} {'—':>13} {'—':>13}")
        else:
            g = rdf["duplicate_group"].nunique()
            r = len(rdf)
            print(f"{name:<25} {g:>7} {r:>13} {r/len(df):>12.0%}")
    print("=" * 55)
    print(f"\nResults saved to {os.path.basename(INPUT_FILE)}")
    print("Sheets: A_Numeric, B_Fuzzy, C_Semantic")


if __name__ == "__main__":
    main()
