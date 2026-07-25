#!/usr/bin/env python3
"""
Pipeline 2 – Round 2: Alternative Thematic Coding
Script 02b: Taxonomy coding using independently worded vocabulary and
            count-weighted scoring (≥ 2 distinct keyword hits required).

Round 2 counterpart to 02_thematic_coding.py.
Design differences from Round 1:
  - Input       : fulltext_extracts_alt.jsonl (pypdf, 12 pages)
  - Vocabulary  : independently devised synonyms / paraphrases — NOT copies of
                  Round 1 keywords; each category is represented by fresh wording
                  that a second independent coder would naturally choose
  - Matching    : requires ≥ MATCH_THRESHOLD (2) distinct keyword hits per category
                  (Round 1 assigns on presence of any single keyword)
  - No default  : unmatched papers remain uncoded (unlike Round 1's G fallback)
                  to make disagreements visible rather than hiding them

Run 03_consensus.py after both rounds to compute the consensus taxonomy counts
that are reported in the paper.

Outputs:
  pipeline2_analysis/outputs/tables/thematic_coding_alt.csv
  pipeline2_analysis/outputs/tables/taxonomy_summary_alt.csv

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
EXTRACT = ROOT / "pipeline2_analysis" / "outputs" / "tables" / "fulltext_extracts_alt.jsonl"
OUT     = ROOT / "pipeline2_analysis" / "outputs" / "tables"

# ── Round 2 taxonomy vocabulary ──────────────────────────────────────────────
# Each entry uses synonyms and paraphrases INDEPENDENT of Round 1's keyword set.
# This simulates a second coder working from the same category definitions but
# choosing their own vocabulary, as in the isvlsi26 dual-round methodology.

TAXONOMY_ALT = {
    "A_automated_grading": [
        # synonyms for automated grading / AI-based scoring
        "machine grading", "computer-assisted grading", "algorithmic scoring",
        "model-based scoring", "llm-based evaluation", "gpt-based assessment",
        "generative ai grading", "large language model feedback",
        "computational essay scoring", "code evaluation", "submission scoring",
        "assignment evaluation", "automated marking system",
        "ai-assisted marking", "natural language generation feedback",
    ],
    "B_authentic_assessment": [
        # synonyms for authentic / performance-based / AI-resistant design
        "real-world task", "situated assessment", "applied assessment",
        "oral defence", "oral exam", "spoken assessment",
        "industry-aligned assessment", "workplace simulation",
        "competency demonstration", "hands-on evaluation",
        "experiential assessment", "contextualised assessment",
        "project work assessment", "design challenge",
        "artefact plus reflection",
    ],
    "C_academic_integrity": [
        # synonyms for integrity / detection / misconduct
        "academic honesty", "assessment fraud", "cheating behaviour",
        "unauthorised assistance", "ai content detection",
        "gpt-generated text", "ai watermarking", "originality verification",
        "source attribution", "contract cheating prevention",
        "ai misuse", "student dishonesty", "integrity violation",
        "plagiarism detection tool", "essay authenticity",
    ],
    "D_formative_adaptive": [
        # synonyms for formative / adaptive / feedback loops
        "ongoing feedback", "continuous assessment", "diagnostic feedback",
        "ai-assisted feedback", "chatbot tutor", "virtual teaching assistant",
        "adaptive learning path", "hint generation", "socratic questioning",
        "error correction feedback", "step-by-step guidance",
        "personalized hint", "learning loop", "ai coaching",
        "mastery-based assessment",
    ],
    "E_ethics_policy": [
        # synonyms for ethics / governance / equity
        "ethical implications", "algorithmic fairness", "data privacy",
        "student data protection", "institutional guideline",
        "university regulation", "government policy",
        "digital equity", "technology access gap",
        "environmental cost", "responsible use",
        "accountability framework", "ai literacy",
        "curriculum reform", "accreditation concern",
    ],
    "F_perception_affect": [
        # synonyms for perception / affect / attitudes
        "student attitude", "learner opinion", "user perception",
        "affective response", "emotional impact", "student wellbeing",
        "digital confidence", "self-efficacy", "ai apprehension",
        "trust in ai", "comfort with ai", "resistance to ai",
        "instructor view", "faculty attitude",
        "academic community response",
    ],
    "G_review_methodology": [
        # synonyms for review / methodology / synthesis
        "evidence synthesis", "knowledge mapping", "research landscape",
        "state of the art review", "survey of research",
        "thematic analysis", "content analysis review",
        "scoping study", "integrative review", "narrative review",
        "conceptual framework proposal", "research taxonomy",
        "structured review", "rapid review",
        "research agenda synthesis",
    ],
}

# Minimum distinct keyword hits required for category assignment (Round 2 is stricter)
MATCH_THRESHOLD = 2


def code_text_alt(text: str) -> list[str]:
    """Assign categories where ≥ MATCH_THRESHOLD distinct keywords are found."""
    text_lower = text.lower()
    codes = []
    for cat, keywords in TAXONOMY_ALT.items():
        hits = sum(
            1 for kw in keywords
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
        )
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
        for line in tqdm(f, desc="Round 2 coding (alt vocab, threshold ≥2)"):
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
    print("\nRound 2 distribution (alt vocab, threshold ≥2):")
    for _, r in summary.iterrows():
        bar = "█" * int(r["pct_r2"] / 2)
        print(f"  {r['category']:<30} {r['papers_r2']:>4} papers  {r['pct_r2']:>5.1f}%  {bar}")
    print("\nRun 03_consensus.py to compute the consensus counts for the paper.")


if __name__ == "__main__":
    main()
