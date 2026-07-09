#!/usr/bin/env python3
"""
verify_pdfs.py — Verify each downloaded PDF actually matches its intended paper.
Extracts first-2-pages text via PyMuPDF, scores token overlap with the intended
title and author surnames. Flags MATCH / WEAK / MISMATCH. Also flags hash dups.
"""
import json, re, hashlib, sys
from pathlib import Path
import fitz

HERE = Path(__file__).parent
PDFS = HERE / "_pdfs"
MANUAL = json.loads((HERE / "download_manual.json").read_text())

STOP = set("the a an of for and to in on with using used use via toward towards into "
           "study case based driven aided supported model framework system approach "
           "evaluation evaluating assessment ai generative artificial intelligence "
           "education educational higher learning teaching student students through "
           "large language models llm llms chatgpt gpt new an age".split())

def real(p): return p.exists() and p.stat().st_size>=10_000 and p.read_bytes()[:4]==b"%PDF"

def toks(s):
    return set(w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w)>2 and w not in STOP)

def surnames(authors):
    # authors like "Xu, Ruoyu and Li, Gaoxiang" OR "Smita Jadhav and ..."
    out=set()
    for part in re.split(r"\band\b|;", authors or ""):
        part=part.strip()
        if not part: continue
        if "," in part:
            out.add(part.split(",")[0].strip().lower())
        else:
            ws=part.split()
            if ws: out.add(ws[-1].lower())
    return set(w for w in out if len(w)>2 and re.match(r"^[a-z\-]+$", w))

def page_text(fp, n=2):
    try:
        d=fitz.open(fp)
        t="\n".join(d[i].get_text() for i in range(min(n,len(d))))
        d.close()
        return t
    except Exception as e:
        return ""

# hash map for dup detection
by_hash={}
for p in MANUAL:
    fp=PDFS/p.get("filename","")
    if real(fp):
        by_hash.setdefault(hashlib.md5(fp.read_bytes()).hexdigest(),[]).append(p.get("filename"))

results=[]
for p in MANUAL:
    fn=p.get("filename","")
    fp=PDFS/fn
    if not real(fp):
        continue
    title=p.get("title","") or ""
    txt=page_text(fp)
    low=txt.lower()
    ttoks=toks(title)
    hit=ttoks & toks(txt[:3000])
    title_score = len(hit)/max(1,len(ttoks)) if ttoks else 0.0
    sn=surnames(p.get("authors",""))
    sn_hit={s for s in sn if s in low[:4000]}
    sn_score=len(sn_hit)/max(1,len(sn)) if sn else 0.0
    h=hashlib.md5(fp.read_bytes()).hexdigest()
    dup=len(by_hash[h])>1
    # verdict
    if dup:
        v="DUP"
    elif title and (title_score>=0.5 or (title_score>=0.34 and sn_score>=0.5)):
        v="MATCH"
    elif not title and sn_score>=0.5:
        v="MATCH(noTitle)"
    elif title_score>=0.34 or sn_score>=0.5:
        v="WEAK"
    else:
        v="MISMATCH"
    results.append(dict(fn=fn, verdict=v, ts=round(title_score,2), ss=round(sn_score,2),
                        title=title[:55], authors=(p.get("authors","")[:40]),
                        hit=sorted(hit)[:8], snhit=sorted(sn_hit),
                        pdftitle=re.sub(r"\s+"," ",txt[:120]).strip()))

order={"MISMATCH":0,"DUP":1,"WEAK":2,"MATCH(noTitle)":3,"MATCH":4}
results.sort(key=lambda r:(order.get(r["verdict"],9), r["ts"]))
for r in results:
    print(f"[{r['verdict']:>13}] ts={r['ts']:.2f} ss={r['ss']:.2f}  {r['fn'][:52]}")
    print(f"                want: {r['title']} | {r['authors']}")
    print(f"                pdf : {r['pdftitle'][:90]}")
    if r['hit']: print(f"                hit : {r['hit']}")
    print()

from collections import Counter
c=Counter(r["verdict"] for r in results)
print("SUMMARY:", dict(c))
(HERE/"_verify_report.json").write_text(json.dumps(results,indent=2))
