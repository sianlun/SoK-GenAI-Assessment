"""
01b_enrich_affiliations.py
===========================
Queries OpenAlex for author affiliations for IEEE/ACM/ERIC records
(which lack C1/affiliation data in their BibTeX exports).

RESUMABLE: Progress is checkpointed to affiliations_enriched.csv after every
SAVE_EVERY records. If interrupted, re-running skips already-processed DOIs.

Usage:
  python3 pipeline2_analysis/bibliometrics/01b_enrich_affiliations.py

Set OPENALEX_EMAIL env var or edit EMAIL below for the polite pool (100 req/s).
Default (no email): 10 req/s.

Output:
  data/processed/affiliations_enriched.csv   — one row per queried DOI
  data/processed/affiliations_enrichment_log.json

Next step:
  Rscript pipeline2_analysis/bibliometrics/01c_apply_affiliations.R
"""

import os
import re
import time
import json
import csv
import sys
import requests
import pandas as pd
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────
HERE      = Path(__file__).parent
ROOT      = HERE.parent.parent
PROC      = ROOT / "data" / "processed"
OUT_CSV   = PROC / "affiliations_enriched.csv"
OUT_LOG   = PROC / "affiliations_enrichment_log.json"
MERGED_CSV = PROC / "bibliometrix_merged.csv"   # exported from R — see below

EMAIL     = os.environ.get("OPENALEX_EMAIL", "sianlunl@sunway.edu.my")
BASE      = "https://api.openalex.org/works"
DELAY     = 0.12    # ~8 req/s (polite pool allows 100/s with email)
SAVE_EVERY = 50     # write checkpoint every N records

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_doi(raw: str) -> str:
    return re.sub(r"https?://doi\.org/", "", str(raw).strip().lower())


def query_openalex(doi: str) -> dict | None:
    url = f"{BASE}/doi:{doi}"
    params = {"mailto": EMAIL, "select": "id,authorships,title"}
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return None
        elif r.status_code == 429:
            print("  Rate limited — sleeping 30s …")
            time.sleep(30)
            return query_openalex(doi)   # one retry
        else:
            print(f"  HTTP {r.status_code} for doi:{doi}")
            return None
    except requests.Timeout:
        print(f"  Timeout for doi:{doi} — skipping")
        return None
    except requests.RequestException as e:
        print(f"  Request error for doi:{doi}: {e}")
        return None


def parse_affiliations(work: dict) -> tuple[str, str]:
    """
    Returns (c1_string, country_string) in bibliometrix format.
    c1_string  : "[LastnameF, Institution, Country] [...]"
    country_string: "US;FI;NZ;..."
    """
    if not work or "authorships" not in work:
        return "", ""

    c1_parts, countries = [], []
    for authorship in work.get("authorships", []):
        display = authorship.get("author", {}).get("display_name", "")
        parts   = display.strip().split()
        if len(parts) >= 2:
            author_tag = f"{parts[-1]}{''.join(p[0] for p in parts[:-1])}"
        else:
            author_tag = display

        insts = authorship.get("institutions", [])
        inst_names = []
        for inst in insts:
            name    = inst.get("display_name", "")
            country = inst.get("country_code", "")
            if name:
                inst_names.append(name)
            if country and country not in countries:
                countries.append(country)
        if inst_names:
            c1_parts.append(f"[{author_tag}, {'; '.join(inst_names)}]")
        else:
            c1_parts.append(f"[{author_tag}]")

    return " ".join(c1_parts), ";".join(countries)

# ── Load source data ──────────────────────────────────────────────────────────

if not MERGED_CSV.exists():
    print("bibliometrix_merged.csv not found.")
    print("Export it first from R:")
    print()
    print('  Rscript -e \'write.csv(readRDS("data/processed/bibliometrix_merged.rds"),')
    print('             "data/processed/bibliometrix_merged.csv", row.names=FALSE)\'')
    sys.exit(1)

print(f"Loading {MERGED_CSV.name} …")
df = pd.read_csv(MERGED_CSV, dtype=str).fillna("")
print(f"  {len(df)} total records")

# Filter to IEEE/ACM/ERIC records with DOIs
db_col  = next((c for c in df.columns if c.upper() == "DB_SOURCE"), None)
doi_col = next((c for c in df.columns if c.upper() in ("DI", "DOI")), None)

if db_col is None or doi_col is None:
    print(f"ERROR: Could not find DB_SOURCE or DI column. Columns: {list(df.columns[:20])}")
    sys.exit(1)

target = df[df[db_col] == "IEEE_ACM_ERIC"].copy()
target = target[target[doi_col].str.strip().str.len() > 3].copy()
target["_doi_norm"] = target[doi_col].apply(clean_doi)
print(f"  IEEE/ACM/ERIC records with DOI: {len(target)}")

# ── Load checkpoint (already-processed DOIs) ──────────────────────────────────

done_dois: dict[str, dict] = {}   # doi_norm → result row

if OUT_CSV.exists():
    existing = pd.read_csv(OUT_CSV, dtype=str).fillna("")
    for _, row in existing.iterrows():
        doi_norm = clean_doi(row.get("DI", ""))
        if doi_norm:
            done_dois[doi_norm] = row.to_dict()
    print(f"  Checkpoint: {len(done_dois)} DOIs already processed — will skip these")

# ── Main loop ─────────────────────────────────────────────────────────────────

fieldnames = ["DI", "C1_enriched", "AU_CO_enriched", "found"]

# Open in append mode if checkpoint exists, write mode if fresh
mode     = "a" if done_dois else "w"
f_out    = open(OUT_CSV, mode, newline="", encoding="utf-8")
writer   = csv.DictWriter(f_out, fieldnames=fieldnames)
if not done_dois:
    writer.writeheader()

pending = target[~target["_doi_norm"].isin(done_dois)].copy()
print(f"  Pending queries: {len(pending)}")

log = {"found": sum(1 for r in done_dois.values() if r.get("found") in (True, "True")),
       "not_found": sum(1 for r in done_dois.values() if r.get("found") not in (True, "True")),
       "errors": 0}

buffer = []

try:
    for i, (_, row) in enumerate(pending.iterrows()):
        doi_raw  = row[doi_col]
        doi_norm = row["_doi_norm"]

        if i % 50 == 0:
            pct = (i / max(len(pending), 1)) * 100
            print(f"  [{i}/{len(pending)}  {pct:.0f}%] querying …")

        work = query_openalex(doi_norm)
        time.sleep(DELAY)

        if work:
            c1, countries = parse_affiliations(work)
            log["found"] += 1
            found = True
        else:
            c1, countries = "", ""
            log["not_found"] += 1
            found = False

        record = {"DI": doi_raw, "C1_enriched": c1, "AU_CO_enriched": countries, "found": found}
        buffer.append(record)
        done_dois[doi_norm] = record

        # Flush to disk every SAVE_EVERY records
        if len(buffer) >= SAVE_EVERY:
            writer.writerows(buffer)
            f_out.flush()
            buffer.clear()
            print(f"    ✓ Checkpoint saved ({len(done_dois)} total)")

except KeyboardInterrupt:
    print("\n  Interrupted — saving progress …")
finally:
    if buffer:
        writer.writerows(buffer)
        f_out.flush()
    f_out.close()

# ── Write log ─────────────────────────────────────────────────────────────────

total_done  = len(done_dois)
total_found = log["found"]
pct_found   = total_found / max(total_done, 1) * 100

with open(OUT_LOG, "w", encoding="utf-8") as f:
    json.dump({**log, "total_processed": total_done,
               "total_target": len(target)}, f, indent=2)

print(f"\n✓ Done")
print(f"  Processed : {total_done} / {len(target)}")
print(f"  Found     : {total_found} ({pct_found:.1f}%)")
print(f"  Not found : {log['not_found']}")
print(f"  Written   → {OUT_CSV}")

if total_done < len(target):
    remaining = len(target) - total_done
    print(f"\n  {remaining} records still pending — re-run to continue.")
else:
    print("\n  All records processed.")
    print("  Next: Rscript pipeline2_analysis/bibliometrics/01c_apply_affiliations.R")
