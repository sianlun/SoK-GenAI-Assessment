#!/usr/bin/env python3
"""
Pipeline 2 – Phase 2: Content Analysis
Script 02: Keyword-based thematic coding on extracted full text.

Maps each paper to one or more SoK taxonomy categories:
  A — Automated grading & feedback (programming, code)
  B — Authentic & performance-based assessment design
  C — Academic integrity & AI detection
  D — AI as evaluation co-pilot (formative, adaptive)
  E — Ethical governance, policy & accreditation
  F — Student perception & affect (trust, anxiety)
  G — Foundational / review / methodological

Outputs:
  analysis/outputs/tables/thematic_coding.csv
  analysis/outputs/tables/taxonomy_summary.csv

Requirements:
  pip install pandas tqdm
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
from tqdm import tqdm

ROOT    = Path(__file__).parent.parent.parent
CORPUS  = ROOT / "data" / "processed" / "corpus_final.json"
EXTRACT = ROOT / "analysis" / "outputs" / "tables" / "fulltext_extracts.jsonl"
OUT     = ROOT / "analysis" / "outputs" / "tables"

# ── Taxonomy keyword map ─────────────────────────────────────────────────────

# ── Vocabulary A (Round 1) ────────────────────────────────────────────────────
# Design rules:
#   1. All terms are 2+ word phrases — no single generic words
#   2. All terms are category-specific: unlikely to appear in papers not about
#      the topic (e.g. "ethics" is too broad; "ai ethics" is specific)
#   3. No term appears in Vocabulary B (see 02b_thematic_coding_alt.py)
#   4. Comparable breadth across categories (~16-18 terms each)

TAXONOMY = {
    "A_automated_grading": [
        "automated grading", "automated marking", "automated scoring",
        "automated feedback", "ai grading", "ai scoring",
        "ai marking", "llm grading", "gpt grading",
        "code grading", "programming assessment", "rubric scoring",
        "essay scoring", "short answer grading", "automated essay scoring",
        "ai-generated feedback", "grading automation",
    ],
    "B_authentic_assessment": [
        "authentic assessment", "assessment redesign", "ai-resistant assessment",
        "oral examination", "oral defence", "oral assessment",
        "portfolio assessment", "process portfolio", "capstone assessment",
        "project-based assessment", "problem-based assessment", "performance-based assessment",
        "ai-integrated assessment", "assessment reform", "assessment transformation",
        "competency-based assessment", "redesigning assessment",
    ],
    "C_academic_integrity": [
        "academic integrity", "academic dishonesty", "academic misconduct",
        "ai detection", "chatgpt detection", "plagiarism detection",
        "contract cheating", "ai-generated text", "ai content detection",
        "integrity violation", "cheating detection", "misconduct detection",
        "ghostwriting detection", "originality check", "ai plagiarism",
        "honour code", "student misconduct",
    ],
    "D_formative_adaptive": [
        "formative assessment", "formative feedback", "adaptive assessment",
        "ai tutor", "ai tutoring", "ai teaching assistant",
        "intelligent tutoring", "personalized feedback", "adaptive feedback",
        "chatbot feedback", "immediate feedback", "real-time feedback",
        "on-demand feedback", "learning analytics", "conversational agent",
        "feedback generation", "ai-powered feedback",
    ],
    "E_ethics_policy": [
        "ai ethics", "ethical implications", "ethical concerns",
        "ai policy", "institutional ai policy", "academic ai policy",
        "ai regulation", "ai governance", "algorithmic bias",
        "ai fairness", "digital equity", "equitable access",
        "responsible ai", "data privacy", "student privacy",
        "ai accountability", "ethics of ai",
    ],
    "F_perception_affect": [
        "student perception", "instructor perception", "faculty perception",
        "student attitude", "instructor attitude", "ai anxiety",
        "ai acceptance", "ai adoption", "technology acceptance",
        "ai trust", "student experience", "ai concern",
        "ai awareness", "student wellbeing", "user experience with ai",
        "ai apprehension", "attitude toward ai",
    ],
    "G_review_methodology": [
        "systematic review", "literature review", "meta-analysis", "bibliometric",
        "sok", "systematization", "scoping review", "mapping study",
        "research agenda", "framework", "taxonomy", "ontology",
    ],
}


def code_text(text: str) -> list[str]:
    """Assign categories on presence of any single keyword (substring match).

    Uses fast substring search rather than regex. All Vocabulary A terms are
    2+-word phrases, so substring matching is equivalent without regex overhead.
    """
    text_lower = text.lower()
    codes = [cat for cat, keywords in TAXONOMY.items()
             if any(kw in text_lower for kw in keywords)]
    return codes or ["G_review_methodology"]   # default if no match


def main():
    corpus  = {p["filename"]: p for p in json.loads(CORPUS.read_text())}

    # Load extracted texts
    rows    = []
    cat_counts = defaultdict(int)

    with open(EXTRACT, encoding="utf-8") as f:
        for line in tqdm(f, desc="Coding papers"):
            rec    = json.loads(line)
            fn     = rec["filename"]
            text   = rec.get("text", "")
            codes  = code_text(text)
            paper  = corpus.get(fn, {})

            row = {
                "filename"   : fn,
                "doi"        : paper.get("doi", ""),
                "title"      : paper.get("title", ""),
                "year"       : paper.get("year", ""),
                "publisher"  : paper.get("publisher", ""),
                "categories" : "|".join(codes),
                "n_categories": len(codes),
                "word_count" : rec.get("word_count", 0),
            }
            rows.append(row)
            for c in codes:
                cat_counts[c] += 1

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "thematic_coding.csv", index=False)

    # Summary table
    summary = pd.DataFrame([
        {"category": cat, "label": cat.split("_", 1)[1].replace("_", " ").title(),
         "papers": cnt, "pct": round(cnt / len(rows) * 100, 1)}
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1])
    ])
    summary.to_csv(OUT / "taxonomy_summary.csv", index=False)

    print(f"\nCoded {len(rows)} papers → {OUT / 'thematic_coding.csv'}")
    print("\nTaxonomy distribution:")
    for _, r in summary.iterrows():
        bar = "█" * int(r["pct"] / 2)
        print(f"  {r['category']:<30} {r['papers']:>4} papers  {r['pct']:>5.1f}%  {bar}")


if __name__ == "__main__":
    main()
