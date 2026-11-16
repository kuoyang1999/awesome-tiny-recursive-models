#!/usr/bin/env python3
"""List new arXiv and OpenReview candidates that are not yet in the catalog.

    python scripts/find_new.py > candidates.md                  # window starts at data/coverage.yaml
    python scripts/find_new.py --since 2026-11-01 --json candidates.json > candidates.md

This is a maintainer aid, not an inclusion rule: every candidate still needs a human read of the
abstract against CONTRIBUTING.md before it is added. By default the window starts three days before
`searched_through` in data/coverage.yaml (the end of the last complete manual search), so a missed
week is searched again instead of being skipped.

The report says what was searched. A failed or rate-limited query is listed as such and makes the
exit status 2, so an empty list is never mistaken for "no new papers". An OpenReview term whose ranked
matches outrun the pages read is listed as capped (reported, not fatal).
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time
import xml.etree.ElementTree as ET

import requests
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ATOM = "{http://www.w3.org/2005/Atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
UA = {"User-Agent": "awesome-tiny-recursive-models/find_new (+https://github.com/kuoyang1999/awesome-tiny-recursive-models)"}
ARXIV_QUERIES = [
    'abs:"tiny recursive" OR ti:"tiny recursive"',
    'abs:"tiny recursion" OR ti:"tiny recursion"',
    'abs:"hierarchical reasoning model" OR abs:"hierarchical reasoning models"',
    'abs:"recursive reasoning model" OR abs:"recursive reasoning models"',
    'abs:"recursive reasoning" AND (abs:tiny OR abs:small OR abs:latent OR abs:sudoku OR abs:ARC)',
    'abs:"recurrent reasoning model" OR abs:"recurrent reasoning models"',
    'abs:TRM AND (abs:recursive OR abs:recursion)',
    'abs:HRM AND abs:hierarchical AND abs:reasoning',
    'abs:"Sudoku-Extreme" OR abs:"Maze-Hard"',
    'abs:"ARC-AGI" AND (abs:recursive OR abs:recurrent OR abs:looped OR abs:tiny)',
    'abs:"looped transformer" OR abs:"looped transformers"',
    'abs:"looped language model" OR abs:"looped language models"',
    'abs:"recurrent depth" OR abs:"recurrent-depth" OR abs:"depth-recurrent"',
    'abs:"weight-tied" AND (abs:reasoning OR abs:depth OR abs:recurrence)',
    'abs:"fixed-point" AND abs:reasoning AND (abs:transformer OR abs:recurrent OR abs:looped)',
    # added 2026-11-16 from the knowledge base's query families: in the 2026-10-09..2026-11-12 manual pass,
    # 33 of the 98 new candidates were found only by those families, not by the queries above
    'abs:"depth recurrent" OR abs:"layer recurrence" OR abs:"layer-recurrent" OR abs:"recurrent layers"',
    'abs:"universal transformer" AND (abs:reasoning OR abs:recurrence OR abs:depth)',
    'abs:"latent reasoning" AND (abs:loop OR abs:looped OR abs:recurrent OR abs:recursive OR abs:iteration)',
    'abs:"test-time compute" AND (abs:recurrent OR abs:looped OR abs:latent)',
    'abs:"adaptive computation" AND (abs:halting OR abs:ponder)',
    'abs:"deep equilibrium" AND abs:reasoning',
    'abs:attractor AND abs:reasoning AND (abs:neural OR abs:transformer)',
    'abs:"equilibrium reasoners" OR abs:"equilibrium reasoning"',
    'abs:"ARC-AGI-2" OR abs:"ARC-AGI-3"',
    'abs:sudoku AND (abs:recurrent OR abs:recursive OR abs:looped) AND abs:reasoning',
    'ti:survey AND (abs:looped OR abs:"recurrent depth" OR abs:recursive) AND abs:reasoning',
    '(ti:survey OR ti:review) AND (abs:"tiny recursive" OR abs:"hierarchical reasoning model" OR abs:"recursive reasoning")',
]
OPENREVIEW_TERMS = ["tiny recursive", "recursive reasoning model", "recurrent reasoning model",
                    "hierarchical reasoning model", "Sudoku-Extreme", "Maze-Hard", "looped transformer",
                    "recurrent depth"]
# used only when arXiv fails: plain phrases for OpenAlex, which indexes arXiv with a lag of days
FALLBACK_PHRASES = ["tiny recursive model", "hierarchical reasoning model", "recursive reasoning model",
                    "Sudoku-Extreme", "Maze-Hard", "looped transformer"]
OPENREVIEW_LIMIT = 1000   # notes per search request (the API maximum)
OPENREVIEW_PAGES = 4      # pages per term via `offset`, i.e. up to 4,000 ranked matches
ARXIV_PAGE = 200


def norm(t):
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def known():
    papers = []
    for name in ("papers.yaml", "extra_papers.yaml"):
        if (ROOT / "data" / name).exists():
            papers += yaml.safe_load(open(ROOT / "data" / name)) or []
    keys, titles = set(), set()
    for p in papers:
        titles.add(norm(p["title"]))
        urls = list((p.get("links") or {}).values()) + [v.get("url", "") for v in p.get("versions") or []]
        for u in urls:
            keys.update(re.findall(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", u or ""))
            keys.update(re.findall(r"openreview\.net/forum\?id=([\w-]+)", u or ""))
    return keys, titles


def reported(path):
    """arXiv ids and OpenReview forums already listed in earlier candidate issues."""
    if not path or not pathlib.Path(path).exists():
        return set()
    text = pathlib.Path(path).read_text()
    return set(re.findall(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", text)) | set(
        re.findall(r"openreview\.net/forum\?id=([\w-]+)", text))


def get(url, params, log, label, tries=4):
    """GET with backoff; returns a Response or None (and records why)."""
    last = "no response"
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=90, headers=UA)
        except requests.RequestException as e:
            last = type(e).__name__
            time.sleep(15 * (attempt + 1))
            continue
        if r.status_code == 200:
            return r
        last = f"HTTP {r.status_code}"
        if r.status_code in (403, 404):
            break
        retry = r.headers.get("Retry-After", "")
        time.sleep(min(int(retry) if retry.isdigit() else 30 * (attempt + 1), 180))
    log.append({"source": label, "status": "failed", "detail": last})
    return None


def arxiv(since, until, log):
    out = {}
    window = f"submittedDate:[{since.replace('-', '')}0000 TO {until.replace('-', '')}2359]"
    for q in ARXIV_QUERIES:
        label = f"arXiv: {q}"
        start, total, ok = 0, None, True
        while True:
            r = get("https://export.arxiv.org/api/query", {
                "search_query": f"({q}) AND {window}", "start": start, "max_results": ARXIV_PAGE,
                "sortBy": "submittedDate", "sortOrder": "descending"}, log, label)
            time.sleep(3.5)  # arXiv API terms: at most one request every three seconds
            if r is None:
                ok = False
                break
            try:
                root = ET.fromstring(r.text)
                total = int(root.find(OPENSEARCH + "totalResults").text)
            except (ET.ParseError, AttributeError, ValueError):
                log.append({"source": label, "status": "failed", "detail": "unparseable response"})
                ok = False
                break
            entries = root.findall(ATOM + "entry")
            for e in entries:
                aid = re.sub(r"v\d+$", "", e.find(ATOM + "id").text.rsplit("/abs/", 1)[-1])
                out[aid] = (e.find(ATOM + "published").text[:10], " ".join(e.find(ATOM + "title").text.split()),
                            " ".join((e.find(ATOM + "summary").text or "").split()))
            start += len(entries)
            if not entries or start >= total:
                if entries == [] and start < (total or 0):
                    log.append({"source": label, "status": "failed", "detail": f"empty page at {start}/{total}"})
                    ok = False
                break
        if ok:
            log.append({"source": label, "status": "ok", "detail": f"{total} results"})
    return out


def openalex(since, log):
    out = {}
    for phrase in FALLBACK_PHRASES:
        label = f"OpenAlex (fallback): {phrase}"
        r = get("https://api.openalex.org/works", {
            "search": phrase, "filter": f"from_publication_date:{since}", "per-page": 200}, log, label)
        time.sleep(1)
        if r is None:
            continue
        works = r.json().get("results", [])
        for w in works:
            urls = [(loc or {}).get("landing_page_url") or "" for loc in w.get("locations") or []]
            ids = [m for u in urls for m in re.findall(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", u)]
            if ids:
                out[ids[0]] = (w.get("publication_date") or "", " ".join((w.get("title") or "").split()), "")
        log.append({"source": label, "status": "ok", "detail": f"{len(works)} results"})
    return out


def openreview(since, log):
    out = {}
    cutoff = dt.datetime.fromisoformat(since).replace(tzinfo=dt.timezone.utc).timestamp() * 1000
    for term in OPENREVIEW_TERMS:
        label = f"OpenReview: {term}"
        # Matches are ranked by relevance, not date, so a newly public record can sit anywhere in the list:
        # page with `offset` until a short page, and report the term as capped if the pages run out.
        notes, ids, pages, failed, capped = [], set(), 0, False, ""
        while pages < OPENREVIEW_PAGES:
            r = get("https://api2.openreview.net/notes/search", {
                "term": term, "type": "terms", "content": "all", "source": "forum",
                "limit": OPENREVIEW_LIMIT, "offset": pages * OPENREVIEW_LIMIT}, log, label)
            time.sleep(1.5)
            if r is None:  # get() logged the failure; keep the pages already read
                failed = True
                break
            try:
                batch = r.json().get("notes", [])
            except ValueError:
                log.append({"source": label, "status": "failed", "detail": "unparseable response"})
                failed = True
                break
            pages += 1
            new = [n for n in batch if n.get("id") not in ids]
            if batch and not new:
                capped = "the API ignored `offset` and repeated a page"
                break
            ids.update(n.get("id") for n in new)
            notes += new
            if len(batch) < OPENREVIEW_LIMIT:
                break
        else:
            capped = f"{OPENREVIEW_PAGES} pages read"
        if not failed:
            log.append({"source": label, "status": "capped" if capped else "ok",
                        "detail": f"{len(notes)} results in {pages} page(s)"
                        + (f" ({capped}; lower-ranked matches are not returned)" if capped else "")})
        for n in notes:
            c = n.get("content", {})
            title = (c.get("title") or {}).get("value", "")
            abstract = (c.get("abstract") or {}).get("value", "")
            if term.lower() not in (title + " " + abstract).lower():
                continue
            venueid = (c.get("venueid") or {}).get("value", "")
            links = " ".join(str((c.get(k) or {}).get("value", "")) for k in ("pdf", "html"))
            mirror = venueid.startswith("dblp.org/") or venueid == "OpenReview.net/Public_Article"
            arxiv_ids = re.findall(r"(\d{4}\.\d{4,5})", links) if mirror else []
            if arxiv_ids:
                # a DBLP mirror of an arXiv paper: the arXiv search covers it; skip papers older than the window
                if arxiv_ids[0][:4] < since[2:4] + since[5:7]:
                    continue
            # odate = made public; mirrors carry a placeholder year-end pdate, so use their creation date
            public = (n.get("cdate") if mirror else (n.get("odate") or n.get("pdate") or n.get("cdate"))) or 0
            if public < cutoff:
                continue
            day = dt.datetime.fromtimestamp(public / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
            venue = (c.get("venue") or {}).get("value", "") + (" (DBLP mirror)" if mirror else "")
            out[n["forum"]] = (venue, " ".join(title.split()), day, " ".join(abstract.split()),
                               arxiv_ids[0] if arxiv_ids else None)
    return out


def default_since():
    cov = yaml.safe_load(open(ROOT / "data" / "coverage.yaml"))
    return (dt.date.fromisoformat(str(cov["searched_through"])) - dt.timedelta(days=3)).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM-DD (default: data/coverage.yaml searched_through minus 3 days)")
    ap.add_argument("--until", default=dt.date.today().isoformat(), help="YYYY-MM-DD (default: today)")
    ap.add_argument("--reported", help="text file with earlier candidate issues; their papers are not relisted")
    ap.add_argument("--json", help="also write a machine-readable report here")
    args = ap.parse_args()
    since = args.since or default_since()
    keys, titles = known()
    seen = reported(args.reported)
    log = []
    ors = openreview(since, log)
    arx = arxiv(since, args.until, log)
    arxiv_failed = any(e["status"] == "failed" and e["source"].startswith("arXiv") for e in log)
    fallback = openalex(since, log) if arxiv_failed else {}
    # complete = every primary query answered; a capped OpenReview term is reported but not fatal,
    # because multi-word terms can match more records than are read (matches are ranked, not dated)
    complete = not any(e["status"] == "failed" for e in log if not e["source"].startswith("OpenAlex"))
    capped = [e["source"] for e in log if e["status"] == "capped"]

    cands, skipped = [], 0
    for forum, (venue, title, day, abstract, aid) in ors.items():
        if forum in keys or norm(title) in titles or (aid and (aid in keys or aid in arx)):
            continue
        if forum in seen or (aid and aid in seen):
            skipped += 1
            continue
        cands.append({"source": "openreview", "id": forum, "date": day, "venue": venue, "title": title,
                      "url": f"https://openreview.net/forum?id={forum}", "abstract": abstract})
    for src, found in (("arxiv", arx), ("openalex", fallback)):
        for aid, (day, title, abstract) in found.items():
            if aid in keys or norm(title) in titles or any(c["id"] == aid for c in cands):
                continue
            if aid in seen:
                skipped += 1
                continue
            cands.append({"source": src, "id": aid, "date": day, "title": title,
                          "url": f"https://arxiv.org/abs/{aid}", "abstract": abstract})

    print(f"# Candidates since {since}\n")
    print(f"Window: OpenReview records made public on or after {since}; arXiv v1 submitted {since} to "
          f"{args.until}. {len(cands)} new candidates"
          + (f"; {skipped} already listed in earlier candidate issues" if skipped else "") + ".\n")
    if not complete:
        print("> [!WARNING]\n> **Incomplete search.** Some queries failed or were rate-limited (see the log "
              "below). Missing candidates are possible; rerun this window before treating it as covered.\n")
    if capped:
        print(f"> [!NOTE]\n> {len(capped)} OpenReview term(s) had more ranked matches than were read "
              f"(up to {OPENREVIEW_PAGES} x {OPENREVIEW_LIMIT}); newly public matches ranked below them are not "
              "returned.\n")
    for title, src in (("OpenReview", "openreview"), ("arXiv", "arxiv"),
                       ("OpenAlex fallback (arXiv records; may lag by days)", "openalex")):
        rows = sorted((c for c in cands if c["source"] == src), key=lambda c: c["date"], reverse=True)
        if src == "openalex" and not arxiv_failed:
            continue
        print(f"## {title}\n")
        for c in rows:
            venue = f"{c['venue']}: " if c.get("venue") else ""
            print(f"- [ ] {c['date']} {venue}[{c['title']}]({c['url']})")
        print()
    print("<details><summary>Search log</summary>\n\n| Query | Status | Detail |\n|:--|:--|:--|")
    for e in log:
        print(f"| {e['source'].replace('|', '/')} | {e['status']} | {e['detail']} |")
    print("\n</details>")
    if args.json:
        json.dump({"since": since, "until": args.until, "complete": complete, "capped": capped,
                   "candidates": cands, "skipped_already_reported": skipped, "log": log},
                  open(args.json, "w"), indent=1)
    sys.exit(0 if complete else 2)


if __name__ == "__main__":
    main()
