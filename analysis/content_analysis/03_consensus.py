#!/usr/bin/env python3
"""
Pipeline 2 – Dual-Round Consensus
Script 03: Compare Round 1 and Round 2 category assignments; compute consensus.

Consensus rule (following the isvlsi26 dual-round methodology):
  CONFIRMED  : paper assigned to category by BOTH rounds → included in final count
  ROUND_1_ONLY / ROUND_2_ONLY : assigned by one round only → flagged as disputed
  NOT_ASSIGNED : neither round assigned the category

The CONFIRMED counts are what should be reported in Table III of the paper.
The agreement rate per category is reported in the methodology section.

Outputs:
  pipeline2_analysis/outputs/tables/taxonomy_consensus.csv
      — per-category: R1 count, R2 count, consensus count, disputed counts,
        agreement rate, consensus %
  pipeline2_analysis/outputs/tables/taxonomy_disagreements.csv
      — one row per (paper × category) disagreement for manual inspection
  pipeline2_analysis/outputs/tables/consensus_summary.txt
      — human-readable table for copying into the paper

Requirements: pip install pandas
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT  = ROOT / "pipeline2_analysis" / "outputs" / "tables"

CATEGORIES = [
    "A_automated_grading",
    "B_authentic_assessment",
    "C_academic_integrity",
    "D_formative_adaptive",
    "E_ethics_policy",
    "F_perception_affect",
    "G_review_methodology",
]

LABELS = {
    "A_automated_grading"   : "Automated Grading",
    "B_authentic_assessment": "Authentic Assessment Redesign",
    "C_academic_integrity"  : "Academic Integrity",
    "D_formative_adaptive"  : "Formative and Adaptive Assessment",
    "E_ethics_policy"       : "Ethics and Policy",
    "F_perception_affect"   : "Perception and Affect",
    "G_review_methodology"  : "Review / Methodology",
}


def load_coding(path: Path) -> dict[str, set[str]]:
    """Return {filename: set_of_category_codes}."""
    df = pd.read_csv(path, dtype=str)
    result = {}
    for _, row in df.iterrows():
        fn = row["filename"]
        raw = row.get("categories", "")
        cats = set(raw.split("|")) if pd.notna(raw) and raw.strip() else set()
        result[fn] = cats
    return result


def main():
    r1_path = OUT / "thematic_coding.csv"
    r2_path = OUT / "thematic_coding_alt.csv"

    if not r1_path.exists():
        raise FileNotFoundError(f"Round 1 output not found: {r1_path}\n"
                                "Run 02_thematic_coding.py first.")
    if not r2_path.exists():
        raise FileNotFoundError(f"Round 2 output not found: {r2_path}\n"
                                "Run 01b_text_extraction_alt.py then "
                                "02b_thematic_coding_alt.py first.")

    r1 = load_coding(r1_path)
    r2 = load_coding(r2_path)

    # Papers present in both rounds (intersection for fairness)
    common = sorted(set(r1) & set(r2))
    n = len(common)
    print(f"Papers in both rounds: {n}")
    print(f"  Round 1 only: {len(set(r1) - set(r2))}")
    print(f"  Round 2 only: {len(set(r2) - set(r1))}")

    # Accumulate counts
    counts = {cat: {"r1": 0, "r2": 0, "confirmed": 0,
                    "r1_only": 0, "r2_only": 0}
              for cat in CATEGORIES}

    disagreement_rows = []

    for fn in common:
        cats_r1 = r1[fn]
        cats_r2 = r2[fn]

        for cat in CATEGORIES:
            in1 = cat in cats_r1
            in2 = cat in cats_r2

            counts[cat]["r1"] += int(in1)
            counts[cat]["r2"] += int(in2)

            if in1 and in2:
                counts[cat]["confirmed"] += 1
            elif in1 and not in2:
                counts[cat]["r1_only"] += 1
                disagreement_rows.append({
                    "filename": fn, "category": cat,
                    "round1": "YES", "round2": "NO",
                    "verdict": "ROUND_1_ONLY",
                })
            elif in2 and not in1:
                counts[cat]["r2_only"] += 1
                disagreement_rows.append({
                    "filename": fn, "category": cat,
                    "round1": "NO", "round2": "YES",
                    "verdict": "ROUND_2_ONLY",
                })

    # Build consensus summary
    summary_rows = []
    for cat in CATEGORIES:
        c = counts[cat]
        # Agreement = papers where both rounds give same answer (YES+YES or NO+NO)
        both_no = n - (c["r1"] + c["r2"] - c["confirmed"])   # neither assigned
        agreements = c["confirmed"] + both_no
        agree_pct = round(agreements / n * 100, 1) if n > 0 else 0
        cons_pct  = round(c["confirmed"] / n * 100, 1) if n > 0 else 0

        summary_rows.append({
            "category"        : cat,
            "label"           : LABELS[cat],
            "round1_count"    : c["r1"],
            "round1_pct"      : round(c["r1"] / n * 100, 1) if n > 0 else 0,
            "round2_count"    : c["r2"],
            "round2_pct"      : round(c["r2"] / n * 100, 1) if n > 0 else 0,
            "consensus_count" : c["confirmed"],
            "consensus_pct"   : cons_pct,
            "r1_only"         : c["r1_only"],
            "r2_only"         : c["r2_only"],
            "total_disputed"  : c["r1_only"] + c["r2_only"],
            "agreement_pct"   : agree_pct,
        })

    pd.DataFrame(summary_rows).to_csv(OUT / "taxonomy_consensus.csv", index=False)
    pd.DataFrame(disagreement_rows).to_csv(OUT / "taxonomy_disagreements.csv", index=False)

    # ── Human-readable summary ────────────────────────────────────────────────
    lines = [
        "=" * 80,
        "DUAL-ROUND CONSENSUS SUMMARY",
        f"Papers in consensus analysis: {n}",
        f"Total (paper × category) disagreements: {len(disagreement_rows)}",
        "=" * 80,
        f"{'Category':<35} {'R1':>5} {'R2':>5} {'Cons':>6} {'Cons%':>6} {'Agree%':>7}",
        "-" * 80,
    ]
    for r in summary_rows:
        lines.append(
            f"{r['label']:<35} {r['round1_count']:>5} {r['round2_count']:>5}"
            f" {r['consensus_count']:>6} {r['consensus_pct']:>5.1f}% {r['agreement_pct']:>6.1f}%"
        )
    lines += [
        "=" * 80,
        "",
        "UPDATE bare_conf.tex Table III with CONSENSUS_COUNT and CONSENSUS_PCT.",
        "Update the methodology section with the agreement rates above.",
        "Review taxonomy_disagreements.csv for manual inspection of disputed cases.",
    ]

    summary_text = "\n".join(lines)
    (OUT / "consensus_summary.txt").write_text(summary_text)
    print("\n" + summary_text)


if __name__ == "__main__":
    main()
