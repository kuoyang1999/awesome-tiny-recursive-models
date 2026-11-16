#!/usr/bin/env python3
"""Report official OpenReview decisions that disagree with catalog statuses.

    python scripts/check_status.py --json status.json > status.md

For every catalog entry with an OpenReview link, fetch the forum note from the OpenReview API and
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
UA ={"User-Agent": "awesome-tiny-recursive-models/check_status (+https://github.com/kuoyang1999/awesome-tiny-recursive-models)"}


def catalog():
    papers = []
    for name in ("papers.yaml", "extra_papers.yaml"):
        if (ROOT / "data" / name).exists():
            papers += yaml.safe_load(open(ROOT / "data" / name)) or []
    return papers


def fetch(forum):
    for base in ("https://api2.openreview.net", "https://api.openreview.net"):  # API v2, then v1 venues
        for attempt in range(3):
            try:
                r = requests.get(f"{base}/notes", params={"id": forum}, timeout=60, headers=UA)
            except requests.RequestException:
                time.sleep(10 * (attempt + 1))
                continue
            if r.status_code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            if r.status_code == 200 and r.json().get("notes"):
                return r.json()["notes"][0]
            break
    return None


def value(content, key):
    v = content.get(key)
    return v.get("value") if isinstance(v, dict) else v


def decision(venueid, venue):
    """Map an OpenReview venue id to the catalog's status vocabulary."""
    vid = venueid or ""
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
    args = ap.parse_args()
    changes, failed, records = [], [], []

    def day(ms):
        return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d") if ms else None
    for p in catalog():
        url = (p.get("links") or {}).get("openreview") or ""
        m = re.search(r"forum\?id=([\w-]+)", url)
        if not m:
            continue
        note = fetch(m.group(1))
        time.sleep(0.4)  # stay well under the API's 180 requests/minute
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
    if failed:
        print("\nNot fetched: " + ", ".join(failed))
    if args.json:
        json.dump({"checked": len(records), "changes": changes, "failed": failed, "records": records},
                  open(args.json, "w"), indent=1)
    sys.exit(2 if failed else 0)


if __name__ == "__main__":
    main()
