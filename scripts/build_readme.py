#!/usr/bin/env python3
"""Render README.md from the YAML catalog.

    python scripts/build_readme.py           # rewrite README.md
    python scripts/build_readme.py --check   # exit 1 if README.md is stale

Sources of truth:
    data/papers.yaml    one entry per paper (see CONTRIBUTING.md for the schema)
    data/repos.yaml     code repositories and implementations
    data/results.yaml   protocol-annotated reported results
    scripts/template.md README skeleton with {{placeholders}}
"""
import argparse
import collections
import datetime as dt
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

SECTIONS = [
    ("lineage", "🧬 Core lineage: HRM, TRM, and direct successors"),
    ("architecture", "🏗️ Operator and state design"),
    ("training", "🎓 Supervision and training contracts"),
    ("search", "🎲 Exploration, search, and selection"),
    ("depth", "⏱️ Depth, stability, halting, and fixed points"),
    ("analysis", "🔬 Analyses, audits, and theory"),
    ("efficiency", "⚡ Efficiency and compression"),
    ("applications", "🌍 Applications beyond puzzles"),
    ("benchmarks", "📏 Benchmarks, competitions, and evaluation"),
    ("foundations", "🏛️ Foundations and precursors"),
    ("looped", "🔁 Related looped and recurrent-depth models"),
    ("surveys", "📚 Surveys, perspectives, and related lists"),
    ("boundary", "🧱 Boundary: agent, harness, and self-improvement loops"),
]
APP_GROUPS = [
    ("control", "Control, robotics, and RL"),
    ("vision", "Vision and generation"),
    ("language", "Language, code, and speech"),
    ("tabular", "Tabular, time series, and recommendation"),
    ("science", "Science and engineering"),
    ("combinatorial", "Graphs and combinatorial optimization"),
    ("other", "Other domains"),
]
STATUS = {"V": "peer-reviewed", "W": "workshop", "U": "under review", "P": "preprint",
          "O": "report", "B": "blog"}
REQUIRED = ["id", "title", "date", "section", "status", "links", "tldr"]


def load(name):
    p = ROOT / "data" / name
    return yaml.safe_load(open(p)) or [] if p.exists() else []


def validate(papers):
    errs, seen = [], set()
    valid_sections = {s for s, _ in SECTIONS}
    for p in papers:
        for k in REQUIRED:
            if k not in p or p[k] in (None, ""):
                errs.append(f"{p.get('id', '?')}: missing {k}")
        if p.get("id") in seen:
            errs.append(f"duplicate id {p['id']}")
        seen.add(p.get("id"))
        if p.get("section") not in valid_sections:
            errs.append(f"{p.get('id')}: unknown section {p.get('section')}")
        if p.get("status") not in STATUS:
            errs.append(f"{p.get('id')}: unknown status {p.get('status')}")
        if p.get("section") == "applications" and p.get("app") not in {g for g, _ in APP_GROUPS}:
            errs.append(f"{p.get('id')}: applications entry needs app group")
        if not re.match(r"^\d{4}-\d{2}(-\d{2})?$", str(p.get("date", ""))):
            errs.append(f"{p.get('id')}: date must be YYYY-MM or YYYY-MM-DD")
    return errs


def badges(p):
    L = p.get("links", {}) or {}
    out = []
    if L.get("paper"):
        label = "arXiv" if "arxiv.org" in L["paper"] else "paper"
        out.append(f"[{label}]({L['paper']})")
    if L.get("openreview"):
        out.append(f"[OpenReview]({L['openreview']})")
    if L.get("code"):
        out.append(f"[code]({L['code']})")
    if L.get("project"):
        out.append(f"[project]({L['project']})")
    return " · ".join(out)


def venue(p):
    v = p.get("venue") or STATUS[p["status"]]
    return v.replace("|", "/")


def row(p):
    star = " ⭐" if p.get("must_read") else ""
    short = f"**{p['short']}** — " if p.get("short") else ""
    title = p["title"].replace("|", "/")
    tldr = p["tldr"].replace("|", "/").strip()
    return f"| {str(p['date'])[:7]} | {short}{title}{star} | {venue(p)} | {badges(p)} | {tldr} |"


def table(items):
    head = "| Date | Paper | Venue / status | Links | TL;DR |\n|:--|:--|:--|:--|:--|"
    items = sorted(items, key=lambda p: (str(p["date"]), p["title"]), reverse=True)
    return head + "\n" + "\n".join(row(p) for p in items)


def render(papers, repos, results):
    by_sec = collections.defaultdict(list)
    for p in papers:
        by_sec[p["section"]].append(p)
        for s in p.get("also", []) or []:
            by_sec[s].append(p)
    toc, body = [], []
    for key, title in SECTIONS:
        items = by_sec.get(key, [])
        if not items:
            continue
        # GitHub drops emoji/punctuation but keeps the space after a leading emoji -> leading "-"
        anchor = re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-")
        toc.append(f"- [{title}](#{anchor}) ({len(items)})")
        body.append(f"## {title}\n")
        if key == "applications":
            groups = collections.defaultdict(list)
            for p in items:
                groups[p.get("app", "other")].append(p)
            for g, gt in APP_GROUPS:
                if groups.get(g):
                    body.append(f"### {gt}\n\n{table(groups[g])}\n")
        else:
            body.append(table(items) + "\n")

    must = sorted([p for p in papers if p.get("must_read")], key=lambda p: str(p["date"]))
    def head(p):
        return f"**{p['short']}** — {p['title']}" if p.get("short") else f"**{p['title']}**"
    start = "\n".join(f"{i}. {head(p)} ({str(p['date'])[:7]}). {p['tldr']} {badges(p)}"
                      for i, p in enumerate(must, 1))

    res_md = []
    by_bench = collections.defaultdict(list)
    for r in results:
        by_bench[r["benchmark"]].append(r)
    for bench in sorted(by_bench):
        rs = sorted(by_bench[bench], key=lambda r: -float(r["value"]))
        res_md.append(f"### {bench}\n\n| System | Score | Metric | Params | Protocol | Source |\n|:--|--:|:--|--:|:--|:--|")
        for r in rs:
            res_md.append(f"| {r['system']} | {r['value']} | {r['metric']} | {r.get('params', '—')} | "
                          f"{r.get('protocol', '—')} | [{r['source_short']}]({r['source']}) |")
        res_md.append("")

    repo_md = ["| Repository | Kind | Notes |", "|:--|:--|:--|"]
    for r in sorted(repos, key=lambda r: (r.get("kind", ""), r["name"].lower())):
        repo_md.append(f"| [{r['name']}]({r['url']}) | {r.get('kind', '')} | {r.get('notes', '').replace('|', '/')} |")

    status_counts = collections.Counter(p["status"] for p in papers)
    stats = (f"**{len(papers)} papers** · {len(repos)} repositories · {len(results)} annotated results · "
             + " · ".join(f"{status_counts[k]} {STATUS[k]}" for k in STATUS if status_counts.get(k)))

    tpl = open(ROOT / "scripts" / "template.md").read()
    return (tpl.replace("{{STATS}}", stats)
               .replace("{{UPDATED}}", dt.date.today().isoformat())
               .replace("{{TOC}}", "\n".join(toc))
               .replace("{{START_HERE}}", start)
               .replace("{{SECTIONS}}", "\n".join(body))
               .replace("{{RESULTS}}", "\n".join(res_md))
               .replace("{{REPOS}}", "\n".join(repo_md)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    papers, repos, results = load("papers.yaml"), load("repos.yaml"), load("results.yaml")
    # hand-curated and community entries live in extra_papers.yaml so knowledge-base exports never overwrite them
    if (ROOT / "data" / "extra_papers.yaml").exists():
        known = {p["id"] for p in papers}
        papers += [p for p in load("extra_papers.yaml") if p["id"] not in known]
    errs = validate(papers)
    if errs:
        print("\n".join(errs), file=sys.stderr)
        sys.exit(1)
    md = render(papers, repos, results)
    readme = ROOT / "README.md"
    if args.check:  # the "updated" stamp is today's date, so it is ignored when comparing
        def unstamped(text):
            return re.sub(r"updated \d{4}-\d{2}-\d{2}", "updated", text)
        if not readme.exists() or unstamped(readme.read_text()) != unstamped(md):
            print("README.md is stale; run python scripts/build_readme.py", file=sys.stderr)
            sys.exit(1)
        print("README.md is up to date")
        return
    readme.write_text(md)
    print(f"wrote README.md ({len(papers)} papers)")


if __name__ == "__main__":
    main()
