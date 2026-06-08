# -*- coding: utf-8 -*-
"""
Item data validation logic — independent of any UI framework.

Each check mirrors a real quality gate used during item master data
harmonisation projects: ERP field constraints, naming convention rules,
and cross-field consistency checks.

Returns
-------
run_checks : original DataFrame + one result column per check.
  Boolean checks  → True (pass) / False (fail)
  String checks   → "ok" (pass) / comma-separated list of offending columns
summary   : aggregated pass/fail counts and pass rate per check.
"""

import re
import pandas as pd

# Characters that cause problems in ERP import pipelines or display:
#   Ø, °  — encoding variants that break SAP's default character set (CP1252/Latin-1)
#   "     — curly quote that looks like a straight quote but isn't; breaks parsing
#   # * ; — used as field/record delimiters in some flat-file export formats
#   remaining symbols — structurally ambiguous or reserved in XML/JSON export schemas
FORBIDDEN_SYMBOLS = [
    chr(0xD8),    # Ø  — encoding variant that breaks SAP CP1252 import
    chr(0xB0),    # °  — same issue; write "DEG" instead in item data
    chr(0x201C),  # left curly quote, visually identical to straight quote but breaks exact-match
    "#", "'", "*", ";",
    "?", "!", "\\", "|", "[", "]", "{", "}", "=",
]

# All free-text columns that carry item content — status is an internal
# workflow field and intentionally excluded from content checks.
TEXT_COLS = [
    "basic_name", "specification",
    "description_en", "description_fi", "description_de",
    "product_code",
]

# ERP description fields must be uppercase so they display consistently
# across all system interfaces. product_code is excluded because
# manufacturer part numbers legitimately contain mixed-case brand prefixes
# (e.g. "SKF-6204-2RS1", "Continental-SPZ800").
UPPERCASE_COLS = ["basic_name", "description_en", "description_fi", "description_de"]

# SAP short-text fields are capped at 40 characters; the manufacturer
# part number field at 30. Exceeding these truncates data on import.
DESC_COLS  = ["description_en", "description_fi", "description_de"]
DESC_LIMIT = 40
CODE_LIMIT = 30


def load_reference(path: str) -> pd.DataFrame:
    """Load the product group reference catalogue from an Excel file."""
    return pd.read_excel(path)


def run_checks(items: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """
    Run all validation checks and append result columns to a copy of items.

    Boolean result columns (True = pass):
        check_product_group, check_basic_name, check_name_in_desc

    String result columns ("ok" = pass, otherwise lists the offending columns):
        check_symbols, check_uppercase, check_spaces,
        check_length, check_spec_in_desc
    """
    df = items.copy()
    df = df.fillna("")
    df[TEXT_COLS] = df[TEXT_COLS].astype(str)

    # Pre-build lookup sets for fast membership testing across all rows.
    valid_groups = set(ref["product_group_id"].astype(str))
    valid_names  = set(ref["basic_name"].dropna().astype(str))

    # ------------------------------------------------------------------
    # Check 1 — Product group must exist in the reference catalogue.
    # An unknown code means the item cannot be classified in the ERP.
    # ------------------------------------------------------------------
    df["check_product_group"] = df["product_group"].astype(str).isin(valid_groups)

    # ------------------------------------------------------------------
    # Check 2 — Basic name must be a term approved in the reference catalogue.
    # Free-text names lead to inconsistent search results and duplicate items.
    # ------------------------------------------------------------------
    df["check_basic_name"] = df["basic_name"].isin(valid_names)

    # ------------------------------------------------------------------
    # Check 3 — No forbidden symbols in any content field.
    # Returns a semicolon-separated list of "column: symbol" pairs so the
    # user knows exactly where to look.
    # ------------------------------------------------------------------
    def _symbols(row):
        hits = []
        for col in TEXT_COLS:
            val = str(row[col])
            found = [s for s in FORBIDDEN_SYMBOLS if s in val]
            if found:
                hits.append(f"{col}: {', '.join(found)}")
        return "; ".join(hits) if hits else "ok"

    df["check_symbols"] = df.apply(_symbols, axis=1)

    # ------------------------------------------------------------------
    # Check 4 — Description and basic name fields must be fully uppercase.
    # Returns a comma-separated list of columns that contain lowercase.
    # ------------------------------------------------------------------
    def _uppercase(row):
        bad = []
        for col in UPPERCASE_COLS:
            val = str(row[col])
            # Skip empty cells and the placeholder value used for missing data.
            if val and val != "none" and any(c.islower() for c in val):
                bad.append(col)
        return ", ".join(bad) if bad else "ok"

    df["check_uppercase"] = df.apply(_uppercase, axis=1)

    # ------------------------------------------------------------------
    # Check 5 — No leading, trailing, or consecutive spaces.
    # Extra spaces are invisible in the UI but cause exact-match lookups
    # to fail and create duplicates after whitespace normalisation.
    # ------------------------------------------------------------------
    def _spaces(row):
        bad = []
        for col in TEXT_COLS:
            if re.search(r"^\s+|\s+$|\s{2,}", str(row[col])):
                bad.append(col)
        return ", ".join(bad) if bad else "ok"

    df["check_spaces"] = df.apply(_spaces, axis=1)

    # ------------------------------------------------------------------
    # Check 6 — Field length must not exceed ERP import limits.
    # Reports column name and actual length so the user knows how much
    # to trim (e.g. "description_en (43)" means 3 characters over).
    # ------------------------------------------------------------------
    def _length(row):
        bad = []
        for col in DESC_COLS:
            length = len(str(row[col]).strip())
            if length > DESC_LIMIT:
                bad.append(f"{col} ({length})")
        code_len = len(str(row["product_code"]).strip())
        if code_len > CODE_LIMIT:
            bad.append(f"product_code ({code_len})")
        return ", ".join(bad) if bad else "ok"

    df["check_length"] = df.apply(_length, axis=1)

    # ------------------------------------------------------------------
    # Check 7 — Basic name must appear verbatim in the English description.
    # The description is structured as "<BASIC NAME> <SPECIFICATION> [extras]",
    # so an absent basic name signals that the description was built incorrectly
    # or that the basic_name field was filled in after the description.
    # ------------------------------------------------------------------
    df["check_name_in_desc"] = df.apply(
        lambda r: str(r["basic_name"]) in str(r["description_en"]), axis=1
    )

    # ------------------------------------------------------------------
    # Check 8 — Specification (model/type designator) must appear verbatim
    # in every non-empty description column.
    # All language variants should describe the same physical item, so the
    # technical designator (e.g. "6204 2RS", "M12X50 A4") must be identical
    # across languages — it is never translated.
    # ------------------------------------------------------------------
    def _spec_in_desc(row):
        spec = str(row["specification"])
        if not spec or spec == "none":
            return "specification empty"
        missing = [
            col for col in DESC_COLS
            if str(row[col]) and str(row[col]) != "none" and spec not in str(row[col])
        ]
        return ", ".join(missing) if missing else "ok"

    df["check_spec_in_desc"] = df.apply(_spec_in_desc, axis=1)

    return df


# Ordered list used to iterate over all check columns consistently.
CHECK_COLS = [
    "check_product_group",
    "check_basic_name",
    "check_symbols",
    "check_uppercase",
    "check_spaces",
    "check_length",
    "check_name_in_desc",
    "check_spec_in_desc",
]

# Human-readable labels shown in the UI summary table and column headers.
CHECK_LABELS = {
    "check_product_group": "Product group valid",
    "check_basic_name":    "Basic name valid",
    "check_symbols":       "No forbidden symbols",
    "check_uppercase":     "Uppercase",
    "check_spaces":        "No extra spaces",
    "check_length":        "Field length",
    "check_name_in_desc":  "Basic name in description",
    "check_spec_in_desc":  "Specification in all descriptions",
}


def is_pass(col: str, value) -> bool:
    """
    Normalise a check result to a single boolean.

    The three membership checks (product_group, basic_name, name_in_desc)
    return Python booleans directly from pandas .isin() / lambda comparisons.
    The remaining row-apply checks return the string "ok" on success and a
    diagnostic string on failure, so we test for that sentinel value.
    """
    if col in ("check_product_group", "check_basic_name", "check_name_in_desc"):
        return bool(value)
    return str(value).strip().lower() == "ok"


def summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return a per-check summary with pass count, fail count, and pass rate."""
    rows = []
    total = len(df)
    for col, label in CHECK_LABELS.items():
        passes = sum(is_pass(col, v) for v in df[col])
        rows.append({
            "Check":     label,
            "Pass":      passes,
            "Fail":      total - passes,
            "Pass rate": f"{passes / total:.0%}",
        })
    return pd.DataFrame(rows)


def bad_data_cells(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a boolean DataFrame (same index, data columns only) where True
    means the cell is implicated in at least one failed check.

    Used to highlight the actual problematic data cells — not just the check
    result columns — so the user can see at a glance which value to fix.

    Boolean checks map to a single column (product_group, basic_name,
    description_en). String checks already embed the failing column names in
    their result text, so we parse those out with a regex.
    """
    data_cols = [c for c in df.columns if not c.startswith("check_")]
    bad = pd.DataFrame(False, index=df.index, columns=data_cols)

    # Direct column mapping for the three boolean checks
    BOOL_CHECKS = {
        "check_product_group": "product_group",
        "check_basic_name":    "basic_name",
        "check_name_in_desc":  "description_en",
    }
    for check_col, data_col in BOOL_CHECKS.items():
        if check_col in df.columns and data_col in bad.columns:
            bad.loc[~df[check_col].astype(bool), data_col] = True

    # String checks encode the failing column names in the result text.
    # Parse them out so we can highlight the correct data cells.
    col_re = re.compile(
        r"\b(product_group|basic_name|specification|"
        r"description_en|description_fi|description_de|product_code)\b"
    )
    string_checks = [
        "check_symbols", "check_uppercase", "check_spaces",
        "check_length", "check_spec_in_desc",
    ]
    for check_col in string_checks:
        if check_col not in df.columns:
            continue
        for idx, val in df[check_col].items():
            s = str(val).strip().lower()
            # "ok" and "specification empty" are not errors
            if s in ("ok", "specification empty", ""):
                continue
            for col in col_re.findall(str(val)):
                if col in bad.columns:
                    bad.at[idx, col] = True

    return bad


def auto_fix(items: pd.DataFrame) -> tuple:
    """
    Apply deterministic, risk-free corrections to the raw item data.

    Two fix types:
      - Uppercase: description and basic_name fields converted to uppercase.
        Safe because ERP systems require uppercase and the content is not lost.
      - Spaces: leading/trailing and consecutive spaces removed.
        Safe because spaces carry no meaning in these fields.

    Returns
    -------
    fixed_df : pd.DataFrame
        Corrected item data (same columns as input, no check columns).
    changes_df : pd.DataFrame
        Log of every change: item_id, column, before, after.
    """
    fixed = items.copy()
    changes = []

    id_col = "item_id" if "item_id" in fixed.columns else fixed.columns[0]

    # Fix 1 — uppercase on description and basic_name columns
    for col in UPPERCASE_COLS:
        if col not in fixed.columns:
            continue
        for idx, val in fixed[col].items():
            s = str(val)
            if s in ("", "nan", "none"):
                continue
            corrected = s.upper()
            if corrected != s:
                changes.append({
                    "item_id": fixed.at[idx, id_col],
                    "column":  col,
                    "before":  s,
                    "after":   corrected,
                    "fix_type": "uppercase",
                })
                fixed.at[idx, col] = corrected

    # Fix 2 — strip leading/trailing spaces and collapse consecutive spaces
    for col in TEXT_COLS:
        if col not in fixed.columns:
            continue
        for idx, val in fixed[col].items():
            s = str(val)
            corrected = re.sub(r"\s{2,}", " ", s).strip()
            if corrected != s:
                changes.append({
                    "item_id": fixed.at[idx, id_col],
                    "column":  col,
                    "before":  s,
                    "after":   corrected,
                    "fix_type": "spaces",
                })
                fixed.at[idx, col] = corrected

    return fixed, pd.DataFrame(changes)


def manual_fix_rows(results: pd.DataFrame) -> pd.DataFrame:
    """
    Return one row per ✏️ error that requires manual correction:
    forbidden symbols, field-length violations, basic name missing
    from description, and specification missing from description columns.

    'after' is empty — the user types in the corrected value.
    Only rows where a check actually failed are included.
    """
    id_col = "item_id" if "item_id" in results.columns else results.columns[0]
    col_re = re.compile(
        r"\b(basic_name|specification|"
        r"description_en|description_fi|description_de|product_code)\b"
    )
    rows = []

    for idx in results.index:
        item_id = results.at[idx, id_col]

        def _val(col):
            return str(results.at[idx, col]) if col in results.columns else ""

        # Forbidden symbols: result format is "col: sym1, sym2; col: sym"
        sym = _val("check_symbols")
        if sym.lower() not in ("ok", ""):
            for segment in sym.split(";"):
                m = col_re.match(segment.strip())
                if m:
                    col = m.group(1)
                    rows.append({
                        "item_id": item_id, "column": col,
                        "before": _val(col), "after": "",
                        "fix_type": "manual",
                        "error_description": "Forbidden symbol",
                    })

        # Field length: result format is "col (N), col (N)"
        length = _val("check_length")
        if length.lower() not in ("ok", ""):
            for part in length.split(","):
                part = part.strip()
                m = col_re.match(part)
                if m:
                    col = m.group(1)
                    length_match = re.search(r"\((\d+)\)", part)
                    n = length_match.group(1) if length_match else "?"
                    limit = CODE_LIMIT if col == "product_code" else DESC_LIMIT
                    rows.append({
                        "item_id": item_id, "column": col,
                        "before": _val(col), "after": "",
                        "fix_type": "manual",
                        "error_description": f"Too long: {n} chars (max {limit})",
                    })

        # Basic name missing from description_en (boolean check)
        name_in = results.at[idx, "check_name_in_desc"] if "check_name_in_desc" in results.columns else True
        if not bool(name_in):
            rows.append({
                "item_id": item_id, "column": "description_en",
                "before": _val("description_en"), "after": "",
                "fix_type": "manual",
                "error_description": "Basic name missing from description",
            })

        # Specification missing: result is comma-separated column names
        spec = _val("check_spec_in_desc")
        if spec.lower() not in ("ok", "specification empty", ""):
            for col in col_re.findall(spec):
                if col.startswith("description_"):
                    rows.append({
                        "item_id": item_id, "column": col,
                        "before": _val(col), "after": "",
                        "fix_type": "manual",
                        "error_description": "Specification missing from description",
                    })

    cols = ["item_id", "column", "before", "after", "fix_type", "error_description"]
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def suggest_fixes(items: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """
    Generate correction suggestions for errors that cannot be auto-fixed.

    Currently covers two checks:
      - basic_name: invalid value → closest approved name from reference
      - product_group: invalid code → closest match via item description

    Uses difflib.get_close_matches (edit-distance based) so no external
    dependencies are needed.

    Returns a DataFrame with the same columns as auto_fix() changes_df so
    both can be displayed in the same table:
      item_id, column, before, after, fix_type
    Only rows where a plausible suggestion was found are included.
    """
    from difflib import get_close_matches

    id_col       = "item_id" if "item_id" in items.columns else items.columns[0]
    valid_groups = set(ref["product_group_id"].astype(str))
    valid_names  = ref["basic_name"].dropna().unique().tolist()

    suggestions = []

    for idx, row in items.iterrows():
        item_id = row[id_col]

        # Suggestion for basic_name — find closest approved name
        bn = str(row.get("basic_name", ""))
        if bn and bn not in valid_names:
            matches = get_close_matches(bn.upper(),
                                        [n.upper() for n in valid_names],
                                        n=1, cutoff=0.4)
            if matches:
                # Recover original casing from valid_names list
                suggested = next(n for n in valid_names if n.upper() == matches[0])
                suggestions.append({
                    "item_id":  item_id,
                    "column":   "basic_name",
                    "before":   bn,
                    "after":    suggested,
                    "fix_type": "suggestion",
                })

        # Suggestion for product_group — match item description against
        # reference category descriptions to find the most likely group
        pg = str(row.get("product_group", ""))
        if pg not in valid_groups:
            desc = str(row.get("description_en", "")).upper()
            if desc:
                ref_labels = ref["description_en"].dropna().tolist()
                matches = get_close_matches(desc, ref_labels, n=1, cutoff=0.3)
                if matches:
                    suggested_code = ref.loc[
                        ref["description_en"] == matches[0], "product_group_id"
                    ].iloc[0]
                    suggestions.append({
                        "item_id":  item_id,
                        "column":   "product_group",
                        "before":   pg,
                        "after":    str(suggested_code),
                        "fix_type": "suggestion",
                    })

    return pd.DataFrame(suggestions)
