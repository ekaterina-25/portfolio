# Duplicate Detection in Product Catalog Data

A Python pipeline for finding duplicate items in industrial spare parts catalogs
using TF-IDF text similarity. Two modes are supported:

- **Within-file** — finds duplicate items inside a single catalog file
- **Cross-file** — finds matching items between two files from different source systems

**Try it online:** [Open the Streamlit app](https://ekaterina-25-portfolio-duplicate-detectionapp-gubecm.streamlit.app) — run instantly with built-in demo datasets, upload your own Excel file, or use the sample files in the [`data/`](data/) folder. No installation needed.

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

The problem appears in two common scenarios:

| Scenario | Mode |
|---|---|
| The same product has been entered more than once within one system | Within-file |
| Two systems hold overlapping catalogs, e.g. after an acquisition or before a system migration | Cross-file |

---

## How It Works

Both modes share the same normalisation step. After that the pipelines differ.

### Step 1 — Normalise (both modes)

Before any comparison, text is standardised:

- All text converted to uppercase
- Common abbreviations expanded: `BRG` → `BEARING`, `HYD` → `HYDRAULIC`,
  `HEX` → `HEXAGON`, `FLT` → `FILTER`, `VLV` → `VALVE`
- Measurement formats unified: `M8 X 30`, `M8x30`, `M8X30` → all become `M8X30`

Multiple columns (e.g. `specification` + `name`) can be combined into one text per item.
If a column is empty for a row it is skipped, so adding `name` as a fallback ensures
items without a specification are still compared via their name.

---

### Within-file pipeline

**Step 2 — Candidate search (TF-IDF)**

TF-IDF (Term Frequency – Inverse Document Frequency) converts each specification text
into a weighted vector. The key property: **rare terms get higher weight**.

In a catalog of 2 000 screws:
- `"ISO 4014"` appears in 1 800 items → low weight (not discriminating)
- `"M6X45"` appears in 3 items → high weight (very discriminating)

Character n-grams (3–5 characters) are used instead of full words, so `"6205-2RS1"`
and `"6205 2RS"` are recognised as similar because they share the character sequence `"6205"`.

All pairs with similarity ≥ `CANDIDATE_THRESHOLD` (default 0.70) are collected.

**Step 3 — Within-group verification**

The candidate groups may contain false positives — items of the **same type but
different size**. To remove these, TF-IDF is re-calculated using only the members of
each candidate group.

Why this works: within a group containing O-rings of sizes 40×3, 50×3, and 60×3,
the term `"DIN 3771"` appears in all members → its weight drops to nearly zero. But
`"40X3"` appears only once → its weight becomes high. The different size codes now
dominate the similarity score, and different-size items score low against each other.

For genuine duplicates (e.g., three entries for the same 6206 bearing), all members
share the same product code → high within-group similarity → confirmed as duplicates.

Pairs with within-group similarity ≥ `VERIFY_THRESHOLD` (default 0.60) are kept.

**Step 4 — Discriminator filter (optional)**

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

### Cross-file pipeline

**Step 2 — TF-IDF on combined corpus**

All texts from **both files** are fed to the TF-IDF vectorizer together. This is the
key difference from within-file: IDF weights are calculated globally across both systems.

A product code like `"6206"` that appears in only 2 items across both files gets a high
weight regardless of which file it comes from. A generic term like `"ISO"` that appears
hundreds of times gets a low weight. This ensures that the same rare product code is
weighted consistently whether it appears in system 1 or system 2.

**Step 3 — Cross-file similarity matrix**

Cosine similarity is computed only for cross-file pairs: every item in file 1 against
every item in file 2. This gives an *m × n* matrix where *m* = rows in file 1 and
*n* = rows in file 2.

File 1 vs file 1 and file 2 vs file 2 comparisons are skipped — the goal is to find
items that exist in both systems, not duplicates within a single system.

All pairs with similarity ≥ threshold are collected and sorted by file 1 item ID,
then similarity descending. This groups all potential matches for one item together
so the reviewer sees the best match first.

**No within-group verification step**

Within-group verification is not used in cross-file mode. The purpose of that step in
within-file mode is to filter out "same type, different size" false positives by
re-weighting terms inside each candidate group. In cross-file mode the output is
already a flat list of individual candidate pairs for human review — there is no group
structure to re-verify.

---

## Output

### Within-file output

Results are saved as a two-sheet Excel file:
- **Data** — the original file as uploaded
- **Duplicates** — the detected duplicate groups

| Column | Description |
|---|---|
| `duplicate_group` | Group number — all items with the same number are potential duplicates |
| `similarity_pct` | Minimum pairwise similarity within the group (0–100 %). Higher = more confident. |
| `comparison_data` | Normalised text used for comparison — shows what the algorithm "saw" |
| *(context columns)* | Original fields selected in the app for human review |

Groups are sorted from highest to lowest similarity so reviewers can start with the
most confident matches.

### Cross-file output

Results are saved as a three-sheet Excel file:
- **File1** — original data from file 1
- **File2** — original data from file 2
- **Duplicates** — candidate pairs

| Column | Description |
|---|---|
| `similarity_pct` | Match strength (0–100 %). Higher = more likely the same product. |
| `s1_<id>` | Item identifier from file 1 |
| `s1_comparison_data` | Normalised text from file 1 used for comparison |
| `s2_<id>` | Item identifier from file 2 |
| `s2_comparison_data` | Normalised text from file 2 used for comparison |
| `s1_<col>`, `s2_<col>` | Reference columns from each file, interleaved for side-by-side comparison |

Rows are sorted by file 1 item ID first, then similarity descending — so all candidates
for the same file 1 item appear together with the best match on top.

**How to interpret similarity_pct (both modes):**

| Range | Meaning |
|---|---|
| 90–100 % | Very high confidence — likely the same product with minor formatting differences |
| 70–89 % | Review needed — specification and key fields should be compared manually |
| 60–69 % | Borderline — at least one pair is uncertain; review carefully |
| 50–59 % | Low confidence — only shown when threshold is set below 0.60 |

---

## Dataset

- **`spare_parts_system1.xlsx`** — 204 items, single catalog
  - 9 categories: Bearings, Seals & Gaskets, Bolts & Fasteners, Filters,
    Pumps & Valves, Electrical, Mechanical, Pipe Fittings, Lubrication
  - ~30 % of items are intentional duplicates with different field combinations
  - ~35 % of rows have at least one empty text field (realistic data quality)
  - Multilingual: `description_en` (English) and `description_fi` (Finnish)

- **`spare_parts_system2.xlsx`** — 165 items, simulates a second ERP system
  - Same category structure, overlapping products formatted differently
  - Designed for cross-file comparison against system1
  - Names and specifications use different conventions for the same products

- **`spare_parts_screws.xlsx`** — 218 items, screw catalog with standard codes
  - Intentional duplicate groups (same screw, slight naming variation)
  - Discriminator test pairs: same specification but different `Standard` value (DIN 931 vs DIN 933)
  - Demonstrates how the discriminator column prevents false matches

---

## Configuration

### Within-file (`find_duplicates.py`)

```python
INPUT_FILE          = "data/spare_parts_system1.xlsx"
SHEET_NAME          = "Items"
ID_COL              = "item_id"        # column with unique item identifier
SPEC_COL            = "specification"  # primary comparison field
HEADER_ROW          = 0

DISCRIMINATOR_COL   = None            # set to e.g. "Standard" for screws
CONTEXT_COLS        = ["name", "description_en", "description_fi",
                        "specification", "category", "manufacturer"]

CANDIDATE_THRESHOLD = 0.70  # stage 2: first-pass similarity filter
VERIFY_THRESHOLD    = 0.60  # stage 3: within-group confirmation threshold
```

**Threshold tuning:**

| Situation | Recommendation |
|---|---|
| Specification field well-filled (>90 % of rows) | Keep defaults 0.70 / 0.60 |
| Specification partially filled or inconsistent | Lower to 0.65 / 0.50 |
| Very large catalog (>50 000 rows) | Raise candidate threshold to 0.80 to limit pair count |
| Only comparing within one product group | Can lower both thresholds slightly |

### Cross-file (`find_duplicates_cross_file.py`)

```python
FILE1          = "data/spare_parts_system1.xlsx"
FILE2          = "data/spare_parts_system2.xlsx"
ID_COL1        = "item_id"
ID_COL2        = "item_id"

# Defined separately — the two files may use different column names
COMPARE_COLS1  = ["specification", "name"]
COMPARE_COLS2  = ["specification", "name"]

CONTEXT_COLS1  = ["name", "description_en", "specification", "category"]
CONTEXT_COLS2  = ["name", "description_en", "specification", "category"]

THRESHOLD      = 0.70
```

**Threshold tuning:**

| Situation | Recommendation |
|---|---|
| Both files have well-filled specification fields | Keep default 0.70 |
| Files use very different terminology for the same products | Lower to 0.60 |
| One file has many generic descriptions without product codes | Raise to 0.75–0.80 |

---

## How to Run

### Option 1 — Streamlit web app (recommended)

**Live app:** [https://ekaterina-25-portfolio-duplicate-detectionapp-gubecm.streamlit.app](https://ekaterina-25-portfolio-duplicate-detectionapp-gubecm.streamlit.app)

The app has two modes selectable at the top of the sidebar:

**Within-file** — find duplicate items inside one Excel file
- Select comparison columns, discriminator column, and context columns
- Adjust two similarity thresholds with sliders
- Browse duplicate groups colour-coded by confidence level
- Download: two-sheet Excel (*Data* = original, *Duplicates* = results)

**Cross-file** — find matching items between two files from different source systems
- Upload two files independently with their own column mappings
- Select comparison columns and reference columns separately for each file
- Results show pairs side by side: `s1_name | s2_name | s1_specification | s2_specification ...`
- Download: three-sheet Excel (*File1*, *File2*, *Duplicates*)

**Sample files** in the `data/` folder:
- `spare_parts_system1.xlsx` — try within-file mode, use `specification` as comparison column
- `spare_parts_system2.xlsx` — try cross-file mode against system1
- `spare_parts_screws.xlsx` — try within-file with `Standard` as discriminator column

**Run locally:**
```bash
pip install streamlit pandas scikit-learn openpyxl plotly
python -m streamlit run duplicate_detection/app.py
```

---

### Option 2 — Command line

**Within-file:**
```bash
python find_duplicates.py
```
Edit the configuration block at the top of `find_duplicates.py` to point to your file.
The `Duplicates` sheet is added to the source Excel file.

**Cross-file:**
```bash
python find_duplicates_cross_file.py
```
Edit `FILE1`, `FILE2`, `COMPARE_COLS1`, `COMPARE_COLS2` at the top of the script.
Output is saved to `data/cross_file_candidates.xlsx` with three sheets.

---

## Example Results

### Example 1 — Within-file: multi-column duplicate

This group shows why checking one column at a time is not enough.
Each row has different fields filled in, and the name uses different abbreviations:

| item_id | similarity_pct | name | description_en | specification |
|---|---|---|---|---|
| ITM-10054 | 87 % | `BEARING BALL 6206` | *(empty)* | `6206 2RS 30X62X16` |
| ITM-10102 | 87 % | `BALL BEARING 6206 2RS` | `DEEP GROOVE BALL BEARING` | `6206 2RS 30X62X16` |
| ITM-10140 | 87 % | `BALL BEARING 6206 2RS` | *(empty)* | `30X62X16 6206` |

All three describe the same 6206 deep groove ball bearing.
- Row 1: no description, abbreviated name (`BEARING BALL` vs `BALL BEARING`)
- Row 3: specification written in reverse order (`30X62X16 6206` instead of `6206 2RS 30X62X16`)

A simple exact-match or column-by-column search would miss these.

---

### Example 2 — Within-file: discriminator prevents false match

Without a discriminator column, these two screws would be flagged as duplicates
because their specification is identical:

| item_id | name | specification | Standard |
|---|---|---|---|
| ITM-1001 | `HEX BOLT M20X60 8.8` | `M20X60 - 8.8` | `EN ISO 4014, DIN 931` (partial thread) |
| ITM-1002 | `HEX BOLT M20X60 8.8` | `M20X60 - 8.8` | `EN ISO 4017, DIN 933` (full thread) |

Setting `DISCRIMINATOR_COL = "Standard"` keeps them separate — they are physically
different products even though the dimensions and grade are identical.

---

### Example 3 — Cross-file: same item in two systems

Running cross-file detection on system1 (204 rows) vs system2 (165 rows) with threshold 0.70
found 146 candidate pairs: 81 at 90–100 % and 65 at 70–89 %.

High-confidence matches (100 %) are items entered identically in both systems:

| similarity_pct | s1_item_id | s1_specification | s2_item_id | s2_specification |
|---|---|---|---|---|
| 100 % | ITM-10004 | `6012-2RS1 60X95X18MM` | SYS2-20055 | `6012-2RS1 60X95X18MM` |
| 100 % | ITM-10025 | `M16X150 ZINC PLATED HILTI` | SYS2-20008 | `M16X150 ZINC PLATED HILTI` |
| 100 % | ITM-10057 | `DN100 PN16 SS316L DIN 2576` | SYS2-20053 | `DN100 PN16 SS316L DIN 2576` |

One item can have multiple candidates when the other system contains several similar entries:

| similarity_pct | s1_item_id | s1_specification | s2_item_id | s2_specification |
|---|---|---|---|---|
| 96 % | ITM-10006 | `M16 X 60 10.9` | SYS2-20043 | *(name only: HEX BOLT M16X60 10.9)* |
| 73 % | ITM-10006 | `M16 X 60 10.9` | SYS2-20005 | `HEXAGON HEAD BOLT` |

Both rows belong to the same system1 item. The 96 % match is very likely the same product;
the 73 % match shares only the bolt type and size in the name, and needs manual review.
