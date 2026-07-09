#!/usr/bin/env python3
"""
Pipeline 2 – Phase 2: Content Analysis
Script 01: Extract full text from all PDFs in _pdfs/

Outputs:
  pipeline2_analysis/outputs/tables/fulltext_extracts.jsonl
    — one JSON line per paper: {filename, doi, title, year, text, pages, word_count}
  pipeline2_analysis/outputs/tables/extraction_report.csv

Requirements:
  pip install pymupdf tqdm
"""

import json
import csv
import re
from pathlib import Path

import fitz          # PyMuPDF — pip install pymupdf
from tqdm import tqdm

ROOT   = Path(__file__).parent.parent.parent
PDFS   = ROOT / "_pdfs"
CORPUS = ROOT / "data" / "processed" / "corpus_final.json"
OUT    = ROOT / "pipeline2_analysis" / "outputs" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

EXTRACT_FILE = OUT / "fulltext_extracts.jsonl"
REPORT_FILE  = OUT / "extraction_report.csv"


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)   # rejoin hyphenated line-breaks
    return text.strip()


def extract_pdf(path: Path) -> tuple[str, int]:
    doc   = fitz.open(path)
    pages = len(doc)
    text  = " ".join(page.get_text("text") for page in doc)
    doc.close()
    return clean_text(text), pages


def main():
    corpus = json.loads(CORPUS.read_text())
    ok, fail, missing = 0, 0, 0
    report_rows = []

    with open(EXTRACT_FILE, "w", encoding="utf-8") as jl:
        for paper in tqdm(corpus, desc="Extracting PDFs"):
            fn    = paper.get("filename", "")
            doi   = paper.get("doi", "")
            title = paper.get("title", "")
            year  = paper.get("year", "")
            path  = PDFS / fn

            if not path.exists() or path.stat().st_size < 10_000:
                missing += 1
                report_rows.append({"filename": fn, "status": "missing", "pages": 0, "words": 0})
                continue

            try:
                text, pages = extract_pdf(path)
                words = len(text.split())
                jl.write(json.dumps({
                    "filename": fn, "doi": doi, "title": title, "year": year,
                    "pages": pages, "word_count": words, "text": text
                }, ensure_ascii=False) + "\n")
                report_rows.append({"filename": fn, "status": "ok", "pages": pages, "words": words})
                ok += 1
            except Exception as e:
                report_rows.append({"filename": fn, "status": f"error: {e}", "pages": 0, "words": 0})
                fail += 1

    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "status", "pages", "words"])
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"\nExtraction complete: {ok} extracted, {fail} failed, {missing} missing")
    print(f"  → {EXTRACT_FILE} ({ok} records)")
    print(f"  → {REPORT_FILE}")


if __name__ == "__main__":
    main()
