#!/usr/bin/env python3
"""
find_oa_all.py — Find OA PDF links for ALL remaining papers
============================================================
Queries three sources in order of reliability:
  1. Semantic Scholar  — openAccessPdf field (best for CS/education papers)
  2. OpenAlex          — open_access.oa_url  (broadest coverage)
  3. Unpaywall         — best_oa_location    (publisher-authorised versions)

For papers without DOIs, searches by title on Semantic Scholar.

OUTPUT
  download_oa_found.sh   — wget/curl commands for all found PDFs
  find_oa_report.json    — full results for inspection

USAGE
  pip install requests
  python3 find_oa_all.py --email kiawin@gmail.com
  bash download_oa_found.sh
"""

import argparse, json, time, re
from pathlib import Path
from urllib.parse import quote

import requests

HERE      = Path(__file__).parent
MANUAL    = HERE / "download_manual.json"
PDFS_DIR  = HERE / "_pdfs"
OUT_SH    = HERE / "download_oa_found.sh"
OUT_JSON  = HERE / "find_oa_report.json"

HEADERS = {"User-Agent": "SoK-OA-Finder/1.0 (kiawin@gmail.com; research)"}


# ── API helpers ───────────────────────────────────────────────────────────────

def s2_by_doi(doi: str, session) -> str:
    """Semantic Scholar: openAccessPdf via DOI."""
    try:
        r = session.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
            f"?fields=openAccessPdf,externalIds",
            timeout=15)
        if r.status_code == 200:
            oa = r.json().get("openAccessPdf") or {}
            return oa.get("url", "")
    except Exception:
        pass
    return ""

def s2_by_title(title: str, session) -> str:
    """Semantic Scholar: search by title, return first openAccessPdf."""
    try:
        r = session.get(
            f"https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={quote(title)}&limit=3&fields=openAccessPdf,title",
            timeout=15)
        if r.status_code == 200:
            for p in r.json().get("data", []):
                oa = p.get("openAccessPdf") or {}
                if oa.get("url"):
                    return oa["url"]
    except Exception:
        pass
    return ""

def openalex_by_doi(doi: str, session) -> str:
    """OpenAlex: open_access.oa_url via DOI."""
    try:
        r = session.get(
            f"https://api.openalex.org/works/doi:{doi}",
            params={"select": "open_access,primary_location"},
            timeout=15)
        if r.status_code == 200:
            data = r.json()
            oa = data.get("open_access") or {}
            url = oa.get("oa_url") or ""
            if url:
                return url
            # Try primary location PDF
            loc = data.get("primary_location") or {}
            return loc.get("pdf_url") or ""
    except Exception:
        pass
    return ""

def openalex_by_title(title: str, author: str, session) -> str:
    """OpenAlex: search by title + author."""
    try:
        q = title[:80]
        r = session.get(
            f"https://api.openalex.org/works",
            params={"search": q, "per-page": 3,
                    "select": "open_access,display_name,primary_location"},
            timeout=15)
        if r.status_code == 200:
            for w in r.json().get("results", []):
                oa = w.get("open_access") or {}
                url = oa.get("oa_url") or ""
                if url:
                    return url
                loc = w.get("primary_location") or {}
                if loc.get("pdf_url"):
                    return loc["pdf_url"]
    except Exception:
        pass
    return ""

def unpaywall_by_doi(doi: str, email: str, session) -> str:
    """Unpaywall: best_oa_location."""
    try:
        r = session.get(
            f"https://api.unpaywall.org/v2/{doi}?email={email}",
            timeout=15)
        if r.status_code == 200:
            data = r.json()
            best = data.get("best_oa_location") or {}
            url  = best.get("url_for_pdf") or best.get("url") or ""
            if not url:
                for loc in data.get("oa_locations", []):
                    url = loc.get("url_for_pdf") or loc.get("url") or ""
                    if url: break
            return url
    except Exception:
        pass
    return ""

def verify_pdf_url(url: str, session) -> bool:
    """HEAD request to check if URL likely returns a PDF."""
    try:
        r = session.head(url, timeout=10, allow_redirects=True)
        ct = r.headers.get("Content-Type","")
        return r.status_code == 200 and ("pdf" in ct or "octet" in ct)
    except Exception:
        return True   # assume ok if HEAD fails, wget will confirm


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True,
                        help="Email for Unpaywall API")
    parser.add_argument("--skip-verify", action="store_true",
                        help="Skip HEAD verification of found URLs")
    args = parser.parse_args()

    manual = json.loads(MANUAL.read_text())
    PDFS_DIR.mkdir(exist_ok=True)

    def is_real_pdf(path):
        if not path.exists(): return False
        if path.stat().st_size < 10_000: return False
        with open(path, "rb") as f:
            return f.read(4) == b"%PDF"

    remaining = [p for p in manual
                 if not is_real_pdf(PDFS_DIR / p.get("filename",""))]

    print(f"\n{'═'*72}")
    print(f"  OA Finder — {len(remaining)} papers to search")
    print(f"  Sources: Semantic Scholar → OpenAlex → Unpaywall")
    print(f"{'═'*72}\n")

    session = requests.Session()
    session.headers.update(HEADERS)

    results  = []
    found    = []
    not_found = []

    for i, paper in enumerate(remaining, 1):
        doi      = (paper.get("doi") or "").strip()
        title    = (paper.get("title") or "").strip()
        authors  = (paper.get("authors") or "").strip()
        filename = paper.get("filename","")
        label    = (title or authors)[:60]

        oa_url = ""
        source = ""

        # ── 1. Semantic Scholar ──
        if doi:
            oa_url = s2_by_doi(doi, session)
            if oa_url: source = "s2-doi"
            time.sleep(0.5)

        if not oa_url and title:
            oa_url = s2_by_title(title, session)
            if oa_url: source = "s2-title"
            time.sleep(0.5)

        # ── 2. OpenAlex ──
        if not oa_url and doi:
            oa_url = openalex_by_doi(doi, session)
            if oa_url: source = "openalex-doi"
            time.sleep(0.3)

        if not oa_url and title:
            oa_url = openalex_by_title(title, authors, session)
            if oa_url: source = "openalex-title"
            time.sleep(0.3)

        # ── 3. Unpaywall ──
        if not oa_url and doi:
            oa_url = unpaywall_by_doi(doi, args.email, session)
            if oa_url: source = "unpaywall"
            time.sleep(0.5)

        status = f"✓ [{source:<16}]" if oa_url else "✗"
        print(f"  [{i:>3}/{len(remaining)}] {status} {label}", flush=True)

        rec = {**paper, "oa_url": oa_url, "oa_source": source}
        results.append(rec)

        if oa_url:
            found.append(rec)
        else:
            not_found.append(rec)

    # ── Write shell script ──────────────────────────────────────────────────
    lines = [
        "#!/usr/bin/env bash",
        "# download_oa_found.sh — OA PDFs found by find_oa_all.py",
        "# Prints URL on failure so you can open it manually in a browser.",
        "",
        'cd "$(dirname "$0")"',
        "mkdir -p _pdfs",
        "",
        "ok=0; fail=0; skipped=0",
        "",
    ]
    for rec in found:
        fn  = rec["filename"].replace("'", r"\'")
        url = rec["oa_url"].replace("'", r"\'")
        doi = rec.get("doi","")
        src = rec.get("oa_source","")
        lines.append(f"# [{src}] {doi}")
        lines.append(f"if [ ! -f '_pdfs/{fn}' ]; then")
        lines.append(f"  wget -q --user-agent='Mozilla/5.0' -O '_pdfs/{fn}' '{url}' 2>/dev/null || \\")
        lines.append(f"  curl -sL -A 'Mozilla/5.0' -o '_pdfs/{fn}' '{url}' 2>/dev/null || true")
        lines.append(f"  if python3 -c \"import sys; d=open('_pdfs/{fn}','rb').read(4) if __import__('os').path.exists('_pdfs/{fn}') else b''; sys.exit(0 if d==b'%PDF' else 1)\" 2>/dev/null; then")
        lines.append(f"    echo '✓  {fn}'")
        lines.append(f"    ok=$((ok+1))")
        lines.append(f"  else")
        lines.append(f"    rm -f '_pdfs/{fn}'")
        lines.append(f"    echo '✗  FAILED — copy URL to browser:'")
        lines.append(f"    echo '    {url}'")
        lines.append(f"    fail=$((fail+1))")
        lines.append(f"  fi")
        lines.append(f"else")
        lines.append(f"  skipped=$((skipped+1))")
        lines.append(f"fi")
        lines.append("")
    lines += [
        "",
        'echo ""',
        'echo "━━━ Summary ━━━"',
        'echo "✓ Downloaded : $ok"',
        'echo "✗ Failed     : $fail  (URLs shown above — open in browser)"',
        'echo "– Skipped    : $skipped  (already existed)"',
        "",
    ]

    OUT_SH.write_text("\n".join(lines), encoding="utf-8")
    OUT_SH.chmod(0o755)

    # ── Write JSON report ───────────────────────────────────────────────────
    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    # ── Summary ─────────────────────────────────────────────────────────────
    from collections import Counter
    src_counts = Counter(r["oa_source"] for r in found)

    print(f"\n{'─'*72}")
    print(f"  Found  : {len(found)} / {len(remaining)}")
    for src, n in src_counts.most_common():
        print(f"    {src:<20}: {n}")
    print(f"  Missing: {len(not_found)}")

    if not_found:
        print(f"\n  No OA version found for:")
        for p in not_found:
            doi = p.get("doi","(no doi)")
            print(f"    {doi:<35} {(p.get('title') or p.get('authors',''))[:45]}")

    print(f"\n  Script: {OUT_SH}")
    print(f"  Report: {OUT_JSON}")
    print(f"\n  NEXT STEP:")
    print(f"    bash download_oa_found.sh")
    print(f"{'═'*72}\n")


if __name__ == "__main__":
    main()
