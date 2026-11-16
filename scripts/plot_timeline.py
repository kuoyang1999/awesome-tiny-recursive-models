#!/usr/bin/env python3
"""Draw assets/field_timeline.png from data/papers.yaml and data/extra_papers.yaml (core RRM sections only).

    pip install pyyaml matplotlib && python scripts/plot_timeline.py

Months run from 2025-06 to the latest month with a core entry; each paper is counted once, in the
month of its first public version (the catalog `date`).
"""
import collections
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_readme import catalog  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE = {"lineage", "architecture", "training", "search", "depth", "analysis", "efficiency", "applications"}
# validated categorical slots 1-4 (blue, orange, aqua, yellow)
COLORS = {"V": "#2a78d6", "W": "#eb6834", "U": "#1baf7a", "P": "#eda100"}
LABELS = {"V": "peer-reviewed", "W": "workshop", "U": "under review", "P": "preprint / other"}
START = (2025, 6)


def main():
    papers = [p for p in catalog() if p["section"] in CORE]
    counts = {k: collections.Counter() for k in COLORS}
    for p in papers:
        st = p["status"] if p["status"] in COLORS else "P"
        counts[st][str(p["date"])[:7]] += 1
    last = max(str(p["date"])[:7] for p in papers)
    months, (y, m) = [], START
    while f"{y:04d}-{m:02d}" <= last:
        months.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    fig, ax = plt.subplots(figsize=(8, 2.6), dpi=200)
    bottom = [0] * len(months)
    for st, color in COLORS.items():
        h = [counts[st][mo] for mo in months]
        ax.bar(range(len(months)), h, bottom=bottom, color=color, width=0.72, label=LABELS[st],
               edgecolor="white", linewidth=0.8)
        bottom = [b + x for b, x in zip(bottom, h)]
    ax.set_xticks(range(0, len(months), 2))
    ax.set_xticklabels([mo[2:] for mo in months][::2], fontsize=8)
    ax.set_ylabel("papers / month", fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e1e0d9", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(ncol=4, fontsize=8, frameon=False, loc="upper left")
    ax.set_title(f"Recursive reasoning model papers by month of first public version ({sum(bottom)} works)",
                 fontsize=9, loc="left")
    fig.tight_layout()
    (ROOT / "assets").mkdir(exist_ok=True)
    fig.savefig(ROOT / "assets" / "field_timeline.png", metadata={"Software": None})
    print(f"wrote assets/field_timeline.png ({sum(bottom)} core works, {months[0]}..{months[-1]})")


if __name__ == "__main__":
    main()
