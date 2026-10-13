#!/usr/bin/env python3
"""Draw assets/field_timeline.png from data/papers.yaml and data/extra_papers.yaml (core RRM sections only).

    pip install pyyaml matplotlib && python scripts/plot_timeline.py
"""
import collections
import pathlib

import matplotlib.pyplot as plt
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE = {"lineage", "architecture", "training", "search", "depth", "analysis", "efficiency", "applications"}
# validated categorical slots 1-4 (blue, orange, aqua, yellow)
COLORS = {"V": "#2a78d6", "W": "#eb6834", "U": "#1baf7a", "P": "#eda100"}
LABELS = {"V": "peer-reviewed", "W": "workshop", "U": "under review", "P": "preprint / other"}


def main():
    papers = []
    for name in ("papers.yaml", "extra_papers.yaml"):
        if (ROOT / "data" / name).exists():
            papers += yaml.safe_load(open(ROOT / "data" / name)) or []
    months, counts = [], {k: collections.Counter() for k in COLORS}
    y, m = 2025, 6
    while (y, m) <= (2026, 12):
        months.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    for p in papers:
        if p["section"] not in CORE:
            continue
        mo = str(p["date"])[:7]
        st = p["status"] if p["status"] in COLORS else "P"
        if mo in months:
            counts[st][mo] += 1
    last = max(i for i, mo in enumerate(months) if any(counts[s][mo] for s in COLORS))
    months = months[: last + 1]
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
    ax.set_title(f"Recursive reasoning model papers by month ({sum(bottom)} works)", fontsize=9, loc="left")
    fig.tight_layout()
    (ROOT / "assets").mkdir(exist_ok=True)
    fig.savefig(ROOT / "assets" / "field_timeline.png")
    print("wrote assets/field_timeline.png")


if __name__ == "__main__":
    main()
