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
  pipeline2_analysis/outputs/tables/thematic_coding.csv
  pipeline2_analysis/outputs/tables/taxonomy_summary.csv

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
EXTRACT = ROOT / "pipeline2_analysis" / "outputs" / "tables" / "fulltext_extracts.jsonl"
OUT     = ROOT / "pipeline2_analysis" / "outputs" / "tables"

# ── Taxonomy keyword map ─────────────────────────────────────────────────────

TAXONOMY = {
    "A_automated_grading": [
        "automated grading", "automatic grading", "auto-grading", "autograding",
        "automated assessment", "automated marking", "code grading", "programming assignment",
        "code review", "test case", "unit test", "automated feedback", "autofeedback",
        "llm grading", "gpt grading", "ai grading", "rubric scoring", "essay scoring",
        "short answer grading", "automated evaluation", "code evaluation",
    ],
    "B_authentic_assessment": [
        "authentic assessment", "performance-based", "project-based", "portfolio",
        "capstone", "design project", "real-world task", "workplace", "competency",
        "outcome-based", "obe", "problem-based learning", "case study assessment",
        "lab assessment", "practical assessment", "viva", "oral examination",
    ],
    "C_academic_integrity": [
        "academic integrity", "academic dishonesty", "plagiarism", "ai detection",
        "chatgpt detection", "gptzero", "turnitin", "contract cheating",
        "essay mill", "ghostwriting", "misconduct", "honour code", "originality",
        "authorship", "ai-generated text", "text authenticity", "humanize",
    ],
    "D_formative_adaptive": [
        "formative assessment", "adaptive assessment", "feedback generation",
        "personalized feedback", "immediate feedback", "chatbot feedback",
        "ai tutor", "ai teaching assistant", "conversational agent",
        "intelligent tutoring", "learning analytics", "self-assessment",
        "peer assessment", "metacognition", "scaffolding",
    ],
    "E_ethics_policy": [
        "ethics", "ethical", "policy", "regulation", "accreditation", "abet",
        "governance", "bias", "fairness", "equity", "transparency",
        "explainability", "responsible ai", "ai policy", "institutional policy",
        "higher education policy", "curriculum policy", "faculty guideline",
    ],
    "F_perception_affect": [
        "student perception", "faculty perception", "attitude", "trust",
        "anxiety", "acceptance", "adoption", "tam", "technology acceptance",
        "engagement", "motivation", "satisfaction", "concern", "awareness",
        "student experience", "instructor experience",
    ],
    "G_review_methodology": [
        "systematic review", "literature review", "meta-analysis", "bibliometric",
        "sok", "systematization", "scoping review", "mapping study",
        "research agenda", "framework", "taxonomy", "ontology",
    ],
}


def code_text(text: str) -> list[str]:
    text_lower = text.lower()
    codes = []
    for cat, keywords in TAXONOMY.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                codes.append(cat)
                break
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
