#!/usr/bin/env python3
"""Build constitution/constitution-of-the-republic-of-south-africa-1996.md.

Source: Department of Justice and Constitutional Development (DoJ&CD),
https://www.justice.gov.za/constitution/ - the Preamble and Chapters 1-14 from the HTML
pages (chp01.html ... chp14.html), the Schedules and Annexures from the official
"Schedules & Annexures" PDF (SAConstitution-web-eng-s-a-combined.pdf).

Usage: python za_constitution.py [--raw DIR] [--out REPO_DIR]
"""
import argparse
import datetime
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup, NavigableString
from pypdf import PdfReader

BASE = "https://www.justice.gov.za/constitution/"
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
PAGES = ["preamble"] + [f"chp{i:02d}" for i in range(1, 15)]
SCHED_PDF = "SAConstitution-web-eng-s-a-combined.pdf"


def fetch(raw, name, binary=False):
    p = os.path.join(raw, name)
    if not os.path.exists(p):
        r = requests.get(BASE + name, headers={"User-Agent": UA}, timeout=120)
        r.raise_for_status()
        with open(p, "wb") as f:
            f.write(r.content)
        time.sleep(1)
    with open(p, "rb") as f:
        d = f.read()
    return d if binary else d.decode("utf-8", "replace")


def clean(s):
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return s.strip()


def text_of(el):
    parts = []
    for d in el.descendants:
        if isinstance(d, NavigableString):
            parts.append(str(d).replace("\n", " "))
        elif d.name == "br":
            parts.append("\n")
    return clean("".join(parts))


def esc(line):
    # keep "9. (1) ..." from being rendered as a Markdown ordered list
    line = re.sub(r"^(\d+)\.(\s)", r"\1\\.\2", line)
    line = re.sub(r"^([-+*#>])", r"\\\1", line)
    return line


def para(t):
    return "  \n".join(esc(l) for l in t.split("\n"))


def html_part(html):
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.select_one("h1.page-header")
    title = clean(h1.find(string=True, recursive=False) or h1.get_text(" "))
    sub = h1.select_one(".small")
    sub = clean(sub.get_text(" ")) if sub else ""
    date = soup.select_one("p.TDate")
    out = []
    blocks = []
    for el in soup.find_all(["p", "h2", "h3", "h4", "table"]):
        if el is date:
            break
        if el.find_parent(["nav", "ol", "table"]) and el.name != "table":
            continue
        if el.find_parent("div", class_="container") is None:
            continue
        if el.name in ("p", "h2", "h3", "h4") and el.find_parent("table"):
            continue
        blocks.append(el)
    i = 0
    while i < len(blocks):
        el = blocks[i]
        if el.name == "table":
            rows = []
            for tr in el.find_all("tr"):
                cells = [text_of(c).replace("\n", " ").replace("|", "\\|") for c in tr.find_all(["td", "th"])]
                rows.append(cells)
            if rows:
                w = max(len(r) for r in rows)
                rows = [r + [""] * (w - len(r)) for r in rows]
                out.append("| " + " | ".join(rows[0]) + " |")
                out.append("|" + "---|" * w)
                out.extend("| " + " | ".join(r) + " |" for r in rows[1:])
                out.append("")
            i += 1
            continue
        t = text_of(el)
        if not t or el.find_parent("div", class_="carousel") or "leading the reading" in t:
            i += 1
            continue
        if el.name in ("h2", "h3", "h4"):
            out += [f"### {t.replace(chr(10), ' ')}", ""]
        elif el.name == "p" and "subscript" not in (el.get("class") or []) and \
                el.find("strong") and clean(el.find("strong").get_text(" ")) == t.replace("\n", " "):
            # section heading; take the number from the next paragraph
            num = ""
            if i + 1 < len(blocks):
                m = re.match(r"\s*(\d+[A-Z]?)\.\s", text_of(blocks[i + 1]))
                if m:
                    num = m.group(1) + ". "
            out += [f"#### {num}{t.replace(chr(10), ' ')}", ""]
        else:
            out += [para(t), ""]
        i += 1
    when = clean(date.get_text(" ")) if date else ""
    return title, sub, out, when


SCHED_HEAD = re.compile(r"^(SCHEDULE \d+[A-Z]?|ANNEXURE [A-D])\s*$")
SCHED_TITLES = {
    "SCHEDULE 1": "National Flag",
    "SCHEDULE 1A": "Geographical Areas of Provinces",
    "SCHEDULE 2": "Oaths and Solemn Affirmations",
    "SCHEDULE 3": "Election Procedures",
    "SCHEDULE 4": "Functional Areas of Concurrent National and Provincial Legislative Competence",
    "SCHEDULE 5": "Functional Areas of Exclusive Provincial Legislative Competence",
    "SCHEDULE 6": "Transitional Arrangements",
    "ANNEXURE A": "Amendments to Schedule 2 to the previous Constitution",
    "ANNEXURE B": "Government of National Unity: National Sphere",
    "ANNEXURE C": "Government of National Unity: Provincial Sphere",
    "ANNEXURE D": "Public Administration and Security Services: Amendments to Sections of the Previous Constitution",
    "SCHEDULE 6A": "",
    "SCHEDULE 6B": "",
    "SCHEDULE 7": "Laws Repealed",
}
FOOTER = re.compile(r"^(Schedule \d+[A-Z]?|Annexure [A-D])\b")


def schedules(pdf_path):
    r = PdfReader(pdf_path)
    lines = []
    for pg in r.pages:
        pl = [l.replace("\t", " ").rstrip() for l in (pg.extract_text() or "").split("\n") if l.strip()]
        if pl and re.fullmatch(r"\s*\d{1,3}\s*", pl[0]):
            pl = pl[1:]
        if len(pl) >= 2 and FOOTER.match(pl[-2].strip()) and ":" in pl[-2] and pl[-2].strip().endswith("and"):
            pl = pl[:-2]
        elif pl and FOOTER.match(pl[-1].strip()):
            pl = pl[:-1]
        lines.extend(pl)
    out, buf = [], []

    def flush():
        if buf:
            t = clean(" ".join(buf))
            out.append(("- " + t[1:].strip()) if t.startswith("•") else para(t))
            out.append("")
            buf.clear()

    i, skip_title = 0, None
    while i < len(lines):
        l = lines[i].strip()
        m = SCHED_HEAD.match(l)
        if m:
            flush()
            key = m.group(1)
            title = SCHED_TITLES.get(key, "")
            out += [f"## {key.title()}" + (f" — {title}" if title else ""), ""]
            i += 1
            # skip the (small-caps) title lines that repeat the heading
            if title:
                acc = ""
                while i < len(lines) and len(acc) < len(title) and not lines[i].strip().startswith("["):
                    nxt = re.sub(r"\s+", " ", lines[i].strip()).lower()
                    if not title.lower().startswith((acc + " " + nxt).strip()):
                        break
                    acc = (acc + " " + nxt).strip()
                    i += 1
            continue
        if re.fullmatch(r"part [a-z]", l, re.I):
            flush()
            out += [f"### Part {l[-1].upper()}", ""]
            i += 1
            continue
        # bullet items may be merged on one line ("• A • B")
        if "•" in l:
            flush()
            items = [x.strip() for x in l.split("•") if x.strip()]
            if not l.startswith("•") and items:
                buf.append(items.pop(0))
                flush()
            for k, it in enumerate(items):
                buf.append("• " + it)
                if k < len(items) - 1:
                    flush()
            i += 1
            continue
        starts = re.match(r"^(Act No\. |\(\w{1,5}\)|\d+[A-Z]?\.\s|\[|Item \d)", l)
        if starts and buf:
            flush()
        buf.append(l)
        if l.endswith((".", ";", ":", "—", "]", "”")) or (len(l) < 55 and not buf[0].startswith("•")
                                                        and not l.endswith((",", "-", " and", " or", " the", " of"))):
            flush()
        i += 1
    flush()
    return out


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--raw", default=os.path.join(here, "..", "..", "_raw", "za", "const"))
    ap.add_argument("--out", default=os.path.join(here, ".."))
    a = ap.parse_args()
    os.makedirs(a.raw, exist_ok=True)
    body, when = [], ""
    for name in PAGES:
        title, sub, out, w = html_part(fetch(a.raw, name + ".html"))
        m = re.search(r"(\d{1,2}) (\w+),? (\d{4})", w)
        if m:
            d = datetime.datetime.strptime(" ".join(m.groups()), "%d %B %Y").date().isoformat()
            when = max(when, d)
        if name == "preamble":
            body += ["## Preamble", ""] + out
        else:
            n = int(name[3:])
            body += [f"## Chapter {n} — {title}", ""] + out
    fetch(a.raw, SCHED_PDF, binary=True)
    body += schedules(os.path.join(a.raw, SCHED_PDF))
    asat = when
    fm = f'''---
title: "Constitution of the Republic of South Africa, 1996"
identifier: "Act 108 of 1996"
type: constitution
jurisdiction: za
language: en
date: 1996-12-18
commenced: 1997-02-04
last_amended: {asat}
status: in_force
source: "https://www.justice.gov.za/constitution/index.html"
source_schedules: "{BASE}{SCHED_PDF}"
publisher: "Department of Justice and Constitutional Development"
licence: "Public domain: no copyright in official legislative texts (Copyright Act 98 of 1978, s. 12(8)(a))"
retrieved: {datetime.date.today().isoformat()}
note: "DoJ&CD consolidated text incorporating amendments up to the Constitution Seventeenth Amendment Act of 2012. The Constitution Eighteenth Amendment Act, 2023 (Act 3 of 2023; South African Sign Language as an official language, s. 6), brought into operation by Proclamation R. 321 of 2026 (Government Gazette 54901, 26 June 2026), is not yet incorporated in this source text."
---

# Constitution of the Republic of South Africa, 1996

(Manner of reference to the Act, previously "Constitution of the Republic of South Africa, Act 108 of 1996", substituted by s. 1 (1) of the Citation of Constitutional Laws, 2005 (Act No. 5 of 2005))

[Assented to 10 December 1996] [Date of promulgation: 18 December 1996] [Date of commencement: 4 February 1997 (unless otherwise indicated — see also s. 243(5))]

(English text signed by the President)

'''
    text = fm + "\n".join(body).rstrip() + "\n"
    text = re.sub(r"\n{3,}", "\n\n", text)
    od = os.path.join(a.out, "constitution")
    os.makedirs(od, exist_ok=True)
    p = os.path.join(od, "constitution-of-the-republic-of-south-africa-1996.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    print(p, len(text))


if __name__ == "__main__":
    main()
