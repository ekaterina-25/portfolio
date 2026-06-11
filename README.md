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

**Try it:** [Open the Streamlit app](https://ekaterina-25-portfolio-duplicate-detectionapp-gubecm.streamlit.app) — run instantly with built-in demo datasets (general spare parts or screws with discriminator),
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

**Try it:** [Open the Streamlit app](https://ekaterina-25-item-validation.streamlit.app) — run instantly with built-in demo data
(250 synthetic items, 88-row reference catalogue) or upload your own Excel files.

**Tools:** Python, pandas, Streamlit, openpyxl

---

### [Copilot Studio Agents](Copilot_agents/)

Two agents built in Microsoft Copilot Studio for industrial item data management tasks.

#### [Product Classifier](Copilot_agents/product_classifier/)

Classifying vague item creation tickets into the correct internal product group,
with harmonized description and specification as output.

- Web-first: runs Bing search before deciding — no guessing from token similarity alone
- Identifies product type from manufacturer pages, datasheets, and distributors
- Maps to internal product group from a reference catalogue; never invents group codes
- Returns harmonized English/Finnish descriptions and specification in company format
- Confidence score and evidence links included; raises a clarifying question if uncertain

**Try it:** [Open the Streamlit simulation](https://ekaterina-25-item-classifier.streamlit.app) — five pre-built examples replay real agent
responses instantly, or enter any part number for a live web search classification.

**Tools:** Microsoft Copilot Studio, Bing Search · Simulation: Streamlit, Tavily, Claude Haiku

#### [Fastener Normalizer](Copilot_agents/item_data_normalizer/)

Harmonizing legacy fastener item data in Excel against internal naming rules,
with harmonized output written back to Excel automatically.

- Reads item rows from Excel using the Excel Online connector
- Resolves mixed ISO/DIN standards: ISO preferred when both are present
- Normalizes text casing, size formats (`M8x80` → `M8×80`), and specification field order
- Preserves coating and material tokens (`Zn`, `A4-70`, `8.8`)
- Writes harmonized output back to Excel via Power Automate and Office Scripts
- Built for fasteners; naming rules can be extended to other product groups

**Try it:** [Open the Streamlit simulation](https://ekaterina-25-item-data-normalizer.streamlit.app) — select rows from the input table and
see a side-by-side before/after comparison of the harmonization.

**Tools:** Microsoft Copilot Studio, Power Automate, Office Scripts, Excel Online · Simulation: Streamlit
