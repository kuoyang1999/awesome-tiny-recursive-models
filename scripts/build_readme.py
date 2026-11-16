#!/usr/bin/env python3
"""Render README.md from the YAML catalog.

    python scripts/build_readme.py           # rewrite README.md
    python scripts/build_readme.py --check   # exit 1 if the data are invalid or README.md is stale

Sources of truth:
    data/papers.yaml       one entry per paper, exported from the maintainers' knowledge base
    data/extra_papers.yaml hand-curated and community entries (merged at render time)
    data/corrections.yaml  sourced fixes to exported entries (see scripts/apply_corrections.py)
    data/repos.yaml        code repositories and implementations
    data/results.yaml      protocol-annotated reported results
    scripts/template.md    README skeleton with {{placeholders}}
"""
import argparse
import collections
import datetime as dt
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import apply_corrections  # noqa: E402

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

# Result vocabulary (see the legend in scripts/template.md). Order = display order within a benchmark.
PROTOCOLS = ["single trajectory", "extended test-time depth", "multiple trajectories + selection/vote",
             "test-time augmentation + vote", "lattice + learned search", "not determined"]
METRICS = ["exact accuracy (%)", "pass@1 (%)", "pass@2 (%)", "accuracy (%), definition not determined"]
CORE_SECTIONS = {"lineage", "architecture", "training", "search", "depth", "analysis", "efficiency", "applications"}
# a result row's scope must match its source paper: core RRM section -> rrm, boundary -> boundary, other -> related
SCOPES = {"rrm", "related", "boundary"}


def scope_of(section):
    return "rrm" if section in CORE_SECTIONS else "boundary" if section == "boundary" else "related"


def load(name):
    p = ROOT / "data" / name
    return (yaml.safe_load(open(p)) or []) if p.exists() else []


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def record_keys(p):
    """arXiv ids and OpenReview forums that identify a paper (for duplicate and result checks)."""
    keys = set()
    links = p.get("links") or {}
    urls = [links.get("paper") or "", links.get("openreview") or ""]
    urls += [v.get("url", "") for v in p.get("versions") or []]
    for u in urls:
        m = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", u)
        if m:
            keys.add(m.group(1))
        m = re.search(r"openreview\.net/forum\?id=([\w-]+)", u)
        if m:
            keys.add("openreview:" + m.group(1))
    return keys


def validate(papers, results, repos):
    errs, seen = [], set()
    today = dt.date.today().isoformat()
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
        for s in p.get("also", []) or []:
            if s not in valid_sections:
                errs.append(f"{p.get('id')}: unknown extra section {s}")
        if p.get("status") not in STATUS:
            errs.append(f"{p.get('id')}: unknown status {p.get('status')}")
        if p.get("section") == "applications" and p.get("app") not in {g for g, _ in APP_GROUPS}:
            errs.append(f"{p.get('id')}: applications entry needs app group")
        date = p.get("date")
        if not isinstance(date, str) or not re.match(r"^\d{4}-\d{2}(-\d{2})?$", date):
            errs.append(f"{p.get('id')}: date must be a quoted 'YYYY-MM' or 'YYYY-MM-DD' string")
        elif date > today:
            errs.append(f"{p.get('id')}: date {date} is in the future (placeholder date?)")
        for u in list((p.get("links") or {}).values()) + [v.get("url") for v in p.get("versions") or []]:
            if u and not re.match(r"^https?://\S+$", str(u)):
                errs.append(f"{p.get('id')}: malformed link {u}")
    owner = collections.defaultdict(list)
    for p in papers:
        for k in record_keys(p):
            owner[k].append(p["id"])
        owner["title:" + norm_title(p["title"])].append(p["id"])
    for k, ids in owner.items():
        if len(set(ids)) > 1:
            errs.append(f"duplicate record {k} in {sorted(set(ids))}")
    by_key = {k: ids[0] for k, ids in owner.items()}
    by_id = {p["id"]: p for p in papers}
    for r in results:
        tag = f"result {r.get('source_short')} {r.get('benchmark')} {r.get('system')}"
        v = r.get("value")
        if not isinstance(v, str) or not re.match(r"^\d+(\.\d+)?$", v):
            errs.append(f"{tag}: value must be a quoted string exactly as printed in the source (got {v!r})")
        if r.get("metric") not in METRICS:
            errs.append(f"{tag}: unknown metric {r.get('metric')!r}")
        if r.get("protocol") not in PROTOCOLS:
            errs.append(f"{tag}: unknown protocol {r.get('protocol')!r}")
        if r.get("scope", "rrm") not in SCOPES:
            errs.append(f"{tag}: unknown scope {r.get('scope')!r}")
        pid = by_key.get(str(r.get("source_short")))
        if pid is None:
            errs.append(f"{tag}: source is not a catalog entry")
        elif r.get("scope", "rrm") != scope_of(by_id[pid]["section"]):
            errs.append(f"{tag}: scope must be '{scope_of(by_id[pid]['section'])}' "
                        f"(source paper is in section {by_id[pid]['section']})")
    rseen = set()
    for r in repos:
        if not re.match(r"^https://github\.com/[\w.-]+/[\w.-]+$", r.get("url", "")):
            errs.append(f"repo {r.get('name')}: url must be https://github.com/owner/name")
        if r.get("url") in rseen:
            errs.append(f"duplicate repo {r.get('url')}")
        rseen.add(r.get("url"))
    return errs


def badges(p):
    L = p.get("links", {}) or {}
    out = []
    if L.get("paper"):
        label = "arXiv" if "arxiv.org" in L["paper"] else "paper"
        out.append(f"[{label}]({L['paper']})")
    if L.get("openreview"):
        out.append(f"[OpenReview]({L['openreview']})")
    for v in p.get("versions") or []:
        out.append(f"[{v['label']}]({v['url']})")
    if L.get("code"):
        out.append(f"[code]({L['code']})")
    if L.get("project"):
        out.append(f"[project]({L['project']})")
    return " · ".join(out)


def venue(p):
    v = p.get("venue") or STATUS[p["status"]]
    return v.replace("|", "/")


def cell(text):
    return " ".join(str(text).replace("|", "/").split())


def row(p):
    star = " ⭐" if p.get("must_read") else ""
    short = f"**{p['short']}** — " if p.get("short") else ""
    return f"| {str(p['date'])[:7]} | {short}{cell(p['title'])}{star} | {venue(p)} | {badges(p)} | {cell(p['tldr'])} |"


def table(items):
    head = "| Date | Paper | Venue / status | Links | TL;DR |\n|:--|:--|:--|:--|:--|"
    items = sorted(items, key=lambda p: (str(p["date"]), p["title"]), reverse=True)
    return head + "\n" + "\n".join(row(p) for p in items)


def result_rows(rs):
    def key(r):
        return (PROTOCOLS.index(r["protocol"]), METRICS.index(r["metric"]), r["system"].lower())
    out = ["| System | Score | Metric | Params | Protocol | Source |", "|:--|--:|:--|--:|:--|:--|"]
    for r in sorted(rs, key=key):
        proto = r["protocol"] + (f"; {r['note']}" if r.get("note") else "")
        out.append(f"| {cell(r['system'])} | {r['value']} | {r['metric']} | {r.get('params', '—')} | "
                   f"{cell(proto)} | [{r['source_short']}]({r['source']}) |")
    return out


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
    start = "\n".join(f"{i}. {head(p)} ({str(p['date'])[:7]}). {cell(p['tldr'])} {badges(p)}"
                      for i, p in enumerate(must, 1))

    res_md = []
    by_bench = collections.defaultdict(list)
    for r in results:
        by_bench[r["benchmark"]].append(r)
    for bench in sorted(by_bench):
        rrm = [r for r in by_bench[bench] if r.get("scope", "rrm") == "rrm"]
        out = [r for r in by_bench[bench] if r.get("scope", "rrm") != "rrm"]
        res_md.append(f"### {bench}\n")
        res_md += result_rows(rrm)
        if out:
            res_md.append("\n<sub>Outside the RRM scope (related or boundary model classes, listed for reference "
                          "and not comparable with the rows above):</sub>\n")
            res_md += result_rows(out)
        res_md.append("")

    repo_md = ["| Repository | Kind | Notes |", "|:--|:--|:--|"]
    for r in sorted(repos, key=lambda r: (r.get("kind", ""), r["name"].lower())):
        repo_md.append(f"| [{r['name']}]({r['url']}) | {r.get('kind', '')} | {cell(r.get('notes', ''))} |")

    status_counts = collections.Counter(p["status"] for p in papers)
    n_rrm = sum(r.get("scope", "rrm") == "rrm" for r in results)
    stats = (f"**{len(papers)} papers** · {len(repos)} repositories · {len(results)} annotated results "
             f"({n_rrm} in RRM scope) · "
             + " · ".join(f"{status_counts[k]} {STATUS[k]}" for k in STATUS if status_counts.get(k)))

    tpl = open(ROOT / "scripts" / "template.md").read()
    return (tpl.replace("{{STATS}}", stats)
               .replace("{{UPDATED}}", dt.date.today().isoformat())
               .replace("{{TOC}}", "\n".join(toc))
               .replace("{{START_HERE}}", start)
               .replace("{{SECTIONS}}", "\n".join(body))
               .replace("{{RESULTS}}", "\n".join(res_md))
               .replace("{{REPOS}}", "\n".join(repo_md)))


def catalog():
    """papers.yaml plus extra_papers.yaml (extra entries whose id is already exported are skipped)."""
    papers = load("papers.yaml")
    known = {p["id"] for p in papers}
    return papers + [p for p in load("extra_papers.yaml") if p["id"] not in known]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    papers, repos, results = catalog(), load("repos.yaml"), load("results.yaml")
    errs = validate(papers, results, repos)
    errs += apply_corrections.pending(load("papers.yaml"), results, apply_corrections.ledger())
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
