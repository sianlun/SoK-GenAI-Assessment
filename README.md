# SoK: Generative AI in Assessment — Engineering, STEM & CS Education

Systematization of Knowledge (SoK) review repository.  
**Target venue:** IEEE TALE 2026 — Assessment Revolution track.

---

## Overview

This repository contains the full dual-pipeline data extraction and analysis workflow for a Systematization of Knowledge review mapping how Generative AI disrupts, challenges, and augments assessments within engineering, STEM, and computing education (2022–2026).

**Final corpus:** 641 papers | **PDF coverage:** 617/641 (96.3%)  
**Search date:** June 2026

---

## Repository Structure

```
SoK-GenAI-Assessment/
│
├── data/
│   ├── raw/               # Original BIB exports from 5 databases
│   │   ├── ieee_combined_278.bib
│   │   ├── acm_1113.bib
│   │   ├── scopus_1001.bib
│   │   ├── wos_305.bib
│   │   └── eric_69.bib
│   ├── processed/
│   │   ├── corpus_final.json        # 641-paper authoritative corpus
│   │   ├── screening_results.json   # 2,162 records + screening decisions
│   │   └── review_decisions.json    # Secondary review of uncertain records
│   └── manifest/
│       ├── download_manual.json     # Papers still pending retrieval (24)
│       ├── pdf_verification.json    # Structural validation of all PDFs
│       └── find_oa_report.json      # OA URL discovery results
│
├── pipeline1_retrieval/   # Phase 1: corpus construction & OA discovery
│   ├── corpus_builder.py            # Parse BIBs, dedup, build corpus
│   ├── screen.py                    # Keyword title/abstract screener
│   ├── enrich_abstracts.py          # Enriches missing abstracts via APIs
│   ├── extract.py                   # BIB field extraction utilities
│   ├── find_oa_all.py               # OA URL discovery: S2, OpenAlex, Unpaywall
│   ├── find_oa_springer.py          # OA discovery targeted at Springer DOIs
│   ├── verify_pdfs.py               # Structural PDF validation
│   └── requirements.txt             # Python dependencies
│
├── pipeline2_analysis/    # Phase 2: bibliometric + content analysis
│   ├── bibliometrics/
│   │   ├── 01_load_and_merge.R      # Load BIBs, dedup, build M object
│   │   └── 02_bibliometric_analysis.R  # Annual trends, venues, keyword networks
│   ├── content_analysis/
│   │   ├── 01_text_extraction.py    # Extract full text from 617 PDFs
│   │   └── 02_thematic_coding.py    # Keyword coding + taxonomy mapping
│   └── outputs/
│       ├── figures/                 # Generated plots (PNG)
│       └── tables/                  # Generated CSV tables
│
├── docs/
│   ├── retrieval_process.docx       # Full PRISMA-aligned retrieval narrative
│   ├── CORPUS.md                    # Human-readable corpus list
│   └── springer_needed.md           # Remaining Springer papers with OA links
│
└── _pdfs/                           # PDF corpus — GITIGNORED (617 files)
```

---

## Search Strategy

Five bibliographic databases searched in June 2026:

| Database | Raw records | After dedup (primary) |
|---|---|---|
| ACM Digital Library | 1,113 | 892 |
| Scopus | 1,001 | 758 |
| Web of Science | 305 | 305 |
| IEEE Xplore | 278 | 138 |
| ERIC | 69 | 69 |
| **Total** | **2,766** | **2,162** |

**Inclusion criteria:** GenAI applied to assessment, feedback, grading, or academic integrity in engineering/STEM/computing higher education, 2022–2026, English, peer-reviewed.

---

## PRISMA Flow

```
2,766 records identified (5 databases)
   − 604 duplicates
= 2,162 unique records screened
   − 1,517 excluded at title/abstract screening
=   645 → secondary review of 59 uncertain records
   − 4 excluded at secondary review
=   641 FINAL CORPUS
```

---

## Dual-Pipeline Extraction

### Pipeline 1 — Corpus Construction & OA Discovery

```bash
# 1. Build corpus from BIB exports
python3 pipeline1_retrieval/corpus_builder.py

# 2. Screen all records (title + abstract)
python3 pipeline1_retrieval/screen.py

# 3. Discover open-access PDF URLs (Semantic Scholar, OpenAlex, Unpaywall)
python3 pipeline1_retrieval/find_oa_all.py --email your@email.com
# → outputs find_oa_report.json with OA URLs for each paper

# 4. Download OA papers using the discovered URLs
#    Use the URLs in find_oa_report.json with your preferred download method.
#    For papers not available via OA, retrieve through your institution's
#    licensed database access.

# 5. Verify downloaded PDFs
python3 pipeline1_retrieval/verify_pdfs.py
```

**PDF retrieval note:** This repository provides the corpus manifest and OA URL discovery tooling. Full-text PDFs were obtained through a combination of open-access repositories and institutional database access. Researchers reproducing this corpus should retrieve paywalled papers through their own institutional subscriptions. The `data/manifest/find_oa_report.json` file lists discovered OA URLs for the majority of the corpus.

### Pipeline 2 — Bibliometric + Content Analysis

```r
# Phase 1: Bibliometrics (R)
source("pipeline2_analysis/bibliometrics/01_load_and_merge.R")
source("pipeline2_analysis/bibliometrics/02_bibliometric_analysis.R")
```

```bash
# Phase 2: Full-text content analysis (Python)
# Requires PDF corpus in _pdfs/
pip install pymupdf tqdm
python3 pipeline2_analysis/content_analysis/01_text_extraction.py
python3 pipeline2_analysis/content_analysis/02_thematic_coding.py
```

---

## PDF Corpus

The `_pdfs/` directory is **not tracked by git** (size ~3 GB). It is fully described by:
- `data/manifest/pdf_verification.json` — validation status of all 641 expected files
- `data/manifest/download_manual.json` — 24 papers not yet retrieved
- `data/processed/corpus_final.json` — canonical filename for each of the 641 papers

To reproduce the corpus: run Pipeline 1 to identify OA versions via `find_oa_all.py`, download OA papers directly, and retrieve remaining paywalled papers through your institution's database subscriptions. The `data/manifest/pdf_verification.json` documents the validation status of every expected file.

---

## Citation

> Lerk, S. (2026). *Generative AI in Assessment within Engineering, STEM, and Computing Education: A Systematization of Knowledge*. Proceedings of IEEE TALE 2026.

**Repository:** https://github.com/sianlun/SoK-GenAI-Assessment

---

## Dependencies

**Python 3.10+:** see `pipeline1_retrieval/requirements.txt`  
**R 4.3+:** `bibliometrix`, `tidyverse`, `here`
```r
install.packages(c("bibliometrix", "tidyverse", "here"))
```
