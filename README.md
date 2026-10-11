# South Africa legislation — LawCodex

The Constitution of the Republic of South Africa, 1996 and the national Acts of Parliament
published on the South African Government website (www.gov.za), as plain Markdown, one file per
Act. Part of [LawCodex](https://github.com/LawCodex).

**Jurisdiction:** South Africa (`za`) · **Language:** English · **Generated:** 2026-10-12

> **Important — these are mostly *as-enacted* texts, not consolidations.** The only openly
> reusable, bulk-accessible source of South African Acts is gov.za, which publishes each Act as it
> appeared in the *Government Gazette* when it was assented to (amending Acts are separate
> files). Consolidated ("as amended") texts of the whole statute book exist only on the
> AfricanLII / Laws.Africa platforms (lawlibrary.org.za, SAFLII), whose terms forbid scraping
> and bulk download (see *Sources not used*). The Constitution, by contrast, **is** the
> consolidated text published by the Department of Justice. Always check an authoritative
> source before relying on a text.

## What is covered

| Category | Directory | Files |
|---|---|---:|
| Constitution of the Republic of South Africa, 1996 (consolidated) | `constitution/` | 1 |
| Acts of Parliament (as enacted), by year of enactment | `acts/<year>/` | 2,804 |

Acts span 1910–2026 (Union of South Africa 1910 onwards: principal Acts, amendment Acts,
appropriation/revenue Acts and private Acts). Per decade:

| Decade | Files |
|---|---:|
| 1910s | 9 |
| 1920s | 23 |
| 1930s | 31 |
| 1940s | 36 |
| 1950s | 83 |
| 1960s | 188 |
| 1970s | 314 |
| 1980s | 463 |
| 1990s | 766 |
| 2000s | 486 |
| 2010s | 264 |
| 2020s | 141 |

Every file has YAML front matter: `title`, `identifier` (`Act <no> of <year>`), `type`,
`jurisdiction`, `language`, `date` (gov.za document date — usually the Gazette/publication
date), `version`, `status`, `source` (gov.za page), `source_pdf`, `gazette` (Government Gazette
number when known), `text_quality` (set when the text comes from an OCR'd scan), `licence`,
`retrieved`.

`status` is `unknown` for Acts: gov.za flags some repealed Acts in their titles (`[Repealed]`),
and those **247 entries were left out** (the scope is legislation in force), but gov.za
does not systematically track repeals, so some files here are for Acts that have since been
repealed or wholly superseded, and amendment Acts whose provisions have long been merged into
their principal Act are included as published.

## What is NOT covered (gaps)

- **Consolidated versions of Acts** (see the note above). Each amendment is a separate file
  under the year of the amending Act.
- **Acts not on gov.za.** gov.za's collection is extensive but not complete, especially for
  1910–1980. Some important older Acts in force are missing or only present as amending Acts.
- **Listed on gov.za but not converted (12 entries):** no PDF attached (6: Revenue Laws
  Amendment Act 12 of 2024, Pension Funds Amendment Act 31 of 2024, Eskom Debt Relief Amendment
  Act 5 of 2024, Administration of Estates Act 66 of 1965, Protection of Businesses Act 99 of 1978,
  and the interim Constitution, Act 200 of 1993); image-only PDF without a text layer (3: Firearms
  Control Act 60 of 2000, Second Customs and Excise Amendment Act 64 of 1974, a 1920 private Act);
  no Act number on gov.za (3: Public Service Act, 1994 [Proclamation 103 of 1994], Government
  Employees Pension Law [1996 Proclamation], and a duplicate Constitution Thirteenth Amendment Act
  entry).
- **Second-language texts.** South African Acts are published in English and one other official
  language (the signed text alternates). Only the English text is kept; for older Gazettes
  printed in two parallel columns, the English column is selected automatically.
- **Older texts are OCR.** Most pre-1990s PDFs on gov.za are scans with an OCR text layer; their
  text contains OCR errors and occasional omissions (flagged with `text_quality`). The 1910s–1920s
  Gazettes were printed in parallel English/Dutch columns and some Dutch text may leak through.
- Provincial legislation, municipal by-laws, regulations, proclamations, Government Notices,
  Bills, and the interim Constitution of 1993 (Act 200 of 1993; repealed).
- The Constitution file reproduces the DoJ&CD consolidation, which incorporates amendments up to
  the Constitution Seventeenth Amendment Act of 2012; the **Constitution Eighteenth Amendment Act,
  2023** (South African Sign Language as a 12th official language, s. 6), brought into operation
  by Proclamation R. 321 of 2026, is not yet reflected in that source text.

## Sources

- **Constitution:** Department of Justice and Constitutional Development (DoJ&CD),
  <https://www.justice.gov.za/constitution/> — Preamble and Chapters 1–14 from the HTML pages
  (`chp01.html` … `chp14.html`), Schedules 1–7 and Annexures A–D from the official PDF
  `SAConstitution-web-eng-s-a-combined.pdf`.
- **Acts:** South African Government, <https://www.gov.za/documents/acts> (Government
  Communication and Information System, GCIS). The listing (both sort orders, ~103 pages), each
  Act's document page and its attached Gazette PDF were fetched with a 1 s delay per request and
  at most 4 parallel requests; gov.za's robots.txt allows these paths and sets no crawl-delay.

### Sources evaluated but not used

| Source | Finding |
|---|---|
| [lawlibrary.org.za](https://lawlibrary.org.za) (AfricanLII / Laws.Africa "Peachjam") | Best source (consolidated, point-in-time, Akoma Ntoso). robots.txt allows `/akn/` for generic agents (Crawl-delay 5) but disallows ClaudeBot/anthropic-ai and sets `Content-Signal: ai-train=no, ai-input=no`; the [Terms of Use](https://lawlibrary.org.za/terms-of-use/) state *"Scraping and bulk downloading from this Website is strictly prohibited … Please email us if you would like to access our data in bulk"*; content licence is **CC BY-NC 4.0**. Not crawled. Bulk access would need written permission (support@lawlibrary.org.za). |
| [api.laws.africa/v3](https://api.laws.africa/v3/) | Requires a (free) personal API token; robots.txt `Disallow: /`. No account was created. |
| open.lawlibrary.org.za | Not reachable (connection failure) during this build. |
| [SAFLII](https://www.saflii.org) | Every request, including robots.txt, answered with a Cloudflare JavaScript challenge; not circumvented. |
| Laws.Africa "Pocket Law" offline app (GitHub releases) | Contains a WARC of the lawlibrary site; using it to bulk-extract content would sidestep the no-bulk-download terms, so not used. |
| justice.gov.za consolidated Act PDFs | Marked "Copyright Juta & Company Limited and/or Government Printing Works"; editorial consolidations, not used. |

## Licence / copyright

- **Legislation itself is not protected by copyright in South Africa:** section 12(8)(a) of the
  Copyright Act 98 of 1978 provides that *"no copyright shall subsist in official texts of a
  legislative, administrative or legal nature, or in official translations of such texts"*.
- gov.za [terms of use](https://www.gov.za/terms-and-conditions-use-0) allow users to *"view,
  copy, download to a local drive, print and distribute the content of this website … for
  non-commercial informational or reference purposes"*; commercial reuse of gov.za content needs
  GCIS permission. This repository is non-commercial; the Act texts are reproduced unaltered apart
  from text extraction and Markdown formatting.
- The Constitution pages on justice.gov.za carry "Copyright © DoJ&CD"; the constitutional text
  itself is an official legislative text under s. 12(8)(a).
- These are **not** official versions. The authoritative texts are those published in the
  *Government Gazette* (Government Printing Works).

## Structure

```
constitution/constitution-of-the-republic-of-south-africa-1996.md
acts/<year>/<year>-<number>-<slug>.md      e.g. acts/2008/2008-71-companies.md
scripts/                                   fetch + convert code
```

Inside an Act: `## CHAPTER …`, `### Part …`, `#### <n>. <section heading>`; tables of contents
are kept as plain line lists; schedules start with `## SCHEDULE …`. Headings are detected
heuristically from the PDF text layer, so structure is approximate (especially for OCR'd texts).

## Regenerating

```sh
pip install -r scripts/requirements.txt
python scripts/za_constitution.py          # Constitution (cache: ../_raw/za/const)
python scripts/za_fetch.py                 # gov.za listing + Act pages -> ../_raw/za/index.json
python scripts/za_convert.py               # download PDFs, extract English text, write acts/
```

`za_convert.py` caches the extracted page texts in `../_raw/za/text/` and never stores the PDFs;
delete the cache to force re-download.
