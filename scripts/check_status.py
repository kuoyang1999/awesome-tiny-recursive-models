#!/usr/bin/env python3
"""Report official OpenReview decisions that disagree with catalog statuses.

    python scripts/check_status.py --json status.json > status.md

For every catalog entry with an OpenReview link, find the forum note through the OpenReview search API and
compare its venue id with the entry's status (U under review, V/W accepted, P otherwise). This only
reports; a maintainer confirms each change on the official record before editing the data.
Exit status 2 if some notes could not be fetched.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time

import requests
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
UA = {"User-Agent": "awesome-tiny-recursive-models/check_status (+https://github.com/kuoyang1999/awesome-tiny-recursive-models)"}


def catalog():
    papers = []
    for name in ("papers.yaml", "extra_papers.yaml"):
        if (ROOT / "data" / name).exists():
            papers += yaml.safe_load(open(ROOT / "data" / name)) or []
    return papers


def fetch(forum, title):
    """The forum note, found through the search endpoint by its title. Direct note lookups
    (GET /notes?id=) are challenge-gated for anonymous clients, so they are not attempted."""
    for n in by_title(title) or []:
        if n.get("forum") == forum or n.get("id") == forum:
            return n
    return None


def norm(t):
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())


def by_title(title):
    """OpenReview forum notes whose title equals `title` (normalized), or None if the search failed."""
    for attempt in range(3):
        try:
            r = requests.get("https://api2.openreview.net/notes/search", timeout=60, headers=UA, params={
                "term": title, "type": "terms", "content": "all", "source": "forum", "limit": 25})
        except requests.RequestException:
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code == 429:
            time.sleep(30 * (attempt + 1))
            continue
        if r.status_code != 200:
            return None
        return [n for n in r.json().get("notes", []) if norm(value(n.get("content", {}), "title")) == norm(title)]
    return None


def value(content, key):
    v = content.get(key)
    return v.get("value") if isinstance(v, dict) else v


def decision(venueid, venue):
    """Map an OpenReview venue id to the catalog's status vocabulary."""
    vid = venueid or ""
    if vid.startswith("dblp.org/") or vid in ("OpenReview.net/Public_Article", "OpenReview.net/Archive") \
            or (venue or "").startswith("CoRR"):
        return None, "mirror or author-uploaded record, not a venue decision (check the publisher)"
    if re.search(r"/(Under_Review|Decision_Pending)$", vid):
        return "U", "under review"
    if vid.endswith("/Rejected"):
        return "P", "not accepted"
    if re.search(r"/(Withdrawn|Desk_Rejected)_Submission$", vid):
        return "P", "withdrawn" if "Withdrawn" in vid else "desk rejected"
    if vid.endswith("/Rejected_Submission"):
        return "P", "not accepted"
    if vid.endswith("/Submission") or (venue or "").startswith("Submitted to"):
        return "U", "under review"
    if vid:
        return ("W" if "workshop" in (vid + " " + (venue or "")).lower() else "V"), "accepted"
    return None, "no venue id"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--title-search", action="store_true",
                    help="also look up entries without an OpenReview link by exact title")
    ap.add_argument("--max-minutes", type=float, default=30,
                    help="stop after this long and list the entries left unchecked")
    args = ap.parse_args()
    changes, failed, records, matches, unchecked = [], [], [], [], []
    started = time.monotonic()

    def day(ms):
        return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d") if ms else None
    for p in catalog():
        url = (p.get("links") or {}).get("openreview") or ""
        m = re.search(r"forum\?id=([\w-]+)", url)
        if (m or (args.title_search and p["status"] in ("P", "U"))) and \
                time.monotonic() - started > args.max_minutes * 60:
            unchecked.append(p["id"])
            continue
        if not m:
            if args.title_search and p["status"] in ("P", "U"):
                found = by_title(p["title"])
                time.sleep(0.5)
                if found is None:
                    failed.append(p["id"] + " (title search)")
                for n in found or []:
                    c = n.get("content", {})
                    status, label = decision(value(c, "venueid"), value(c, "venue"))
                    matches.append({"id": p["id"], "title": p["title"], "catalog": f"{p['status']} ({p.get('venue')})",
                                    "forum": n["forum"], "venue": value(c, "venue"), "venueid": value(c, "venueid"),
                                    "odate": day(n.get("odate")), "pdate": day(n.get("pdate")),
                                    "authors_visible": bool(value(c, "authors")), "suggested": status, "reason": label})
            continue
        note = fetch(m.group(1), p["title"])
        time.sleep(0.5)  # stay well under the API's 180 requests/minute
        if note is None:
            failed.append(p["id"])
            continue
        c = note.get("content", {})
        venue, venueid = value(c, "venue"), value(c, "venueid")
        records.append({"id": p["id"], "forum": m.group(1), "venue": venue, "venueid": venueid,
                        "odate": day(note.get("odate")), "pdate": day(note.get("pdate")),
                        "cdate": day(note.get("cdate")), "title": value(c, "title")})
        status, label = decision(venueid, venue)
        if status and status != p["status"]:
            changes.append({"id": p["id"], "title": p["title"], "catalog": f"{p['status']} ({p.get('venue')})",
                            "official": f"{venue} [{venueid}]", "suggested": status, "reason": label, "url": url})
    print(f"# OpenReview status check, {dt.date.today().isoformat()}\n")
    print(f"Checked {len(records)} OpenReview records; {len(changes)} disagree with the catalog"
          + (f"; {len(failed)} could not be fetched" if failed else "") + ".\n")
    if changes:
        print("| Entry | Catalog | Official record | Suggested |\n|:--|:--|:--|:--|")
        for c in changes:
            print(f"| [{c['title'][:80].replace('|', '/')}]({c['url']}) | {c['catalog']} | {c['official']} | "
                  f"{c['suggested']} ({c['reason']}) |")
    if matches:
        print(f"\nOpenReview records with the same title as {len({m['id'] for m in matches})} entries that have no "
              "OpenReview link (confirm authors and content before linking; never link an anonymous record by inference):\n")
        print("| Entry | Catalog | OpenReview record |\n|:--|:--|:--|")
        for m in matches:
            print(f"| {m['title'][:80].replace('|', '/')} | {m['catalog']} | "
                  f"[{m['venue']}](https://openreview.net/forum?id={m['forum']}) |")
    if failed:
        print("\nNot found by title search (title differs from the OpenReview record, or the search failed): "
              + ", ".join(failed))
    if unchecked:
        print(f"\nNot checked within the {args.max_minutes:g}-minute budget: " + ", ".join(unchecked))
    if args.json:
        json.dump({"checked": len(records), "changes": changes, "failed": failed, "unchecked": unchecked,
                   "records": records, "title_matches": matches}, open(args.json, "w"), indent=1)
    sys.exit(2 if failed or unchecked else 0)


if __name__ == "__main__":
    main()
