#!/usr/bin/env python3
"""List arXiv and OpenReview candidates that are not yet in data/papers.yaml.

    python scripts/find_new.py --since 2026-10-01 > candidates.md

This is a maintainer aid, not an inclusion rule: every candidate still needs
a human read of the abstract against CONTRIBUTING.md before it is added.
"""
import argparse
import datetime as dt
import pathlib
import re
import time
import xml.etree.ElementTree as ET

import requests
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ATOM = "{http://www.w3.org/2005/Atom}"
QUERIES = [
    'abs:"tiny recursive" OR ti:"tiny recursive"',
    'abs:"hierarchical reasoning model"',
    'abs:"recursive reasoning model" OR abs:"recursive reasoning models"',
    'abs:"recurrent reasoning model" OR abs:"recurrent reasoning models"',
    'abs:"Sudoku-Extreme" OR abs:"Maze-Hard"',
    'abs:"looped transformer" AND (abs:sudoku OR abs:ARC OR abs:maze OR abs:puzzle)',
    'abs:TRM AND (abs:recursive OR abs:recursion)',
]
OR_TERMS = ["tiny recursive", "recursive reasoning model", "hierarchical reasoning model",
            "Sudoku-Extreme", "Maze-Hard"]


def norm(t):
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def known():
    papers = []
    for name in ("papers.yaml", "extra_papers.yaml"):
        if (ROOT / "data" / name).exists():
            papers += yaml.safe_load(open(ROOT / "data" / name)) or []
    ids, titles = set(), set()
    for p in papers:
        titles.add(norm(p["title"]))
        m = re.search(r"(\d{4}\.\d{4,5})", (p.get("links") or {}).get("paper") or "")
        if m:
            ids.add(m.group(1))
    return ids, titles


def arxiv(since):
    """arXiv candidates; on persistent HTTP 429 the remaining queries are skipped, not hammered."""
    out, limited = {}, False
    for q in QUERIES:
        if limited:
            print(f"<!-- skipped (arXiv rate limit): {q} -->")
            continue
        root = None
        for attempt in range(3):
            try:
                r = requests.get("https://export.arxiv.org/api/query", timeout=60, params={
                    "search_query": q, "max_results": 100, "sortBy": "submittedDate", "sortOrder": "descending"})
            except requests.RequestException:
                time.sleep(10)
                continue
            if r.status_code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            try:
                root = ET.fromstring(r.text)
            except ET.ParseError:
                time.sleep(10)
                continue
            break
        if root is None:
            limited = True
            print(f"<!-- arXiv unavailable or rate-limited at: {q}; rerun later -->")
            continue
        for e in root.iter(ATOM + "entry"):
            date = e.find(ATOM + "published").text[:10]
            if date < since:
                continue
            aid = re.sub(r"v\d+$", "", e.find(ATOM + "id").text.rsplit("/abs/", 1)[-1])
            out[aid] = (date, " ".join(e.find(ATOM + "title").text.split()))
        time.sleep(3.1)
    return out


def openreview(since):
    out = {}
    cutoff = dt.datetime.fromisoformat(since).replace(tzinfo=dt.timezone.utc).timestamp() * 1000
    for term in OR_TERMS:
        try:
            r = requests.get("https://api2.openreview.net/notes/search", timeout=60, params={
                "term": term, "type": "terms", "content": "all", "source": "forum", "limit": 1000})
            notes = r.json().get("notes", []) if r.status_code == 200 else None
        except (requests.RequestException, ValueError):
            notes = None
        if notes is None:
            print(f"<!-- OpenReview search unavailable for: {term}; rerun later -->")
            continue
        for n in notes:
            c = n.get("content", {})
            title = (c.get("title") or {}).get("value", "")
            abstract = (c.get("abstract") or {}).get("value", "")
            if term.lower() not in (title + " " + abstract).lower():
                continue
            if (n.get("pdate") or n.get("cdate") or 0) < cutoff:
                continue
            venue = (c.get("venue") or {}).get("value", "")
            out[n["forum"]] = (venue, " ".join(title.split()))
        time.sleep(1.5)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()
    ids, titles = known()
    print(f"# Candidates since {args.since}\n\n## OpenReview\n", flush=True)
    for forum, (venue, title) in openreview(args.since).items():
        if norm(title) not in titles:
            print(f"- [ ] {venue}: [{title}](https://openreview.net/forum?id={forum})", flush=True)
    print("\n## arXiv\n", flush=True)
    for aid, (date, title) in sorted(arxiv(args.since).items(), key=lambda kv: kv[1][0], reverse=True):
        if aid not in ids and norm(title) not in titles:
            print(f"- [ ] {date} [{title}](https://arxiv.org/abs/{aid})", flush=True)


if __name__ == "__main__":
    main()
