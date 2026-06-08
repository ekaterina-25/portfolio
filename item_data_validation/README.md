# Item Data Validation

A Python tool for validating industrial item master data against standardisation rules,
with an interactive correction workflow built in Streamlit.

Eight checks cover the quality gates that matter in practice: ERP field constraints,
naming convention rules, and cross-field consistency. Errors are grouped by fix effort —
some can be corrected automatically, others need a human decision.

## How to Test

**Try it online (recommended):** *(link coming once deployed)* — run instantly with
built-in demo data, upload your own Excel files, or use the sample files in the
[`data/`](data/) folder. No installation needed.

**Run locally:**
```bash
pip install streamlit pandas openpyxl
python -m streamlit run item_data_validation/app.py
```

---

## Business Problem

In industrial PIM and MDM projects, item master data arrives from multiple sources —
ERP systems, supplier data sheets, legacy catalogs — and rarely meets the quality
requirements for the target system. Before a migration or catalog harmonisation,
every item has to pass a set of rules:

- Product group codes and basic names must match the approved reference catalogue.
  An unknown code means the item cannot be classified in the ERP.
- Description fields must be uppercase and within the ERP character limit.
  Lowercase letters and overlong texts cause import failures or truncation.
- Forbidden symbols break import pipelines or display incorrectly in some system interfaces.
- The specification (model/type designator, e.g. `6204 2RS` or `M12X50 A4`) must appear
  verbatim in every language description — it is never translated, and its absence
  signals that the descriptions were built independently rather than from a template.

Manual review of these rules across hundreds or thousands of items is slow and error-prone.
This tool runs all checks in one pass and organises the results by what kind of fix is needed.

---

## Validation Checks

| # | Check | Type | Fix type |
|---|---|---|---|
| 1 | Product group code exists in reference catalogue | Reference | 💡 Suggestion |
| 2 | Basic name exists in reference catalogue | Reference | 💡 Suggestion |
| 3 | No forbidden symbols (Ø, °, `#`, `*`, `;`, curly quotes, etc.) | Field content | ✏️ Manual |
| 4 | Description and basic name fields are fully uppercase | Field content | 🔧 Auto-fix |
| 5 | No leading, trailing, or consecutive spaces | Field content | 🔧 Auto-fix |
| 6 | Field length within ERP import limits (descriptions max 40 chars, part numbers max 30) | Field length | ✏️ Manual |
| 7 | Basic name appears verbatim in the English description | Cross-field | ✏️ Manual |
| 8 | Specification appears verbatim in all non-empty description columns | Cross-field | ✏️ Manual |

**Why those specific symbols are forbidden:** `Ø` and `°` are encoding variants that
break SAP's default character set (CP1252/Latin-1). Curly quotes look identical to
straight quotes on screen but break exact-match lookups. `#`, `*`, and `;` are used
as field and record delimiters in flat-file export formats.

---

## Correction Workflow

After validation, errors are grouped into three types in the **Error fix** tab:

### 🔧 Auto-fix
Uppercase conversion and space normalisation are deterministic and risk-free: the
content is never lost, only formatted. These rows are pre-selected in the editor.

### 💡 Suggestion
For unknown product group codes and basic names, the closest match from the reference
catalogue is found using string similarity (`difflib.get_close_matches`, Ratcliff/Obershelp
algorithm). The two checks use different strategies:

- **basic_name** — the invalid name is compared directly against all approved names in
  the reference. Works well for abbreviations and minor spelling variations
  (`"Ball bearing"` → `"BALL BEARING"`).
- **product_group** — the product group code itself carries no meaning, so instead the
  item's English description is compared against the reference category descriptions.
  The code for the best-matching category is returned as the suggestion.

These rows are **not** pre-selected. String similarity finds the *closest match*, not
necessarily the *correct* match — `"BOLT"` could plausibly suggest `"EYE BOLT"` or
`"ANCHOR BOLT"` depending on what is in the reference. A human familiar with the product
needs to confirm.

### ✏️ Manual fix required
Forbidden symbols, field-length violations, and description consistency errors cannot
be fixed automatically — the correct value depends on the actual product. The user
types the corrected value directly in the editor.

The editor validates accepted values before applying: reference catalogue membership,
uppercase convention, field length, and forbidden symbols are all re-checked on the
proposed value so invalid fixes cannot be written back.

---

## Output

Clicking **Apply selected fixes** updates the data in memory and reruns all checks.
The **Download** tab exports a four-sheet Excel file:

| Sheet | Content |
|---|---|
| `original_data` | Source data, no check columns |
| `check_results_with_errors` | Full results with colour-coded check columns |
| `fixed_data` | Data after corrections: 🟢 green = corrected, 🟡 yellow = suggestion rejected |
| `final_check_summary` | Pass/fail counts and pass rate per check |

---

## Dataset

The demo data was generated synthetically based on the category structure and field
conventions used in industrial spare parts projects (bearings, fasteners, seals, filters,
pipe fittings, valves, and electrical components).

- **`validation_data.xlsx`** — 250 items across 9 columns.
  Realistic error distribution: uppercase violations (~22 items), space errors (~15),
  unknown product groups (~10), unknown basic names (~13), forbidden symbols (~16),
  field-length violations (~9), description consistency errors (~48).

- **`reference_data.xlsx`** — 88-row reference catalogue with product group codes,
  category descriptions, and approved basic names.

---

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — sidebar, KPI row, three tabs |
| `validate_items.py` | Validation logic, independent of any UI framework |
| `generate_synthetic_data.py` | Script used to create the demo dataset |
| `data/validation_data.xlsx` | Demo item data (250 rows) |
| `data/reference_data.xlsx` | Reference catalogue (88 rows) |

---

## Tools

Python · pandas · Streamlit · openpyxl
