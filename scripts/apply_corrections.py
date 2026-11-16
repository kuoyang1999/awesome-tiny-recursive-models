#!/usr/bin/env python3
"""Re-apply data/corrections.yaml to the exported catalog files.

    python scripts/apply_corrections.py           # rewrite data/papers.yaml and data/results.yaml
    python scripts/apply_corrections.py --check   # exit 1 if a recorded correction is not reflected

data/papers.yaml and data/results.yaml are exported from the maintainers' knowledge base, so a
re-export can silently undo a fix made here. Every fix to an exported entry is therefore recorded in
data/corrections.yaml together with its primary source, and this script re-applies the ledger after
each export. `build_readme.py --check` (CI) fails while any correction is missing.

Ledger sections:
    papers:   {id, set: {field: value}, source, basis, checked}
              `links` and `versions` are merged into the entry; other fields are replaced
    merges:   {alias, into, version: {label, url}, source, basis, checked}
              the alias entry is removed and the version is listed on the canonical entry
    results:  {match: {source_short, benchmark}, set: {field: value}, source, basis, checked}
"""
import argparse
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# The export writes these older labels; they map one-to-one onto the current vocabulary.
LEGACY_LABELS = {
    "protocol": {
        "single pass": "single trajectory",
        "multi-trajectory / voting": "multiple trajectories + selection/vote",
        "not stated": "not determined",
    },
    "metric": {
        "exact (%)": "exact accuracy (%)",
        "accuracy (%), attempts not stated": "accuracy (%), definition not determined",
    },
}


def load(name):
    p = DATA / name
    return (yaml.safe_load(open(p)) or []) if p.exists() else []


def dump(obj, name, **kw):
    with open(DATA / name, "w") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False, **kw)


def ledger():
    p = DATA / "corrections.yaml"
    led = (yaml.safe_load(open(p)) or {}) if p.exists() else {}
    return {k: led.get(k) or [] for k in ("papers", "merges", "results")}


def _result_rows(results, match):
    return [r for r in results if all(str(r.get(k)) == str(v) for k, v in match.items())]


def _with_version(entry, version):
    versions = list(entry.get("versions") or [])
    if all(v.get("url") != version["url"] for v in versions):
        versions.append(dict(version))
    entry["versions"] = versions


def apply(papers, results, led):
    """Return corrected copies of papers and results, plus a list of problems."""
    problems = []
    by_id = {p["id"]: p for p in papers}
    for m in led["merges"]:
        if m["into"] not in by_id:
            problems.append(f"merge target {m['into']} is not in papers.yaml")
            continue
        if m.get("version"):
            _with_version(by_id[m["into"]], m["version"])
    aliases = {m["alias"] for m in led["merges"]}
    papers = [p for p in papers if p["id"] not in aliases]
    by_id = {p["id"]: p for p in papers}
    for c in led["papers"]:
        p = by_id.get(c["id"])
        if p is None:
            problems.append(f"correction target {c['id']} is not in papers.yaml")
            continue
        for k, v in c["set"].items():
            if k == "links":
                p["links"] = {**(p.get("links") or {}), **v}
                p["links"] = {lk: lv for lk, lv in p["links"].items() if lv}
            elif k == "versions":  # additive, so merges and corrections can both list versions
                for ver in v:
                    _with_version(p, ver)
            elif v is None:
                p.pop(k, None)
            else:
                p[k] = v
    for r in results:
        for field, mapping in LEGACY_LABELS.items():
            if r.get(field) in mapping:
                r[field] = mapping[r[field]]
    for c in led["results"]:
        rows = _result_rows(results, c["match"])
        if len(rows) != 1:
            problems.append(f"result match {c['match']} hits {len(rows)} rows (expected 1)")
            continue
        for k, v in c["set"].items():
            if v is None:
                rows[0].pop(k, None)
            else:
                rows[0][k] = v
    return papers, results, problems


def pending(papers, results, led):
    """Corrections that the current files do not reflect (used by build_readme.py --check)."""
    out = []
    by_id = {p["id"]: p for p in papers}
    for m in led["merges"]:
        if m["alias"] in by_id:
            out.append(f"merge not applied: {m['alias']} is still listed (should be a version of {m['into']})")
        elif m.get("version") and m["into"] in by_id and all(
                v.get("url") != m["version"]["url"] for v in by_id[m["into"]].get("versions") or []):
            out.append(f"merge not applied: {m['into']} lacks version {m['version']['url']}")
    for c in led["papers"]:
        p = by_id.get(c["id"])
        if p is None:
            out.append(f"correction target {c['id']} is missing from papers.yaml")
            continue
        for k, v in c["set"].items():
            have = p.get(k)
            if k == "links":
                if any((have or {}).get(lk) != lv for lk, lv in v.items() if lv):
                    out.append(f"{c['id']}: links differ from data/corrections.yaml")
            elif k == "versions":
                urls = {x.get("url") for x in have or []}
                if any(ver["url"] not in urls for ver in v):
                    out.append(f"{c['id']}: versions lack an entry from data/corrections.yaml")
            elif (have if have is None else str(have)) != (v if v is None else str(v)):
                out.append(f"{c['id']}: {k} is {have!r}, data/corrections.yaml says {v!r}")
    for c in led["results"]:
        rows = _result_rows(results, c["match"])
        if len(rows) != 1:
            out.append(f"result {c['match']}: {len(rows)} matching rows")
            continue
        for k, v in c["set"].items():
            if rows[0].get(k) != v:
                out.append(f"result {c['match']}: {k} is {rows[0].get(k)!r}, data/corrections.yaml says {v!r}")
    for kind in ("papers", "merges", "results"):
        for c in led[kind]:
            if not c.get("source") or not c.get("checked"):
                out.append(f"corrections.yaml {kind} entry without source/checked: {c}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    led = ledger()
    papers, results = load("papers.yaml"), load("results.yaml")
    if args.check:
        missing = pending(papers, results, led)
        print("\n".join(missing) or "all corrections applied", file=sys.stderr if missing else sys.stdout)
        sys.exit(1 if missing else 0)
    papers, results, problems = apply(papers, results, led)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        sys.exit(1)
    dump(papers, "papers.yaml", width=110)
    dump(results, "results.yaml")
    left = pending(papers, results, led)
    if left:
        print("\n".join(left), file=sys.stderr)
        sys.exit(1)
    print(f"applied {sum(len(v) for v in led.values())} corrections "
          f"({len(papers)} papers, {len(results)} results)")


if __name__ == "__main__":
    main()
