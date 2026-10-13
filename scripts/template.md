<div align="center">

# Awesome Tiny Recursive Models [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

**Tiny Recursive Models (TRM), the Hierarchical Reasoning Model (HRM), and the wider family of
recursive reasoning models: small, weight-tied networks that think by iterating.**

<img src="assets/field_timeline.png" alt="Monthly count of recursive-reasoning-model papers by type" width="92%"/>

{{STATS}} · updated {{UPDATED}}

</div>

---

> **What belongs here.** A *recursive reasoning model* (RRM) applies one small set of weights again and
> again to refine a carried latent and/or answer state (for example `z ← f(x + y + z)`, `y ← f(y + z)`
> in TRM), usually with deep supervision and a stopping rule. We list RRMs, their analyses and
> applications, the benchmarks they are measured on, and a curated slice of related looped models.
> Agent/harness loops (“loop engineering”, recursive self-improvement) appear only in a short boundary
> section: they repeat whole model runs, not tied weights inside one forward pass.
>
> **Reading numbers.** Scores on ARC-AGI, Sudoku-Extreme, and Maze-Hard depend heavily on protocol:
> pass@1 vs. pass@2, test-time augmentation and voting, puzzle-identity embeddings, training on
> evaluation-task demonstrations, and the number of sampled trajectories. Every result in the
> [results tables](#-protocol-annotated-results) carries its protocol; please do not rank across protocols.

## Contents

- [⭐ Start here](#-start-here)
{{TOC}}
- [📊 Protocol-annotated results](#-protocol-annotated-results)
- [🧰 Code and implementations](#-code-and-implementations)
- [🤝 Contributing](#-contributing)

## ⭐ Start here

{{START_HERE}}

{{SECTIONS}}

## 📊 Protocol-annotated results

Numbers are copied from the cited papers (not reproduced by us). “TTA” = test-time augmentation;
“vote@A” = majority vote over A augmented views; “ID” = learned per-task identity embedding.

{{RESULTS}}

## 🧰 Code and implementations

{{REPOS}}

## 🤝 Contributing

Additions and corrections are welcome. Edit `data/papers.yaml` (or `repos.yaml`, `results.yaml`),
run `python scripts/build_readme.py`, and open a pull request; CI checks that the README matches
the data. See [CONTRIBUTING.md](CONTRIBUTING.md) for the schema and inclusion rules.

## License

[CC0 1.0](LICENSE). Paper titles, abstracts, and figures belong to their authors.
