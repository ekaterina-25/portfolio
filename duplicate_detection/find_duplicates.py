"""
Duplicate detection pipeline for product catalog data.

Logic:
  1. Normalize    — uppercase, expand abbreviations, standardise measurement formats
  2. Candidates   — TF-IDF on specification finds items with similar product codes
  3. Verification — within each candidate group, re-compute similarity using only
                    that group's own vocabulary (so "DN50" vs "DN100" score low even
                    though they share "PN16 SS316", because DN codes are distinctive)
  4. Discriminator filter (optional) — remove pairs where a key column differs,
                    e.g. DIN 931 vs DIN 933 for screws: same spec but different product
  5. Output       — duplicate groups with similarity % and configurable context columns

The similarity percentage is the minimum pairwise similarity within a group.
A high percentage means all members are very similar; a low percentage means
at least one pair is uncertain and should be reviewed more carefully.

Configure INPUT_FILE, SPEC_COL, DISCRIMINATOR_COL, and CONTEXT_COLS for each dataset.

Input:  see INPUT_FILE below
Output: sheet 'Duplicates' added to the same file
"""
import os
import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

# ── Configuration ─────────────────────────────────────────────────────────────
# Change these settings to run on a different input file.

INPUT_FILE   = os.path.join(os.path.dirname(__file__), "data", "spare_parts_system1.xlsx")
SHEET_NAME   = "Items"
RESULT_SHEET = "Duplicates"
ID_COL       = "item_id"       # column that uniquely identifies each row
SPEC_COL     = "specification" # primary comparison column (most unique field)

# Header row index in the Excel file (0 = first row is header)
HEADER_ROW = 0

# Discriminator column (optional) — if set, items with DIFFERENT values in this
# column are never grouped as duplicates, even if their specification is identical.
# Example for screws: "Standard" separates DIN 933 (full thread) from DIN 931
# (partial thread) which have the same dimensions but are different products.
# Set to None for datasets without such a distinguishing column.
DISCRIMINATOR_COL = None   # e.g. "Standard" for screw data

# Context columns shown in the output to help the reviewer decide if a group
# really contains duplicates. Include whichever original fields are most useful.
CONTEXT_COLS = ["name", "description_en", "description_fi", "specification",
                "category", "manufacturer"]

# Stage 1: TF-IDF on specification to find candidate pairs
CANDIDATE_THRESHOLD = 0.70   # lower = more candidates, more false positives

# Stage 2: within-group verification threshold
VERIFY_THRESHOLD = 0.60      # pairs below this are discarded from the group

# Common industrial abbreviations — only unambiguous ones included.
# Short or context-dependent abbreviations (NO, NC, ID, OD, GR, CYL) are excluded.
ABBREVS = {
    "BRG":  "BEARING",   "BRNG": "BEARING",
    "HYD":  "HYDRAULIC", "HYDR": "HYDRAULIC",
    "HEX":  "HEXAGON",
    "FLT":  "FILTER",    "FLTR": "FILTER",
    "VLV":  "VALVE",
    "MTR":  "MOTOR",
    "ASSY": "ASSEMBLY",
    "SCR":  "SCREW",
    "HDG":  "HOT DIP GALVANIZED",
}


# ── Step 1: Normalisation ─────────────────────────────────────────────────────

def normalize(text) -> str:
    """
    Standardise a text value so minor formatting differences do not prevent matching.

    - Uppercase everything
    - Expand common abbreviations (BRG → BEARING, HYD → HYDRAULIC, etc.)
    - Normalise measurement separators: 'M8 X 30', 'M8x30' → 'M8X30'
    - Collapse whitespace
    """
    if not text or pd.isna(text):
        return ""
    text = str(text).upper().strip()
    text = " ".join(ABBREVS.get(w, w) for w in text.split())
    text = re.sub(r"(\d)\s*[xX]\s*(\d)", r"\1X\2", text)
    return re.sub(r"\s+", " ", text).strip()


def combined_text(row) -> str:
    """Join all non-empty text columns into one string (for display in output)."""
    parts = [normalize(row[c]) for c in CONTEXT_COLS if c in row.index and pd.notna(row[c]) and str(row[c]).strip()]
    return " ".join(p for p in parts if p)


# ── Step 2: Candidate search ──────────────────────────────────────────────────

def find_candidates(spec_series: pd.Series,
                    threshold: float = CANDIDATE_THRESHOLD) -> set[tuple]:
    """
    Build a TF-IDF matrix on the comparison text and return pairs whose cosine
    similarity exceeds threshold.

    Character n-gram TF-IDF (3–5 chars) is used because it handles partial
    matches well: '6205-2RS1' and '6205 2RS' share the character sequence
    '6205' even though the full tokens differ.

    TF-IDF also weights rare terms (like '6205') more heavily than common terms
    (like 'GRADE' or 'ISO'), so the metric naturally focuses on product codes.
    """
    ids   = spec_series.index.tolist()
    texts = spec_series.fillna("").tolist()

    try:
        matrix = TfidfVectorizer(
            min_df=1, analyzer="char_wb", ngram_range=(3, 5)
        ).fit_transform(texts)
    except ValueError:
        return set()

    sim = cosine_similarity(matrix)
    return {
        (ids[i], ids[j])
        for i in range(len(ids))
        for j in range(i + 1, len(ids))
        if sim[i][j] >= threshold
    }


# ── Step 3: Within-group verification ────────────────────────────────────────

def verify_groups(candidate_pairs: set, spec_series: pd.Series,
                  threshold: float = VERIFY_THRESHOLD) -> dict[tuple, float]:
    """
    Group candidate pairs, then re-compute TF-IDF similarity *within each group*.

    Why within-group TF-IDF matters:
      In a global TF-IDF, 'DN50' and 'DN100' both appear rarely, so they get
      similar high weights and items look very alike. But within a group that
      contains several DN-sizes, 'DN50' appears multiple times and its IDF drops
      — making it a poor discriminator. Each unique size code keeps a high weight,
      so different-size items score LOW and are filtered out.

    Returns a dict of {(id_a, id_b): similarity_score} for confirmed pairs.
    """
    # Build groups via union-find
    all_ids = spec_series.index.tolist()
    parent  = {i: i for i in all_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for a, b in candidate_pairs:
        if a in parent and b in parent:
            union(a, b)

    groups: dict = defaultdict(list)
    for item_id in all_ids:
        groups[find(item_id)].append(item_id)

    # Within each group, compute TF-IDF similarity
    verified: dict[tuple, float] = {}

    for members in groups.values():
        if len(members) < 2:
            continue

        texts = [spec_series.get(m, "") for m in members]
        texts = [t if t else "" for t in texts]

        if all(t == "" for t in texts):
            continue

        try:
            matrix = TfidfVectorizer(
                min_df=1, analyzer="char_wb", ngram_range=(3, 5)
            ).fit_transform(texts)
            sim = cosine_similarity(matrix)
        except Exception:
            continue

        for i, a in enumerate(members):
            for j, b in enumerate(members):
                if i < j:
                    score = float(sim[i, j])
                    if score >= threshold:
                        verified[(min(a, b), max(a, b))] = round(score, 3)

    return verified


# ── Step 4: Build result table ────────────────────────────────────────────────

def apply_discriminator(verified: dict[tuple, float], df: pd.DataFrame,
                        id_col: str = ID_COL,
                        disc_col: str | None = DISCRIMINATOR_COL) -> dict[tuple, float]:
    """
    Remove pairs where the discriminator column has different non-empty values.

    Example: for screw data with disc_col = "Standard":
      - M20X60 8.8 (DIN 931)  vs  M20X60 8.8 (DIN 933)  → removed  (different standard)
      - M20X60 8.8 (DIN 933)  vs  M20X60 - 8.8 (DIN 933) → kept    (same standard)
      - M20X60 8.8 (DIN 933)  vs  M20X60 8.8 (empty)     → kept    (cannot determine)
    """
    if not disc_col or disc_col not in df.columns:
        return verified

    disc = df.set_index(id_col)[disc_col].fillna("").astype(str).to_dict()

    filtered = {}
    for (a, b), score in verified.items():
        val_a = disc.get(a, "").strip().upper()
        val_b = disc.get(b, "").strip().upper()
        # Keep if either is empty (can't determine) or they match
        if not val_a or not val_b or val_a == val_b:
            filtered[(a, b)] = score
    return filtered


def build_results(verified: dict[tuple, float], df: pd.DataFrame,
                  id_col: str = ID_COL) -> pd.DataFrame:
    """
    Convert verified pairs into a grouped result DataFrame.

    Each group gets a similarity_pct = the minimum pairwise similarity in the group
    (the weakest link). A high percentage means all members are very similar; a
    lower percentage means at least one pair is uncertain.

    Groups are sorted by similarity_pct descending so reviewers see the most
    confident matches first.
    """
    if not verified:
        return pd.DataFrame()

    # Group via union-find
    all_ids = df[id_col].tolist()
    parent  = {i: i for i in all_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in verified:
        parent[find(a)] = find(b)

    clusters: dict = defaultdict(list)
    for item_id in all_ids:
        clusters[find(item_id)].append(item_id)

    # Compute minimum pairwise similarity per group.
    # Only include pairs that are actually in verified — pairs that were not
    # verified (scored below VERIFY_THRESHOLD) are not counted, so they do not
    # pull the minimum down to zero.
    members_of: dict[str, set] = {
        root: set(members)
        for root, members in clusters.items()
        if len(members) > 1
    }
    group_min_sim: dict[str, float] = {}
    for root, members_set in members_of.items():
        scores = [
            score
            for (a, b), score in verified.items()
            if a in members_set and b in members_set
        ]
        group_min_sim[root] = round(min(scores) * 100) if scores else 0

    dup_items = {
        item_id: root
        for root, members in clusters.items()
        if len(members) > 1
        for item_id in members
    }

    if not dup_items:
        return pd.DataFrame()

    result = df[df[id_col].isin(dup_items)].copy()
    result = result.drop(columns=["duplicate_group", "similarity_pct"], errors="ignore")
    result.insert(1, "duplicate_group", result[id_col].map(dup_items))

    # Add similarity percentage before sorting
    result.insert(2, "similarity_pct",
                  result[id_col].map(dup_items).map(
                      lambda r: group_min_sim.get(r, 0)
                  ))

    result = (result
              .sort_values(["similarity_pct", "duplicate_group"], ascending=[False, True])
              .reset_index(drop=True))

    # Number groups 1, 2, 3 ... in display order (group 1 = highest similarity)
    seen: dict = {}
    counter = 0
    new_nums: list = []
    for gid in result["duplicate_group"]:
        if gid not in seen:
            counter += 1
            seen[gid] = counter
        new_nums.append(seen[gid])
    result["duplicate_group"] = new_nums

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── Load data ─────────────────────────────────────────────────────────────
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME, header=HEADER_ROW)
    print(f"Loaded {len(df)} rows from {os.path.basename(INPUT_FILE)}")
    if DISCRIMINATOR_COL:
        print(f"Discriminator column: '{DISCRIMINATOR_COL}'")
    print()

    # ── Step 1+2: Normalise and find candidates ───────────────────────────────
    spec_norm = df.set_index(ID_COL)[SPEC_COL].apply(normalize)

    print(f"Step 1+2 — TF-IDF on '{SPEC_COL}' (threshold {CANDIDATE_THRESHOLD}) ...")
    candidates = find_candidates(spec_norm)
    print(f"  Candidate pairs found: {len(candidates)}")

    # ── Step 3: Within-group verification ─────────────────────────────────────
    print(f"Step 3   — Within-group verification (threshold {VERIFY_THRESHOLD}) ...")
    verified = verify_groups(candidates, spec_norm)
    print(f"  Verified pairs kept:   {len(verified)}")

    # ── Step 4 (optional): Discriminator filter ───────────────────────────────
    if DISCRIMINATOR_COL:
        before = len(verified)
        verified = apply_discriminator(verified, df)
        removed = before - len(verified)
        print(f"Step 4   — Discriminator filter ('{DISCRIMINATOR_COL}'): "
              f"removed {removed} pairs with conflicting values")
    print()

    # ── Step 5: Build and save results ────────────────────────────────────────
    result_df = build_results(verified, df)

    if result_df.empty:
        print("No duplicate groups found.")
        return

    # Add combined_text (spec + context columns joined) for quick review
    result_df["combined_text"] = result_df.apply(combined_text, axis=1)

    # Output columns: ID + group info + context columns the user configured
    available_context = [c for c in CONTEXT_COLS if c in result_df.columns]
    if DISCRIMINATOR_COL and DISCRIMINATOR_COL not in available_context:
        available_context.append(DISCRIMINATOR_COL)

    out_cols = [ID_COL, "duplicate_group", "similarity_pct", "combined_text"] + available_context
    out_cols = [c for c in dict.fromkeys(out_cols) if c in result_df.columns]  # deduplicate, keep order

    with pd.ExcelWriter(INPUT_FILE, engine="openpyxl", mode="a",
                        if_sheet_exists="replace") as writer:
        result_df[out_cols].to_excel(writer, sheet_name=RESULT_SHEET, index=False)

    # ── Summary ───────────────────────────────────────────────────────────────
    n_groups = result_df["duplicate_group"].nunique()
    n_rows   = len(result_df)
    print(f"Sheet '{RESULT_SHEET}' written to {os.path.basename(INPUT_FILE)}")
    print(f"  Groups found : {n_groups}")
    print(f"  Rows flagged : {n_rows} / {len(df)} ({n_rows / len(df):.0%})")
    print(f"\n  similarity_pct distribution:")
    bins = result_df.drop_duplicates("duplicate_group")["similarity_pct"]
    for label, lo, hi in [("90–100 %", 90, 101), ("70–89 %", 70, 90), ("<70 %", 0, 70)]:
        n = ((bins >= lo) & (bins < hi)).sum()
        print(f"    {label} : {n} groups")

    print("\nSample groups (highest similarity first):")
    for grp in result_df["duplicate_group"].unique()[:4]:
        sub  = result_df[result_df["duplicate_group"] == grp]
        pct  = sub["similarity_pct"].iloc[0]
        disc = f"  [{DISCRIMINATOR_COL}]" if DISCRIMINATOR_COL else ""
        print(f"\n  Group {grp}  ({pct} %){disc}")
        for _, row in sub.iterrows():
            disc_val = f" | {row[DISCRIMINATOR_COL]}" if DISCRIMINATOR_COL and DISCRIMINATOR_COL in row else ""
            print(f"    {row[ID_COL]}: {str(row.get(SPEC_COL,''))[:45]}{disc_val}")


if __name__ == "__main__":
    main()
