"""
00_normalize_bib.py
====================
Converts IEEE Xplore, ACM Digital Library, and ERIC BibTeX exports into
Scopus-compatible BibTeX so that bibliometrix::convert2df() can load them.

Field mappings applied
----------------------
  author         : kept (IEEE/ACM are already "Last, First"); ERIC "First Last" → flipped
  booktitle      : → journal  (for conference entries)
  keywords       : → author_keywords  (semicolon-normalised)
  year           : ERIC uses "2026/01/01/" → extract 4-digit year
  type           : derived from ENTRYTYPE
  affiliations   : added as empty string  (C1 in bibliometrix)
  source         : set to "Scopus" so convert2df parses it correctly

Output: data/raw/ieee_acm_eric_normalized.bib
"""

import re
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent
ROOT = HERE.parent.parent
RAW  = ROOT / "data" / "raw"

IEEE_BIB = RAW / "ieee_combined_278.bib"
ACM_BIB  = RAW / "acm_1113.bib"
ERIC_BIB = RAW / "eric_69.bib"
OUT_BIB  = RAW / "ieee_acm_eric_normalized.bib"

# ── helpers ─────────────────────────────────────────────────────────────────

def extract_year(raw: str) -> str:
    """Pull a 4-digit year from strings like '2026/01/01/' or '2026'."""
    m = re.search(r"\b(20\d{2})\b", raw or "")
    return m.group(1) if m else ""


def flip_author_name(name: str) -> str:
    """
    Convert 'Firstname [Middle] Lastname' → 'Lastname, Firstname [Middle]'.
    Handles 'Jr.' / 'II' / 'III' suffixes by leaving them at the end.
    Does NOT touch names that already contain a comma (already 'Last, First').
    """
    if "," in name:
        return name   # already in Last, First format
    parts = name.strip().split()
    if len(parts) == 1:
        return name
    # Move last token to front as surname
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def normalise_authors(raw: str, flip: bool = False) -> str:
    """Split on ' and ', optionally flip each name, rejoin."""
    if not raw:
        return ""
    authors = [a.strip() for a in re.split(r"\s+and\s+", raw, flags=re.IGNORECASE)]
    if flip:
        authors = [flip_author_name(a) for a in authors]
    return " and ".join(authors)


def normalise_keywords(raw: str, separator: str = ",") -> str:
    """Split on separator, strip whitespace, rejoin with '; '."""
    if not raw:
        return ""
    kws = [k.strip() for k in raw.split(separator) if k.strip()]
    return "; ".join(kws)


def doc_type(entry_type: str) -> str:
    mapping = {
        "inproceedings": "Conference paper",
        "conference":    "Conference paper",
        "article":       "Article",
        "inbook":        "Book chapter",
        "book":          "Book",
        "phdthesis":     "Thesis",
        "mastersthesis": "Thesis",
        "techreport":    "Report",
    }
    return mapping.get(entry_type.lower(), "Article")


# ── per-source normalisation ────────────────────────────────────────────────

def load_bib(path: Path) -> list:
    """Load a BibTeX file, return list of entry dicts."""
    with open(path, encoding="utf-8", errors="replace") as f:
        db = bibtexparser.load(f)
    return db.entries


def normalise_ieee(entries: list) -> list:
    out = []
    for e in entries:
        n = {}
        n["ENTRYTYPE"]       = "article"          # bibliometrix handles this fine
        n["ID"]              = e.get("ID", "")
        n["author"]          = normalise_authors(e.get("author", ""), flip=False)
        n["title"]           = e.get("title", "")
        # conference papers have booktitle, articles have journal
        n["journal"]         = e.get("journal") or e.get("booktitle", "")
        n["year"]            = extract_year(e.get("year", ""))
        n["abstract"]        = e.get("abstract", "")
        # IEEE uses ';' already for keywords — but sometimes ',' — normalise both
        raw_kw = e.get("keywords", "")
        sep = ";" if ";" in raw_kw else ","
        n["author_keywords"] = normalise_keywords(raw_kw, sep)
        n["keywords"]        = ""          # ID (Keywords Plus) — not available
        n["affiliations"]    = ""          # C1 — not available
        n["doi"]             = e.get("doi", "")
        n["issn"]            = e.get("issn", "")
        n["volume"]          = e.get("volume", "")
        n["number"]          = e.get("number", "")
        n["pages"]           = e.get("pages", "")
        n["type"]            = doc_type(e.get("ENTRYTYPE", "article"))
        n["source"]          = "Scopus"
        out.append(n)
    return out


def normalise_acm(entries: list) -> list:
    out = []
    for e in entries:
        n = {}
        n["ENTRYTYPE"]       = "article"
        n["ID"]              = e.get("ID", "")
        n["author"]          = normalise_authors(e.get("author", ""), flip=False)
        n["title"]           = e.get("title", "")
        n["journal"]         = e.get("journal") or e.get("booktitle") or e.get("series", "")
        n["year"]            = extract_year(e.get("year", ""))
        n["abstract"]        = e.get("abstract", "")
        # ACM uses comma separation
        n["author_keywords"] = normalise_keywords(e.get("keywords", ""), ",")
        n["keywords"]        = ""
        n["affiliations"]    = ""
        n["doi"]             = e.get("doi", "")
        n["issn"]            = e.get("issn", "")
        n["volume"]          = e.get("volume", "")
        n["number"]          = e.get("number", "")
        n["pages"]           = e.get("pages", "")
        n["type"]            = doc_type(e.get("ENTRYTYPE", "article"))
        n["source"]          = "Scopus"
        out.append(n)
    return out


def normalise_eric(entries: list) -> list:
    out = []
    for e in entries:
        n = {}
        n["ENTRYTYPE"]       = "article"
        # ERIC keys are like EJ149739020260101 — keep but prefix to avoid collisions
        n["ID"]              = "ERIC_" + e.get("ID", "")
        # ERIC author field is "First Last" format → flip
        n["author"]          = normalise_authors(e.get("author", ""), flip=True)
        n["title"]           = e.get("title", "")
        n["journal"]         = e.get("journal", "")
        n["year"]            = extract_year(e.get("year", ""))
        n["abstract"]        = e.get("abstract", "")
        # ERIC uses comma separation
        n["author_keywords"] = normalise_keywords(e.get("keywords", ""), ",")
        n["keywords"]        = ""
        n["affiliations"]    = ""
        n["doi"]             = e.get("doi", "")
        n["issn"]            = e.get("issn", "")
        n["volume"]          = e.get("volume", "")
        n["number"]          = e.get("number", "")
        n["pages"]           = e.get("pages", "")
        n["type"]            = doc_type(e.get("ENTRYTYPE", "article"))
        n["source"]          = "Scopus"
        out.append(n)
    return out


# ── write ───────────────────────────────────────────────────────────────────

def write_bib(entries: list, path: Path):
    db = BibDatabase()
    db.entries = entries
    writer = BibTexWriter()
    writer.indent = "\t"
    writer.comma_first = False
    with open(path, "w", encoding="utf-8") as f:
        f.write(writer.write(db))


# ── main ────────────────────────────────────────────────────────────────────

def main():
    print("Loading IEEE  …", end=" ")
    ieee_raw = load_bib(IEEE_BIB)
    print(f"{len(ieee_raw)} entries")

    print("Loading ACM   …", end=" ")
    acm_raw = load_bib(ACM_BIB)
    print(f"{len(acm_raw)} entries")

    print("Loading ERIC  …", end=" ")
    eric_raw = load_bib(ERIC_BIB)
    print(f"{len(eric_raw)} entries")

    ieee_norm  = normalise_ieee(ieee_raw)
    acm_norm   = normalise_acm(acm_raw)
    eric_norm  = normalise_eric(eric_raw)

    # Deduplicate within this combined set by DOI (keep first seen)
    seen_dois = set()
    combined = []
    no_doi = 0
    dup = 0
    for entry in ieee_norm + acm_norm + eric_norm:
        doi = entry.get("doi", "").strip().lower()
        if doi:
            if doi in seen_dois:
                dup += 1
                continue
            seen_dois.add(doi)
        else:
            no_doi += 1
        combined.append(entry)

    print(f"\nNormalized: IEEE={len(ieee_norm)}, ACM={len(acm_norm)}, ERIC={len(eric_norm)}")
    print(f"DOI-deduped within set: {dup} removed")
    print(f"Entries without DOI (kept): {no_doi}")
    print(f"Total output: {len(combined)} entries")

    write_bib(combined, OUT_BIB)
    print(f"\nWritten → {OUT_BIB}")

    # Quick sanity check
    with open(OUT_BIB, encoding="utf-8") as f:
        check = bibtexparser.load(f)
    print(f"Re-parse check: {len(check.entries)} entries loaded OK")


if __name__ == "__main__":
    main()
