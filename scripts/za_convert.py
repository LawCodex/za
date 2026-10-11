#!/usr/bin/env python3
"""Convert the gov.za Acts listed in RAW/index.json (built by za_fetch.py) to Markdown (step 2 of 2).

For every Act: download the PDF(s) attached on gov.za (cached under RAW/pdf only while
processing), extract the text page by page (cached as RAW/text/<slug>.json), delete the PDF,
keep only the English text (South African Acts are published in the Gazette with an
English and a second-language version on facing pages, or in parallel columns in older
Gazettes), strip Gazette page furniture and write acts/<year>/<year>-<no>-<slug>.md.

Usage: python za_convert.py [--raw DIR] [--out REPO_DIR] [--workers N] [--only SLUG ...]
"""
import argparse
import datetime
import io
import json
import os
import re
import sys
import threading
import time
import unicodedata
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import requests
from pypdf import PdfReader

UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
DELAY = 1.0
TODAY = datetime.date.today().isoformat()

EN = set("the and shall to which with any must this that for by be such are from has have been "
         "under not other may person minister section act terms regulation".split())
OTHER = set("die van en word wat vir met nie deur moet hierdie sal wet artikel ingevolge enige "
            "het zijn door de een wordt ook om op aan te ka ya le go na wa ga ke ho tsa kgotsa "
            "ngokwe noma uma lo kwa nga ku zi u wo kha ni hi ri swa leswi eka".split())

_local = threading.local()


def session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = UA
        _local.s = s
    return s


def download(url, tries=5):
    for i in range(tries):
        try:
            r = session().get(url, timeout=300)
            time.sleep(DELAY)
            if r.status_code == 200 and r.content[:5] == b"%PDF-":
                return r.content
            if r.status_code == 404:
                return None
            print(f"HTTP {r.status_code} {url}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"ERR {e} {url}", file=sys.stderr)
        time.sleep(5 * (2 ** i))
    return None


# ---------------------------------------------------------------- language scoring

WORD = re.compile(r"[A-Za-z’']+")


def lang_score(text):
    words = [w.lower() for w in WORD.findall(text)]
    if len(words) < 8:
        return 0.0, 0.0, len(words)
    n = len(words)
    en = sum(1 for w in words if w in EN) / n
    ot = sum(1 for w in words if w in OTHER) / n
    return en, ot, n


def is_english(text):
    en, ot, n = lang_score(text)
    return n >= 8 and en >= 0.06 and en > 1.5 * ot


# ---------------------------------------------------------------- PDF text extraction

def lines_from_items(items):
    """Rebuild text lines from (x, y, text) items."""
    items = sorted(items, key=lambda t: (-t[1], t[0]))
    lines, cur, cy = [], [], None
    for x, y, t in items:
        if cy is None or abs(y - cy) > 3:
            if cur:
                lines.append(" ".join(s for _, s in sorted(cur)))
            cur, cy = [], y
        cur.append((x, t))
    if cur:
        lines.append(" ".join(s for _, s in sorted(cur)))
    return "\n".join(re.sub(r"\s+", " ", l).strip() for l in lines)


def page_text(page):
    """Return (text, mode). mode: 'en', 'other', 'split' (English column of a bilingual page)."""
    try:
        full = page.extract_text() or ""
    except Exception:
        full = ""
    en, ot, n = lang_score(full)
    if n < 8:
        return full, "empty"
    if en >= 0.06 and ot < 0.03:
        return full, "en"
    if en < 0.03:
        return full, "other"
    # mixed page: try a split into two columns
    items = []

    def visit(text, cm, tm, fd, fs):
        if text and text.strip():
            x = cm[4] + tm[4] * cm[0]
            y = cm[5] + tm[5] * cm[3]
            items.append((x, y, text))
    try:
        page.extract_text(visitor_text=visit)
    except Exception:
        return full, "en" if is_english(full) else "other"
    if not items:
        return full, "en" if is_english(full) else "other"
    try:
        w = float(page.mediabox.width)
        x0 = float(page.mediabox.left)
    except Exception:
        w, x0 = 600.0, 0.0
    mid = x0 + w / 2
    left = [it for it in items if it[0] < mid]
    right = [it for it in items if it[0] >= mid]
    lt, rt = lines_from_items(left), lines_from_items(right)
    le, lo, ln = lang_score(lt)
    re_, ro, rn = lang_score(rt)
    if ln >= 8 and rn >= 8:
        if le > 1.5 * lo and ro > 1.5 * re_:
            return lt, "split"
        if re_ > 1.5 * ro and lo > 1.5 * le:
            return rt, "split"
    return full, "en" if is_english(full) else "other"


def extract(pdf_bytes):
    r = PdfReader(io.BytesIO(pdf_bytes))
    out = []
    for p in r.pages:
        try:
            t, m = page_text(p)
        except Exception as e:
            t, m = "", f"error:{e}"
        en, ot, n = lang_score(t)
        if m == "other" and ot < 0.02:
            m = "neutral"
        out.append({"text": t, "mode": m, "en": round(en, 3), "ot": round(ot, 3)})
    return out


# ---------------------------------------------------------------- cleaning

FURNITURE = [
    re.compile(r"^This gazette is also available free online at", re.I),
    re.compile(r"^(STAATSKOERANT|GOVERNMENT GAZETTE|UNION GAZETTE|PROVINCIAL GAZETTE)\b.*\d{4}", re.I),
    re.compile(r"^\d+\s+No\.\s*\d+\s+GOVERNMENT GAZETTE", re.I),
    re.compile(r"GOVERNMENT GAZETTE,?\s+\d{1,2}\s+\w+\s+\d{4}", re.I),
    re.compile(r"^No\.\s*\d+\s*\d*\s*$"),
    re.compile(r"^\d{1,4}$"),
    re.compile(r"^Printed by and obtainable from the Government Printer", re.I),
    re.compile(r"^(Contact Centre|Publications): Tel", re.I),
    re.compile(r"AIDS HELPLINE", re.I),
    re.compile(r"HELPLINE: AIDS", re.I),
    re.compile(r"^Prevention is the cure", re.I),
    re.compile(r"^curethe is Prevention", re.I),
    re.compile(r"^ISSN \d"),
    re.compile(r"^\d \d{6} \d{6}$"),
    re.compile(r"^Gedruk deur en verkrygbaar by", re.I),
    re.compile(r"^Hierdie koerant is ook gratis aanlyn", re.I),
]


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00ad", "").replace("\ufffd", "")
    s = s.replace("‘‘", "“").replace("’’", "”")
    s = re.sub(r"[ \t\u00a0]+", " ", s)
    return s.strip()


def running_header_patterns(pages):
    """Lines repeated at the top of many pages (e.g. 'Act No. 8 of 2018 Labour Relations Amendment Act, 2018')."""
    c = Counter()
    for p in pages:
        ls = [norm(l) for l in p.split("\n") if norm(l)]
        for l in set(ls[:3] + ls[-2:]):
            c[l] += 1
    k = max(3, len(pages) // 3)
    return {l for l, n in c.items() if n >= k and len(l) < 160}


def clean_lines(pages):
    rep = running_header_patterns(pages)
    out = []
    for p in pages:
        for l in p.split("\n"):
            l = norm(l)
            # drop capitals split from the rest of the word ("B E IT ENACTED", "P ARLIAMENT")
            l = re.sub(r"^([B-HJ-Z]) ([A-Z]+)\b", r"\1\2", l)
            if not l or l in rep:
                continue
            if any(rx.search(l) for rx in FURNITURE):
                continue
            # margin line numbers (5, 10, 15 ...) glued to the end of lines
            l = re.sub(r"\s+(5|[1-9]\d?[05])$", "", l) if re.search(r"[a-z,;:]\s+(5|[1-9]\d?[05])$", l) else l
            out.append(l)
    return out


# ---------------------------------------------------------------- Markdown structure

CHAPTER = re.compile(r"^(CHAPTER|Chapter)\s+([0-9]+[A-Z]?|[IVXLC]+)\.?$")
PART = re.compile(r"^(PART|Part)\s+([0-9]+[A-Z]?|[A-Z]|[IVXLC]+)\.?$")
SCHEDULE = re.compile(r"^(SCHEDULE|Schedule)(\s+[0-9A-Z]+)?\.?$|^(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH) SCHEDULE$")
SECTION = re.compile(r"^(\d{1,3}[A-Z]{0,2})\.\s+\S")
TOC = re.compile(r"^(ARRANGEMENT OF SECTIONS|TABLE OF CONTENTS|CONTENTS|INDEX)$", re.I)
NEWPARA = re.compile(r"^(\(\w{1,6}\)\s|\[|“|\"|\d{1,3}[A-Z]{0,2}\.\s|[•●▪-]\s)")


def md_escape(s):
    s = re.sub(r"^(\d+)\.(\s)", r"\1\\.\2", s)
    s = re.sub(r"^([#>+*])", r"\\\1", s)
    s = re.sub(r"^-(\s)", r"\\-\1", s)
    return s


def headingish(l):
    """A short line that looks like a heading (no final punctuation, starts with a capital)."""
    return (len(l) <= 110 and l[:1].isupper() and not l.endswith((".", ",", ";", ":", "—", "-", "–"))
            and not NEWPARA.match(l) and not re.search(r"\b(and|or|of|the|to|in|by|for)$", l))


def to_markdown(lines):
    md = []
    para = []

    def flush():
        if para:
            t = ""
            for seg in para:
                if t.endswith("-") and seg[:1].islower() and not t.endswith(" -"):
                    t = t[:-1] + seg
                else:
                    t = (t + " " + seg) if t else seg
            md.append(md_escape(t))
            md.append("")
            para.clear()

    # locate a table of contents: section numbers appear twice (TOC, then body); the body
    # starts at the first "1." that follows at least three higher-numbered TOC lines
    toc_start = toc_end = None
    nums = []
    for i, l in enumerate(lines):
        m = re.match(r"^(\d{1,3})[A-Z]{0,2}\.\s+\S", l)
        if m:
            nums.append((i, int(m.group(1))))
    seen_hi = 0
    for k, (i, n) in enumerate(nums):
        if n == 1 and seen_hi >= 3:
            j = nums[k + 1][0] if k + 1 < len(nums) else len(lines)
            if sum(len(x) for x in lines[i:j]) > 150:
                toc_end = i
                break
        if n >= 2:
            seen_hi += 1
    if toc_end is not None:
        first = nums[0][0]
        toc_start = first
        for j in range(max(0, first - 40), first):
            if TOC.match(lines[j]):
                toc_start = j
                break
        else:
            while toc_start - 1 >= 0 and first - toc_start < 4 and (CHAPTER.match(lines[toc_start - 1])
                                                                    or PART.match(lines[toc_start - 1])
                                                                    or headingish(lines[toc_start - 1])):
                toc_start -= 1
        k = toc_end
        while k - 1 > toc_start and toc_end - k < 6 and (headingish(lines[k - 1]) or CHAPTER.match(lines[k - 1])
                                                       or PART.match(lines[k - 1])):
            k -= 1
        toc_end = k
        if toc_end - toc_start < 3:
            toc_start = toc_end = None

    i = 0
    while i < len(lines):
        l = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if toc_start is not None and toc_start <= i < toc_end:
            if i == toc_start and TOC.match(l):
                flush()
                md += [f"**{l}**", ""]
            elif i == toc_start:
                flush()
                md.append(md_escape(l) + "  ")
            else:
                md.append(md_escape(l) + "  ")
                if i == toc_end - 1:
                    md.append("")
            i += 1
            continue
        m = CHAPTER.match(l)
        if m:
            flush()
            title = ""
            if nxt and headingish(nxt) and not SECTION.match(nxt) and not PART.match(nxt):
                title, i = nxt, i + 1
            md += [f"## {l}" + (f" — {title}" if title else ""), ""]
            i += 1
            continue
        m = PART.match(l)
        if m:
            flush()
            title = ""
            if nxt and headingish(nxt) and not SECTION.match(nxt):
                title, i = nxt, i + 1
            md += [f"### {l}" + (f" — {title}" if title else ""), ""]
            i += 1
            continue
        if SCHEDULE.match(l):
            flush()
            md += [f"## {l}", ""]
            i += 1
            continue
        # section heading line directly followed by "n. text"
        if headingish(l) and SECTION.match(nxt) and not para:
            flush()
            num = SECTION.match(nxt).group(1)
            md += [f"#### {num}. {l}", ""]
            i += 1
            continue
        if headingish(l) and SECTION.match(nxt) and para:
            head = " ".join(para + [l])
            if len(head) <= 300 and head[:1].isupper() and not para[-1].endswith((".", ";", ":", "—", "]")):
                para.clear()
            else:
                flush()
                head = l
            flush()
            num = SECTION.match(nxt).group(1)
            md += [f"#### {num}. {head}", ""]
            i += 1
            continue
        prev = para[-1] if para else ""
        if NEWPARA.match(l) and re.match(r"^\(\w{1,6}\)", l) and re.search(
                r"\b(sub-?paragraphs?|paragraphs?|sub-?sections?|sections?|items?|sub-?items?|sub-?regulations?|regulations?|and|or|of|in|to|under|with|by)$", prev):
            para.append(l)
            i += 1
            continue
        if NEWPARA.match(l) or re.match(r"^BE IT (FURTHER |THEREFORE )?ENACTED", l, re.I) or l in ("ACT", "PREAMBLE"):
            flush()
        para.append(l)
        if l in ("ACT", "PREAMBLE") or l.endswith((".", ";", ":", "—", "]")) and len(l) < 60:
            flush()
        i += 1
    flush()
    return md


# ---------------------------------------------------------------- metadata

def slugify(s, maxlen=80):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    if len(s) > maxlen:
        s = s[:maxlen].rsplit("-", 1)[0]
    return s


REPEALED = re.compile(r"\s*[\[(]\s*repealed\s*[\])]", re.I)


def clean_title(t):
    t = REPEALED.sub("", t)
    t = re.sub(r"\s*\((English|Afrikaans|isiZulu|isiXhosa|Sepedi|Sesotho|Setswana|siSwati|Tshivenda|Xitsonga|isiNdebele)"
               r"(\s*/\s*[A-Za-z]+)*\)", "", t, flags=re.I)
    t = re.sub(r"\s*\(?\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w* \d{4}\)?\s*$", "", t)
    return re.sub(r"\s+", " ", t).strip()


def short_name(title):
    """Title without the trailing 'NN of YYYY' (used for file names)."""
    return re.sub(r"\s*,?\s*(\(?Act\s+)?(No\.?\s*)?(of\s+)?\d+[A-Z]?\s+of\s+\d{4}\)?\s*$", "", title, flags=re.I).strip()


def act_no(r):
    for s in [r.get("act_number") or ""] + r.get("meta", []) + [r.get("title", "")]:
        m = re.search(r"\b(\d+[A-Z]?)\s+of\s+(\d{4})\b", s)
        if m:
            return m.group(1), int(m.group(2))
    return None, None


def frontmatter(d):
    out = ["---"]
    for k, v in d.items():
        if v is None or v == "":
            continue
        if isinstance(v, (int, float)):
            out.append(f"{k}: {v}")
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)) or k in ("type", "jurisdiction", "language", "status"):
            out.append(f"{k}: {v}")
        else:
            out.append(f"{k}: " + json.dumps(str(v), ensure_ascii=False))
    out.append("---")
    return "\n".join(out)


# ---------------------------------------------------------------- main

def process(r, raw, outdir):
    slug = r["slug"]
    tpath = os.path.join(raw, "text", slug + ".json")
    if os.path.exists(tpath):
        with open(tpath) as f:
            docs = json.load(f)
    else:
        docs = []
        for u in r.get("pdfs", []):
            data = download(u)
            if data is None:
                return {"slug": slug, "error": "download"}
            try:
                pages = extract(data)
            except Exception as e:
                return {"slug": slug, "error": f"pdf:{e}"}
            docs.append({"url": u, "pages": pages})
        os.makedirs(os.path.dirname(tpath), exist_ok=True)
        with open(tpath, "w") as f:
            json.dump(docs, f, ensure_ascii=False)
    return {"slug": slug, "docs": docs}


def build(r, docs, outdir, used):
    no, year = act_no(r)
    title = clean_title(r.get("h1") or r["title"])
    if year is None:
        return None, "no-number"
    if REPEALED.search(r.get("h1") or r["title"]):
        return None, "repealed"
    pages = []
    modes = Counter()
    for d in docs:
        ps = d["pages"]
        for p in ps:
            modes[p["mode"]] += 1
        # parity of English pages in Gazettes that alternate English / other language pages
        en_par = Counter(k % 2 for k, p in enumerate(ps) if p["mode"] == "en")
        ot_par = Counter(k % 2 for k, p in enumerate(ps) if p["mode"] == "other")
        alternating = bool(ot_par) and sum(ot_par.values()) >= 2
        good_par = en_par.most_common(1)[0][0] if en_par else None
        for k, p in enumerate(ps):
            if p["mode"] in ("en", "split"):
                pages.append(p["text"])
            elif p["mode"] in ("neutral", "empty") and p["text"].strip():
                if not alternating or k % 2 == good_par:
                    pages.append(p["text"])
    if not pages or sum(len(p) for p in pages) < 200:
        return None, "no-english-text"
    lines = clean_lines(pages)
    # drop the Gazette cover/notice that precedes the Act itself
    for k, l in enumerate(lines[:80]):
        if l in ("ACT", "ACT.") or l.startswith("GENERAL EXPLANATORY NOTE"):
            lines = lines[k:]
            break
    body = to_markdown(lines)
    yd = os.path.join(outdir, "acts", str(year))
    base = f"{year}-{no.lower()}-{slugify(short_name(title)) or 'act'}"[:100].rstrip("-")
    fn = base + ".md"
    key = (year, no.lower())
    if key in used:
        return None, "duplicate"
    used.add(key)
    fm = {
        "title": title,
        "identifier": f"Act {no} of {year}",
        "type": "act",
        "jurisdiction": "za",
        "language": "en",
        "date": r.get("doc_date"),
        "version": "as enacted (Government Gazette text)",
        "status": "unknown",
        "source": r["url"],
        "source_pdf": " ".join(d["url"] for d in docs),
        "gazette": next((m for m in r.get("meta", []) if re.match(r"^G\s*\d+", m)), None),
        "text_quality": "ocr-bilingual-columns" if modes["split"] >= max(3, sum(modes.values()) // 3) else None,
        "licence": "Public domain: no copyright in official legislative texts (Copyright Act 98 of 1978, s. 12(8)(a)); gov.za content reusable for non-commercial purposes",
        "retrieved": TODAY,
    }
    text = frontmatter(fm) + f"\n\n# {title}\n\n" + "\n".join(body).rstrip() + "\n"
    text = re.sub(r"\n{3,}", "\n\n", text)
    os.makedirs(yd, exist_ok=True)
    with open(os.path.join(yd, fn), "w", encoding="utf-8") as f:
        f.write(text)
    return os.path.join("acts", str(year), fn), "ok"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(here, "..", "..", "_raw", "za"))
    ap.add_argument("--out", default=os.path.join(here, ".."))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    raw, outdir = os.path.abspath(a.raw), os.path.abspath(a.out)
    with open(os.path.join(raw, "index.json")) as f:
        index = [r for r in json.load(f) if r.get("slug")]
    if a.only:
        index = [r for r in index if r["slug"] in a.only]
    if a.limit:
        index = index[:a.limit]
    # prefer entries whose title mentions English, then the most recent posting
    index.sort(key=lambda r: (0 if "english" in r["title"].lower() else 1, r.get("doc_date") or ""), reverse=False)
    results = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for k, res in enumerate(ex.map(partial(process, raw=raw, outdir=outdir), index, chunksize=1)):
            results[res["slug"]] = res
            if (k + 1) % 100 == 0:
                print(f"extracted {k + 1}/{len(index)}", flush=True)
    used, report = set(), []
    for r in index:
        res = results[r["slug"]]
        if "error" in res:
            report.append({"slug": r["slug"], "title": r["title"], "status": res["error"], "url": r["url"]})
            continue
        path, st = build(r, res["docs"], outdir, used)
        report.append({"slug": r["slug"], "title": r["title"], "status": st, "path": path, "url": r["url"],
                       "act": "%s of %s" % act_no(r)})
    with open(os.path.join(raw, "report.json"), "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print(Counter(x["status"] for x in report))


if __name__ == "__main__":
    main()
