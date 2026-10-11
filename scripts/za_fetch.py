#!/usr/bin/env python3
"""Fetch the list of national Acts published on www.gov.za (step 1 of 2).

Steps (each cached under RAW, so re-runs only fetch what is missing):
  1. list   - crawl https://www.gov.za/documents/acts?page=N  -> RAW/list/page-N.html
  2. detail - fetch each Act's document page                  -> RAW/detail/<slug>.html
  An index of everything (incl. PDF URLs) is written to RAW/index.json.
  The PDFs themselves are downloaded, text-extracted and deleted by za_convert.py.

Usage: python za_fetch.py [--raw DIR] [--refresh-list] [--workers N]
"""
import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, unquote

import requests
from bs4 import BeautifulSoup

BASE = "https://www.gov.za"
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
DELAY = 1.0  # seconds between requests per worker

_local = threading.local()


def session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = UA
        _local.s = s
    return s


def get(url, binary=False, tries=5):
    for i in range(tries):
        try:
            r = session().get(url, timeout=120)
            time.sleep(DELAY)
            if r.status_code == 200:
                return r.content if binary else r.text
            if r.status_code == 404:
                return None
            print(f"HTTP {r.status_code} {url}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"ERR {e} {url}", file=sys.stderr)
        time.sleep(5 * (2 ** i))
    return None


def cached(path, url, binary=False):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            data = f.read()
        return data if binary else data.decode("utf-8", "replace")
    data = get(url, binary=binary)
    if data is None:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data if binary else data.encode("utf-8"))
    return data


def parse_list(html):
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for td in soup.select('td[headers="view-title-table-column"]'):
        a = td.select_one(".gazettetitle a")
        if not a:
            continue
        extra = [re.sub(r"\s+", " ", d.get_text(" ")).strip() for d in td.select(".gazette-result")]
        extra = [e for e in extra if e]
        tr = td.find_parent("tr")
        t = tr.select_one("time") if tr else None
        rows.append({
            "title": a.get_text(" ", strip=True),
            "url": urljoin(BASE, a["href"]),
            "meta": extra,
            "doc_date": t["datetime"][:10] if t and t.has_attr("datetime") else None,
        })
    last = 0
    for a in soup.select('a[href*="page="]'):
        m = re.search(r"page=(\d+)", a["href"])
        if m:
            last = max(last, int(m.group(1)))
    return rows, last


def slug_of(url):
    return unquote(url.rstrip("/").rsplit("/", 1)[-1])


def parse_detail(html):
    soup = BeautifulSoup(html, "lxml")
    pdfs = []
    for a in soup.select('a[href$=".pdf"], a[href$=".PDF"]'):
        href = urljoin(BASE, a["href"])
        if "/sites/default/files/" in href and href not in pdfs:
            pdfs.append(href)
    main = soup.select_one("main") or soup
    h1 = main.select_one("h1")
    num = main.select_one(".field--name-field-gcisdoc-act-number")
    body = main.select_one(".field--name-body")
    desc = re.sub(r"\s+", " ", body.get_text(" ")).strip() if body else ""
    return {"h1": h1.get_text(" ", strip=True) if h1 else None, "pdfs": pdfs, "desc": desc[:4000],
            "act_number": num.get_text(" ", strip=True) if num else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(os.path.dirname(__file__), "..", "..", "_raw", "za"))
    ap.add_argument("--refresh-list", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    raw = os.path.abspath(a.raw)
    os.makedirs(raw, exist_ok=True)

    # 1. listing (crawled in two sort orders, because the default date order is not
    #    stable across pages for documents sharing a date)
    rows = []
    for tag, q in (("", ""), ("title-", "&order=title&sort=asc")):
        page, last = 0, 0
        while page <= last:
            path = os.path.join(raw, "list", f"{tag}page-{page}.html")
            if a.refresh_list and os.path.exists(path):
                os.remove(path)
            html = cached(path, f"{BASE}/documents/acts?page={page}{q}")
            if html is None:
                print(f"listing {tag}page {page} failed", file=sys.stderr)
                page += 1
                continue
            r, l = parse_list(html)
            last = max(last, l)
            rows.extend(r)
            page += 1
    seen, uniq = set(), []
    for r in rows:
        if r["url"] not in seen:
            seen.add(r["url"])
            uniq.append(r)
    print(f"{len(uniq)} entries in listing")

    # 2+3. detail pages and PDFs
    def work(r):
        slug = slug_of(r["url"])
        html = cached(os.path.join(raw, "detail", slug + ".html"), r["url"])
        if html is None:
            r["error"] = "detail"
            return r
        r.update(parse_detail(html))
        r["slug"] = slug
        return r

    done = 0
    with ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(work, uniq):
            done += 1
            if done % 200 == 0:
                print(f"{done}/{len(uniq)}", flush=True)
    with open(os.path.join(raw, "index.json"), "w") as f:
        json.dump(uniq, f, indent=1, ensure_ascii=False)
    print("errors:", sum(1 for r in uniq if r.get("error")))


if __name__ == "__main__":
    main()
