#!/usr/bin/env python3
"""
Pipeline 2 – Round 2: Alternative Text Extraction
Script 01b: Extract full text from PDFs using pypdf (all pages).

Round 2 counterpart to 01_text_extraction.py.
Design differences from Round 1:
  - Library     : pypdf  (Round 1 uses PyMuPDF/fitz)
  - Page window : ALL pages — same coverage as Round 1
  - Output      : fulltext_extracts_alt.jsonl

Using the same page window as Round 1 is deliberate: it eliminates coverage
depth as a confounding variable, so any Round 1 / Round 2 disagreement can be
cleanly attributed to either the text-extraction library or the vocabulary —
both of which are independently motivated sources of variation.

PyMuPDF and pypdf produce genuinely different text from the same PDF because
they handle two-column layouts, font encoding, ligatures, and OCR layers
differently. That library-level difference, combined with the independent
synonym vocabulary and stricter matching threshold in 02b_thematic_coding_alt.py,
provides sufficient methodological independence between the two rounds.

Run 02b_thematic_coding_alt.py after this, then 03_consensus.py.

Requirements:
  pip install pypdf tqdm
"""

import json
import csv
import re
from pathlib import Path

import pypdf
from tqdm import tqdm

ROOT   = Path(__file__).resolve().parent.parent.parent
PDFS   = ROOT / "_pdfs"
CORPUS = ROOT / "data" / "processed" / "corpus_final.json"
OUT    = ROOT / "analysis" / "outputs" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

EXTRACT_FILE = OUT / "fulltext_extracts_alt.jsonl"
REPORT_FILE  = OUT / "extraction_report_alt.csv"

def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)   # rejoin hyphenated line-breaks
    return text.strip()


def extract_pdf(path: Path) -> tuple[str, int]:
    """Extract all pages — same coverage as Round 1 (PyMuPDF, all pages)."""
    reader = pypdf.PdfReader(str(path))
    total_pages = len(reader.pages)
    text = " ".join(
        page.extract_text() or ""
        for page in reader.pages          # all pages, no limit
    )
    return clean_text(text), total_pages


def main():
    corpus = json.loads(CORPUS.read_text())
    ok, fail, missing = 0, 0, 0
    report_rows = []

    with open(EXTRACT_FILE, "w", encoding="utf-8") as jl:
        for paper in tqdm(corpus, desc="Round 2 extraction (pypdf, all pages)"):
            fn    = paper.get("filename", "")
            doi   = paper.get("doi", "")
            title = paper.get("title", "")
            year  = paper.get("year", "")
            path  = PDFS / fn

            if not path.exists() or path.stat().st_size < 10_000:
                missing += 1
                report_rows.append({"filename": fn, "status": "missing",
                                    "pages": 0, "words": 0})
                continue

            try:
                text, pages = extract_pdf(path)
                words = len(text.split())
                jl.write(json.dumps({
                    "filename": fn, "doi": doi, "title": title, "year": year,
                    "pages": pages, "word_count": words, "text": text,
                }, ensure_ascii=False) + "\n")
                report_rows.append({"filename": fn, "status": "ok",
                                    "pages": pages, "words": words})
                ok += 1
            except Exception as e:
                report_rows.append({"filename": fn, "status": f"error: {e}",
                                    "pages": 0, "words": 0})
                fail += 1

    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "status", "pages", "words"])
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"\nRound 2 extraction complete (pypdf, all pages): {ok} ok, {fail} failed, {missing} missing")
    print(f"  → {EXTRACT_FILE}")
    print(f"  → {REPORT_FILE}")


if __name__ == "__main__":
    main()
