# Duplicate Detection in Product Catalog Data

A Python pipeline for finding duplicate items in industrial spare parts catalogs
using TF-IDF text similarity and within-group verification.

---

## Business Problem

In Product Information Management (PIM) and Master Data Management (MDM), duplicate
records are a persistent and costly problem. The same physical product appears multiple
times in the catalog because:

- Different users fill in different fields for the same item
- Data is imported from multiple source systems (ERP, legacy databases, acquisitions)
- There is no enforced naming standard — the same bolt can be `M6X45 ZN 8.8`,
  `M6X45 - 8.8 ZN`, or `M6 x 45 zinc 8.8` depending on who entered it

**The result:** inflated catalog, incorrect inventory counts, and confusion when
ordering spare parts.

### When to run duplicate detection

Duplicate detection is typically run **per product group** (e.g., only bearings, only
fasteners). This gives cleaner results because items within the same group share
vocabulary and the algorithm can better distinguish meaningful differences.

However, there are situations where the entire catalog must be processed at once:

- Product group classifications are incomplete or incorrect
- Data was migrated from a legacy system without proper grouping
- A full catalog audit is required before a system migration

In these cases, the thresholds described below may need to be adjusted.

---

## How It Works

The pipeline has four stages:

### Stage 1 — Normalise

Before any comparison, text is standardised:

- All text converted to uppercase
- Common abbreviations expanded: `BRG` → `BEARING`, `HYD` → `HYDRAULIC`,
  `HEX` → `HEXAGON`, `FLT` → `FILTER`, `VLV` → `VALVE`
- Measurement formats unified: `M8 X 30`, `M8x30`, `M8X30` → all become `M8X30`

This ensures that two descriptions of the same product are not missed simply because
of formatting differences.

### Stage 2 — Candidate search (TF-IDF)

TF-IDF (Term Frequency – Inverse Document Frequency) converts each specification text
into a weighted vector. The key property: **rare terms get higher weight**.

In a catalog of 2 000 screws:
- `"ISO 4014"` appears in 1 800 items → low weight (not discriminating)
- `"M6X45"` appears in 3 items → high weight (very discriminating)

This means the similarity score naturally focuses on product codes and dimensions rather
than generic description words. Character n-grams (3–5 characters) are used instead of
full words, so `"6205-2RS1"` and `"6205 2RS"` are recognised as similar because they
share the character sequence `"6205"`.

All pairs with similarity ≥ `CANDIDATE_THRESHOLD` (default 0.70) are collected for
the next stage.

### Stage 3 — Within-group verification

The candidate groups from Stage 2 may contain false positives — items of the **same
type but different size**. To remove these, TF-IDF is re-calculated using only the
members of each candidate group.

Why this works: within a group containing O-rings of sizes 40×3, 50×3, and 60×3,
the term `"DIN 3771"` appears in all members → its weight drops to nearly zero. But
`"40X3"` appears only once → its weight becomes high. The different size codes now
dominate the similarity score, and the different-size items score low against each other.

For genuine duplicates (e.g., three entries for the same 6206 bearing), all members
share the same product code → high within-group similarity → confirmed as duplicates.

Pairs with within-group similarity ≥ `VERIFY_THRESHOLD` (default 0.60) are kept.

### Stage 4 — Discriminator filter (optional)

For product groups where a specific field distinguishes otherwise-identical items,
a **discriminator column** can be set. Items with different values in this column
are never grouped as duplicates — even if their specification text is identical.

**Example — screws:** `DIN 931` (partial thread) and `DIN 933` (full thread) have
the same dimensions but are completely different products. Without the discriminator,
`M20×60 8.8 (DIN 931)` and `M20×60 8.8 (DIN 933)` would be flagged as duplicates.
Setting `DISCRIMINATOR_COL = "Standard"` prevents this.

If one item has an empty discriminator value (the standard was not recorded), the pair
is kept for human review rather than automatically discarded.

---

## Output

Results are written as a new sheet (`Duplicates`) in the source Excel file.

| Column | Description |
|---|---|
| `duplicate_group` | Group number — all items with the same number are potential duplicates |
| `similarity_pct` | Minimum pairwise similarity within the group (0–100 %). Higher = more confident match. |
| `combined_text` | Normalised text used for comparison — shows what the algorithm "saw" |
| *(context columns)* | Original fields configured in `CONTEXT_COLS` for human review |

**How to interpret similarity_pct:**

| Range | Meaning |
|---|---|
| 90–100 % | Very high confidence — likely the same product with minor formatting differences |
| 70–89 % | Good match — review the specification and discriminator fields |
| 60–69 % | Borderline — at least one pair in the group is uncertain; review carefully |

Groups are sorted from highest to lowest similarity so reviewers can start with the
most confident matches.

---

## Dataset

The demo uses a synthetic spare parts catalog generated by `generate_synthetic_data.py`.

- **`spare_parts_system1.xlsx`** — 204 items, single catalog
  - 9 categories: Bearings, Seals & Gaskets, Bolts & Fasteners, Filters,
    Pumps & Valves, Electrical, Mechanical, Pipe Fittings, Lubrication
  - ~30 % of items are intentional duplicates with different field combinations
  - ~35 % of rows have at least one empty text field (realistic data quality)
  - Multilingual: `description_en` (English) and `description_fi` (Finnish)

- **`spare_parts_system2.xlsx`** — 165 items, simulates a second ERP system with
  overlapping products formatted differently *(cross-system comparison — planned)*

---

## Configuration

All settings are at the top of `find_duplicates.py`. Change these to run on a
different file or product group:

```python
INPUT_FILE          = "data/spare_parts_system1.xlsx"
SHEET_NAME          = "Items"
ID_COL              = "item_id"        # column with unique item identifier
SPEC_COL            = "specification"  # primary comparison field
HEADER_ROW          = 0               # row index of column headers (0 = first row)

DISCRIMINATOR_COL   = None            # set to e.g. "Standard" for screws
CONTEXT_COLS        = ["name", "description_en", "description_fi",
                        "specification", "category", "manufacturer"]

CANDIDATE_THRESHOLD = 0.70  # stage 2: first-pass similarity filter
VERIFY_THRESHOLD    = 0.60  # stage 3: within-group confirmation threshold
```

### Threshold tuning

The default thresholds work well for well-filled specification data. Adjust based
on your data:

| Situation | Recommendation |
|---|---|
| Specification field well-filled (>90 % of rows) | Keep defaults 0.70 / 0.60 |
| Specification partially filled or inconsistent | Lower to 0.65 / 0.50 |
| Very large catalog (>50 000 rows) | Raise candidate threshold to 0.80 to limit pair count |
| Only comparing within one product group | Can lower both thresholds slightly |

---

## How to Run

**Install dependencies:**
```bash
pip install pandas scikit-learn openpyxl fuzzywuzzy python-Levenshtein sentence-transformers
```

**Generate demo data:**
```bash
python generate_synthetic_data.py
```

**Find duplicates:**
```bash
python find_duplicates.py
```

The `Duplicates` sheet is added to the source Excel file.

**Compare methods (optional):**
```bash
python compare_methods.py
```
Writes three sheets (A_Numeric, B_Fuzzy, C_Semantic) for method comparison.

---

## Example Results

### Example 1 — Multi-column duplicate (synthetic data)

This group shows why checking one column at a time is not enough.
Each row has different fields filled in, and the name uses different abbreviations and word order:

| item_id | similarity_pct | name | description_en | specification |
|---|---|---|---|---|
| ITM-10054 | 87 % | `BEARING BALL 6206` | *(empty)* | `6206 2RS 30X62X16` |
| ITM-10102 | 87 % | `BALL BEARING 6206 2RS` | `DEEP GROOVE BALL BEARING` | `6206 2RS 30X62X16` |
| ITM-10140 | 87 % | `BALL BEARING 6206 2RS` | *(empty)* | `30X62X16 6206` |

All three describe the same 6206 deep groove ball bearing.
- Row 1: no description, abbreviated name (`BEARING BALL` vs `BALL BEARING`)
- Row 3: specification written in reverse order (`30X62X16 6206` instead of `6206 2RS 30X62X16`)

A simple exact-match or even column-by-column search would miss these.

---

### Example 2 — Discriminator prevents false match (screw data)

Without a discriminator column, these two screws would be flagged as duplicates
because their specification is identical:

| Number | name | specification | Standard |
|---|---|---|---|
| 0503201 | `HEX BOLT M20X60 8.8` | `M20X60 - 8.8` | `EN ISO 4014, DIN 931` (partial thread) |
| 0612847 | `HEX BOLT M20X60 8.8` | `M20X60 - 8.8` | `EN ISO 4017, DIN 933` (full thread) |

Setting `DISCRIMINATOR_COL = "Standard"` keeps them separate — they are physically
different products even though the dimensions and grade are identical.

---

### Example 3 — Screw dataset summary

Running on 2 300 screws with `Standard` column as discriminator:

```
Step 1+2 — TF-IDF on specification (threshold 0.70)
  Candidate pairs: 3 385

Step 3 — Within-group verification (threshold 0.60)
  Verified pairs: 2 293

Step 4 — Discriminator filter (Standard column)
  Removed 1 414 pairs with conflicting standards (DIN 931 vs DIN 933, etc.)
  Remaining verified pairs: 879

Groups found: 166  |  Rows flagged: 524 / 2 300  (23 %)
```

Sample group — same screw, entered twice with slightly different text:

| Number | similarity_pct | name | specification | Standard |
|---|---|---|---|---|
| 2001144 | 100 % | `7/16 UNC COATED SCREW` | `7/16 UNC x 1 COATED` | ANSI B18.3-8.8 ZNE |
| 2001140 | 100 % | `7/16 UNC COATED BOLT` | `7/16 UNC x 1 COATED` | ANSI B18.3-8.8 ZNE |

The specifications are identical but the names differ slightly — an exact-match
deduplication would not catch this pair.
