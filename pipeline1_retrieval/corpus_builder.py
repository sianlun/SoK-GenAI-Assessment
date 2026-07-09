#!/usr/bin/env python3
"""
corpus_builder.py — Build the final corpus manifest after manual screening review
═══════════════════════════════════════════════════════════════════════════════════

WHAT THIS SCRIPT DOES
─────────────────────
This is Step 2 of the SoK pipeline. After screen.py runs and you have manually
reviewed the UNCERTAIN records (and spot-checked the INCLUDE set), this script:

  1. Reads corpus_pending.json (the INCLUDE + UNCERTAIN records from screen.py)
  2. Filters to records where manual_decision == "INCLUDE" (or decision == "INCLUDE"
     and manual_decision is blank, meaning you accepted the AI recommendation)
  3. Generates a URL-safe filename slug for each paper (year_first_5_words_of_title)
  4. Writes corpus_final.json — the definitive paper manifest used by all
     downstream scripts (download_oa.py, extract.py, extract_alt.py)
  5. Writes CORPUS.md — a human-readable bibliography of the final corpus

HOW TO USE IT
─────────────
  Step A — After screen.py finishes, open corpus_pending.json in a text editor
            OR open screening_results.xlsx and filter to UNCERTAIN rows.
            For each UNCERTAIN record, fill in the "manual_decision" field:
              "INCLUDE"  — keep it
              "EXCLUDE"  — remove it (add a note in manual_note)
            Also spot-check INCLUDE records — set manual_decision = "EXCLUDE"
            for any false positives you find.

  Step B — Run this script:
              python3 corpus_builder.py

  Step C — Proceed to download_oa.py to fetch open-access PDFs.

corpus_final.json FORMAT
─────────────────────────
  [
    {
      "filename": "2024_gpt4_automated_grading_cs_education.pdf",
      "title":    "GPT-4 as Automated Grader ...",
      "authors":  "Smith, J and Lee, K",
      "year":     "2024",
      "doi":      "10.1109/...",
      "source":   "IEEE Frontiers in Education",
      "db_source":"IEEE",
      "abstract": "...",
      "record_id":"42"
    },
    ...
  ]

USAGE
─────
  python3 corpus_builder.py
  python3 corpus_builder.py --pending path/to/corpus_pending.json
  python3 corpus_builder.py --accept-uncertain   # auto-accept all UNCERTAIN as INCLUDE
═══════════════════════════════════════════════════════════════════════════════════
"""

import argparse
import json
import re
import unicodedata
from pathlib import Path
from datetime import date

HERE         = Path(__file__).parent
PENDING_JSON = HERE / "corpus_pending.json"
CORPUS_JSON  = HERE / "corpus_final.json"
CORPUS_MD    = HERE / "CORPUS.md"


def slugify(text: str, max_words: int = 7) -> str:
    """Convert a title to a URL-safe filename component."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = [w for w in text.split() if w not in
             {"a","an","the","of","in","on","at","for","to","and","or","with",
              "using","via","based","this","that","from","into","by","as","is",
              "are","be","its","it","we","our","their","towards","toward"}]
    return "_".join(words[:max_words])


def build_filename(year: str, title: str) -> str:
    """Build a canonical PDF filename: YEAR_slug.pdf"""
    yr = str(year).strip()[:4] if year else "0000"
    slug = slugify(title)
    return f"{yr}_{slug}.pdf"


def main():
    parser = argparse.ArgumentParser(description="Build final corpus manifest from screened records")
    parser.add_argument("--pending",          default=str(PENDING_JSON), help="Path to corpus_pending.json")
    parser.add_argument("--accept-uncertain", action="store_true",
                        help="Auto-accept UNCERTAIN records (no manual_decision set) as INCLUDE")
    args = parser.parse_args()

    print(f"\n{'═'*70}")
    print("  SoK Corpus Builder — corpus_builder.py")
    print(f"{'═'*70}\n")

    # ── load pending records ──────────────────────────────────────────────────
    with open(args.pending, encoding="utf-8") as f:
        pending = json.load(f)

    print(f"  Loaded {len(pending)} records from {args.pending}")

    # ── filter to final included set ──────────────────────────────────────────
    corpus = []
    n_skipped = 0

    for rec in pending:
        auto_decision   = rec.get("decision", "")
        manual_decision = str(rec.get("manual_decision", "")).strip().upper()

        # Determine effective decision
        if manual_decision == "INCLUDE":
            effective = "INCLUDE"
        elif manual_decision == "EXCLUDE":
            effective = "EXCLUDE"
        elif manual_decision == "":
            # No manual override
            if auto_decision == "INCLUDE":
                effective = "INCLUDE"       # accept AI recommendation
            elif auto_decision == "UNCERTAIN":
                if args.accept_uncertain:
                    effective = "INCLUDE"   # user opted to accept all uncertain
                else:
                    effective = "EXCLUDE"   # default: exclude if not manually reviewed
                    n_skipped += 1
            else:
                effective = "EXCLUDE"
        else:
            effective = "EXCLUDE"

        if effective == "INCLUDE":
            year     = str(rec.get("year", "")).strip()
            title    = str(rec.get("title", "")).strip()
            doi      = str(rec.get("doi", "")).strip()
            filename = build_filename(year, title)

            corpus.append({
                "filename":  filename,
                "title":     title,
                "authors":   str(rec.get("authors", "")).strip(),
                "year":      year,
                "doi":       doi,
                "source":    str(rec.get("source", "")).strip(),
                "db_source": str(rec.get("db_source", "")).strip(),
                "abstract":  str(rec.get("abstract", "")).strip(),
                "record_id": str(rec.get("record_id", "")).strip(),
                "screen_decision": auto_decision,
                "screen_confidence": rec.get("confidence", ""),
                "screen_code": rec.get("code", ""),
            })

    # ── deduplicate by DOI and filename ──────────────────────────────────────
    seen_dois = set()
    seen_files = set()
    deduped = []
    for rec in corpus:
        doi = rec.get("doi", "")
        fn  = rec.get("filename", "")
        if doi and doi in seen_dois:
            continue
        if fn in seen_files:
            # Make filename unique by appending record_id
            fn = fn.replace(".pdf", f"_{rec['record_id']}.pdf")
            rec["filename"] = fn
        if doi:
            seen_dois.add(doi)
        seen_files.add(fn)
        deduped.append(rec)

    corpus = deduped

    # ── write corpus_final.json ───────────────────────────────────────────────
    with open(CORPUS_JSON, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {CORPUS_JSON}  ({len(corpus)} papers)")

    if n_skipped:
        print(f"  NOTE: {n_skipped} UNCERTAIN records were excluded because they had no manual_decision.")
        print(f"        Re-run with --accept-uncertain to include them, or edit corpus_pending.json.")

    # ── write CORPUS.md ───────────────────────────────────────────────────────
    by_year: dict[str, list] = {}
    for rec in sorted(corpus, key=lambda r: (r.get("year",""), r.get("title",""))):
        yr = rec.get("year", "n.d.")
        by_year.setdefault(yr, []).append(rec)

    lines = [
        f"# Final SoK Corpus — {len(corpus)} papers",
        f"",
        f"Generated: {date.today().isoformat()}  |  Script: corpus_builder.py",
        f"",
    ]
    for yr in sorted(by_year.keys(), reverse=True):
        lines.append(f"## {yr}")
        lines.append("")
        for rec in by_year[yr]:
            doi_link = f"[{rec['doi']}](https://doi.org/{rec['doi']})" if rec.get("doi") else "no DOI"
            lines.append(f"- {rec['title']} — {doi_link} — `{rec['filename']}`")
        lines.append("")

    with open(CORPUS_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {CORPUS_MD}")

    # ── summary ───────────────────────────────────────────────────────────────
    years = [r.get("year","") for r in corpus if r.get("year","").isdigit()]
    if years:
        print(f"\n  Year range: {min(years)} – {max(years)}")
    db_counts = {}
    for r in corpus:
        db = r.get("db_source","Unknown")
        db_counts[db] = db_counts.get(db, 0) + 1
    print("  By database:")
    for db, cnt in sorted(db_counts.items()):
        print(f"    {db:<12} {cnt}")

    print(f"\n  NEXT STEP: python3 download_oa.py")
    print(f"{'═'*70}\n")


if __name__ == "__main__":
    main()
