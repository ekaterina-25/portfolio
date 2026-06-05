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
or upload your own Excel files.

**Run locally:**
```
streamlit run duplicate_detection/app.py
```

**Tools:** Python, scikit-learn, pandas, Streamlit, openpyxl, Plotly

---

### [Item Data Validation](item_data_validation/)

Automated validation of item master data against standardisation rules — based on
real quality gates used in ERP data harmonisation projects.

Each item is checked across four categories:

- **Reference catalogue** — product group codes and basic names must match approved values
- **Field content** — forbidden symbols (encoding issues, delimiter conflicts),
  uppercase convention, no extra spaces
- **Field length** — ERP import limits (descriptions max 40 characters, part numbers max 30)
- **Cross-field consistency** — specification and basic name must appear verbatim
  in all language description columns

Results are shown in a colour-coded table (data cells and check columns both highlighted),
with a per-check summary and a downloadable Excel report.

**Try it:** Run with built-in demo data (250 synthetic items across 20 product categories
and 88 reference codes), or upload your own files — item data and a reference catalogue.
The demo data includes deliberate errors across all check types so every validation
rule is demonstrated.

**Run locally:**
```
streamlit run item_data_validation/app.py
```

**Tools:** Python, pandas, Streamlit, openpyxl

---

*More sections coming: Copilot Studio agent examples.*
