# PIM/MDM Portfolio

Practical Python tools for Product Information Management (PIM) 
and Master Data Management (MDM) challenges — built by someone 
who has worked with the data, not just the algorithms.

## About

I'm Ekaterina Ruotsalainen, a data and systems specialist with 
background in ERP/PDM environments and industrial product data 
management. These projects are based on real problems I have 
encountered working with item master data in industrial contexts: 
duplicate records that exact-match search misses, validation rules 
that need to handle messy real-world input, and classification tasks 
where the request is vague but the answer needs to be precise.

The goal is not to demonstrate textbook implementations, but to show 
how domain understanding shapes technical decisions — like knowing 
that DIN 931 and DIN 933 are different products even when their 
dimensions are identical.

[LinkedIn](https://linkedin.com/in/eruotsalainen) · 
[GitHub](https://github.com/ekaterina-25)

## Projects

### [Duplicate Detection](duplicate_detection/)

Finding duplicate records in industrial spare parts catalogs using TF-IDF text
similarity and within-group verification.

- Handles abbreviations, word-order variations, and inconsistent formatting
- Optional discriminator column prevents confusing similar-but-different items
  (e.g. DIN 931 partial-thread vs DIN 933 full-thread screws)
- Two modes: within a single file, or across two files from different source systems
- Configurable thresholds and output columns for different datasets

**Try it:** Run with built-in demo datasets (general spare parts or screws with discriminator),
upload your own Excel files, or use the datasets in [`duplicate_detection/data/`](duplicate_detection/data/).

**Tools:** Python, scikit-learn, pandas, Streamlit, openpyxl, Plotly

---

### [Item Data Validation](item_data_validation/)

Validating industrial item master data against standardisation rules, with an
interactive correction workflow.

- 8 checks: reference catalogue membership, forbidden symbols, uppercase convention,
  field length (ERP import limits), and cross-field consistency
- Errors grouped by fix effort: auto-fixable (uppercase/spaces), suggestion (closest
  reference match), or manual (symbols, length, description consistency)
- Editor validates proposed fixes before writing back — invalid values are rejected
  with a specific reason
- Download: four-sheet Excel with colour-coded results and corrected data

**Try it:** Run with built-in demo data (250 synthetic items, 88-row reference catalogue)
or upload your own Excel files.

**Tools:** Python, pandas, Streamlit, openpyxl

---

*More sections coming: Copilot Studio agent examples.*
