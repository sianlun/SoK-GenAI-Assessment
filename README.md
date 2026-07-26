# SoK: Generative AI in Assessment — Engineering, STEM & Computing Education

Systematization of Knowledge (SoK) review repository.

> Lau, S. L. (2026). *Evidence Quality in Generative AI Assessment Research: A Systematization of Knowledge for Engineering, STEM, and Computing Education.*. <!-- Citation will be updated upon acceptance. -->

This repository contains the **input data and analysis code** to reproduce the taxonomy coding and consensus findings reported in the paper. PDF retrieval is not included; obtain papers via your institutional subscriptions using the DOIs in `data/processed/corpus_final.json`.

---

## Repository Structure

```
SoK-GenAI-Assessment/
│
├── data/
│   ├── raw/                            ← Original BibTeX exports (5 databases)
│   │   ├── scopus_1001.bib
│   │   ├── wos_305.bib
│   │   ├── ieee_combined_278.bib
│   │   ├── acm_1113.bib
│   │   └── eric_69.bib
│   └── processed/
│       └── corpus_final.json           ← 641-paper authoritative corpus
│
├── analysis/
│   └── content_analysis/
│       ├── 01_text_extraction.py       ← Round 1: extract full text (PyMuPDF, all pages)
│       ├── 01b_text_extraction_alt.py  ← Round 2: extract full text (pypdf, all pages)
│       ├── 02_thematic_coding.py       ← Round 1: taxonomy coding (Vocabulary A)
│       ├── 02b_thematic_coding_alt.py  ← Round 2: taxonomy coding (Vocabulary B)
│       └── 03_consensus.py             ← Compute cross-vocabulary consensus counts
│
└── analysis/outputs/
    └── tables/                         ← Generated CSVs/TXTs (populated after running)
        ├── extraction_report.csv
        ├── extraction_report_alt.csv
        ├── thematic_coding.csv
        ├── thematic_coding_alt.csv
        ├── taxonomy_summary.csv
        ├── taxonomy_summary_alt.csv
        ├── taxonomy_consensus.csv
        ├── taxonomy_disagreements.csv
        └── consensus_summary.txt
```

**Not included:** `_pdfs/` (~3 GB, 617 files) — retrieve using DOIs in `corpus_final.json`. The full-text extract dumps (`fulltext_extracts*.jsonl`, ~34 MB each) are also gitignored; regenerate by running the `01*.py` extraction scripts.

---

## PRISMA Flow

```
2,766 records identified (5 databases)
   − 604 duplicates
= 2,162 unique records screened
   − 1,517 excluded at title/abstract screening
=   645 → secondary review
   − 4 excluded
=   641 FINAL CORPUS   (617 PDFs retrieved, 96.3%)
    614 completing both extraction rounds → consensus analysis
```

---

## Dual-Round Taxonomy Coding

Two fully independent coding processes run on the same corpus. Only papers assigned by **both** rounds are counted in the paper (consensus rule), providing a conservative cross-vocabulary lower bound.

| | Round 1 | Round 2 |
|---|---|---|
| PDF library | PyMuPDF (`fitz`) | `pypdf` |
| Pages read | All | All |
| Vocabulary | Set A — primary terms | Set B — independently devised synonyms/paraphrases |
| Match rule | Any 1 keyword | Any 1 keyword (same threshold — vocabulary is the sole variable) |
| Default | Category G | None (unmatched = uncoded) |

### Vocabulary Design Rules

Both vocabularies follow the same construction rules:
1. All terms are 2+ word phrases — no single generic words
2. All terms are category-specific
3. No term appears in the other vocabulary
4. Comparable breadth (~17 terms per category)

---

## Reproducing the Analysis

### Prerequisites

```bash
pip install pymupdf pypdf pandas tqdm
```

Place the 617 PDFs in `_pdfs/` (filenames match the `filename` field in `corpus_final.json`).

### Run order

```bash
# Round 1 — extract text, then code
python3 analysis/content_analysis/01_text_extraction.py
python3 analysis/content_analysis/02_thematic_coding.py

# Round 2 — extract text (alt library), then code (alt vocabulary)
python3 analysis/content_analysis/01b_text_extraction_alt.py
python3 analysis/content_analysis/02b_thematic_coding_alt.py

# Consensus — compare rounds, compute reported counts
python3 analysis/content_analysis/03_consensus.py
# → analysis/outputs/tables/consensus_summary.txt
# → analysis/outputs/tables/taxonomy_consensus.csv
# → analysis/outputs/tables/taxonomy_disagreements.csv
```

---

## Six-Category Taxonomy (A–F)

| Cat. | Theme | Consensus ($N=614$) | Evidence Quality |
|---|---|---|---|
| A | Automated Grading | 50 (8.1%) | Moderate — small-*n* empirical; limited validity |
| B | Authentic Assessment Redesign | 24 (3.9%) | Low — conceptual/framework; no controlled evaluations |
| C | Academic Integrity | 105 (17.1%) | Moderate — detection studies; policy surveys |
| D | Formative and Adaptive Assessment | 254 (41.4%) | Moderate–High — controlled studies; ITS/CS1 context |
| E | Ethics and Policy | 230 (37.5%) | Low — framework/opinion dominant; no policy effectiveness data |
| F | Perception and Affect | 43 (7.0%) | Moderate — survey-heavy; cross-sectional; no longitudinal data |

Category G (Review/Methodology) is a metadata dimension used by Round 1 as a default; it is not reported as a substantive finding.

All counts are **consensus-only** (both rounds independently assign the paper to the category).

---

## Key Finding

The two most confirmed thematic strands — Formative and Adaptive Assessment (D, 41.4%) and Ethics and Policy (E, 37.5%) — sit at opposite extremes of the evidence quality spectrum. This **diagnosis-to-intervention gap** is the field's most consequential structural challenge: high-volume ethics and policy discourse rests on sparse empirical foundations, while the most rigorously evaluated category (formative and adaptive assessment) has not yet demonstrated generalisability beyond introductory programming contexts.

---

## Citation

> **Note:** Citation will be updated upon acceptance and publication.

```bibtex
@inproceedings{lau2026sok,
  author    = {Lau, Sian Lun},
  title     = {Evidence Quality in Generative {AI} Assessment Research:
               A Systematization of Knowledge for Engineering, {STEM},
               and Computing Education},
  booktitle = {To be updated},
  year      = {2026},
  note      = {Under review},
}
```
