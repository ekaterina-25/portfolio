# PIM/MDM Portfolio

A collection of practical Python examples for Product Information Management (PIM)
and Master Data Management (MDM) challenges, built using public and synthetic datasets.

## Projects

### [Duplicate Detection](duplicate_detection/)

Finding duplicate records in industrial spare parts catalogs using TF-IDF text
similarity and within-group verification.

- Handles abbreviations, word-order variations, and inconsistent formatting
- Optional discriminator column prevents confusing similar-but-different items
  (e.g. DIN 931 partial-thread vs DIN 933 full-thread screws)
- Configurable thresholds and output columns for different datasets

**Tools:** Python, scikit-learn, pandas, openpyxl

---

*More sections coming: data validation, Copilot Studio agent examples.*
