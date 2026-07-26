#!/usr/bin/env python3
"""
Pipeline 2 – Round 2: Alternative Thematic Coding
Script 02b: Taxonomy coding using independently worded vocabulary.

Round 2 counterpart to 02_thematic_coding.py.
Design differences from Round 1:
  - Input       : fulltext_extracts_alt.jsonl (pypdf extraction)
  - Vocabulary  : independently devised synonyms / paraphrases (Vocabulary B) —
                  no term appears in Vocabulary A; same 2+-word phrase rule applies
  - Matching    : same threshold as Round 1 (any single keyword match), making
                  vocabulary the sole variable between rounds
  - No default  : unmatched papers remain uncoded so disagreements are visible
  - Matching    : uses fast substring search (kw in text) — word-boundary regex
                  is unnecessary for 2+-word phrases and adds significant overhead

Run 03_consensus.py after both rounds to compute the consensus taxonomy counts
that are reported in the paper.

Outputs:
  analysis/outputs/tables/thematic_coding_alt.csv
  analysis/outputs/tables/taxonomy_summary_alt.csv

Requirements:
  pip install pandas tqdm
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
from tqdm import tqdm

ROOT    = Path(__file__).resolve().parent.parent.parent
CORPUS  = ROOT / "data" / "processed" / "corpus_final.json"
EXTRACT = ROOT / "analysis" / "outputs" / "tables" / "fulltext_extracts_alt.jsonl"
OUT     = ROOT / "analysis" / "outputs" / "tables"

# ── Vocabulary B (Round 2) ────────────────────────────────────────────────────
# Design rules (revised):
#   1. All terms are 2+ word phrases — no single generic words
#   2. All terms are category-specific: independently devised synonyms and
#      paraphrases that a second coder would naturally choose for the same
#      category definitions, without reference to Vocabulary A
#   3. No term appears in Vocabulary A (see 02_thematic_coding.py)
#   4. Comparable breadth to Vocabulary A: terms should be similarly accessible
#      (neither over-specific rare compound phrases nor over-broad generic terms)
#
# Threshold change (from ≥2 to ≥1):
#   Both rounds now apply the same matching rule (any single keyword match).
#   This isolates vocabulary as the sole variable between rounds, making the
#   consensus a clean cross-vocabulary confirmation: a paper is counted only
#   when two independently constructed vocabularies both identify it.

TAXONOMY_ALT = {
    "A_automated_grading": [
        # independent synonyms for AI/LLM-based grading and scoring
        "machine grading", "computer-assisted grading", "algorithmic grading",
        "model-based scoring", "llm-based grading", "gpt-based scoring",
        "ai-assisted grading", "ai-assisted marking", "submission scoring",
        "assignment evaluation", "homework grading", "test grading",
        "marking automation", "grade automation", "automated assessment tool",
        "ai marking system", "scoring automation",
    ],
    "B_authentic_assessment": [
        # independent synonyms for AI-aware/AI-resistant/AI-integrated assessment design
        "rethinking assessment", "assessment innovation", "redesigned assessment",
        "oral defence format", "synchronous oral assessment", "spoken assessment",
        "reflective portfolio", "artefact-based assessment", "process-based assessment",
        "ai-proof assessment", "cheat-resistant assessment", "ai-aware assessment",
        "industry-aligned assessment", "workplace-based assessment", "situated assessment",
        "experiential assessment", "design-based assessment",
    ],
    "C_academic_integrity": [
        # independent synonyms for academic honesty, AI detection, misconduct
        "assessment integrity", "assessment fraud", "integrity enforcement",
        "generative ai detection", "llm detection", "ai text identification",
        "unauthorised assistance", "student dishonesty", "cheating behaviour",
        "text authenticity", "originality verification", "ai watermarking",
        "gpt-generated text", "ai misuse", "integrity policy",
        "ai abuse", "academic fraud",
    ],
    "D_formative_adaptive": [
        # independent synonyms for AI-driven formative/adaptive feedback
        "ongoing feedback", "continuous assessment", "diagnostic feedback",
        "ai coaching", "virtual tutor", "virtual teaching assistant",
        "adaptive learning", "personalized learning", "learning pathway",
        "hint generation", "socratic questioning", "guided feedback",
        "mastery learning", "corrective feedback", "step-by-step feedback",
        "ai-assisted feedback", "tailored feedback",
    ],
    "E_ethics_policy": [
        # independent synonyms for AI ethics, governance, equity in education
        "ethical issues", "ethical challenges", "ethical framework",
        "university regulation", "government regulation", "policy guideline",
        "governance framework", "regulatory framework", "accountability framework",
        "algorithmic fairness", "bias mitigation", "fairness concern",
        "technology access gap", "inclusive access", "resource equity",
        "privacy concern", "ethical consideration",
    ],
    "F_perception_affect": [
        # independent synonyms for student/instructor perceptions and affect
        "learner attitude", "educator perception", "academic staff perception",
        "affective response", "emotional response", "student emotions",
        "digital self-efficacy", "academic self-efficacy", "ai confidence",
        "resistance to ai", "discomfort with ai", "comfort with ai",
        "instructor view", "faculty view", "staff attitude",
        "ai engagement", "student engagement with ai",
    ],
    "G_review_methodology": [
        # independent synonyms for reviews and methodological papers
        "evidence synthesis", "knowledge mapping", "research landscape",
        "state of the art review", "survey of research",
        "thematic analysis", "content analysis review",
        "scoping study", "integrative review", "narrative review",
        "conceptual framework proposal", "research taxonomy",
        "structured review", "rapid review",
        "research agenda synthesis",
    ],
}

# Both rounds now use the same threshold (any single keyword match).
# Vocabulary is the sole variable between rounds.
MATCH_THRESHOLD = 1


def code_text_alt(text: str) -> list[str]:
    """Assign categories where ≥ MATCH_THRESHOLD distinct keywords are found.

    Uses fast substring search (kw in text_lower) rather than regex.
    All Vocabulary B terms are 2+-word phrases, so substring matching is
    equivalent to word-boundary regex without the compilation overhead.
    """
    text_lower = text.lower()
    codes = []
    for cat, keywords in TAXONOMY_ALT.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits >= MATCH_THRESHOLD:
            codes.append(cat)
    # No default fallback — unmatched papers remain uncoded so disagreements are
    # visible in the consensus comparison rather than hidden behind a G default.
    return codes


def main():
    corpus = {p["filename"]: p for p in json.loads(CORPUS.read_text())}

    rows = []
    cat_counts = defaultdict(int)

    with open(EXTRACT, encoding="utf-8") as f:
        for line in tqdm(f, desc="Round 2 coding (alt vocab, threshold ≥1)"):
            rec   = json.loads(line)
            fn    = rec["filename"]
            text  = rec.get("text", "")
            codes = code_text_alt(text)
            paper = corpus.get(fn, {})

            row = {
                "filename"    : fn,
                "doi"         : paper.get("doi", ""),
                "title"       : paper.get("title", ""),
                "year"        : paper.get("year", ""),
                "categories"  : "|".join(codes) if codes else "",
                "n_categories": len(codes),
                "word_count"  : rec.get("word_count", 0),
            }
            rows.append(row)
            for c in codes:
                cat_counts[c] += 1

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "thematic_coding_alt.csv", index=False)

    n = len(rows)
    summary = pd.DataFrame([
        {
            "category"   : cat,
            "label"      : cat.split("_", 1)[1].replace("_", " ").title(),
            "papers_r2"  : cnt,
            "pct_r2"     : round(cnt / n * 100, 1) if n > 0 else 0,
        }
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1])
    ])
    summary.to_csv(OUT / "taxonomy_summary_alt.csv", index=False)

    print(f"\nRound 2 coding complete: {n} papers → {OUT / 'thematic_coding_alt.csv'}")
    print("\nRound 2 distribution (alt vocab, threshold ≥1):")
    for _, r in summary.iterrows():
        bar = "█" * int(r["pct_r2"] / 2)
        print(f"  {r['category']:<30} {r['papers_r2']:>4} papers  {r['pct_r2']:>5.1f}%  {bar}")
    print("\nRun 03_consensus.py to compute the consensus counts for the paper.")


if __name__ == "__main__":
    main()
