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
> Methods that iterate on a text candidate with a standard pretrained LLM, and agent/harness loops
> (“loop engineering”, recursive self-improvement), appear only in a short boundary section: they
> repeat whole model calls, not tied weights inside one forward pass.
>
> **Reading numbers.** Scores on ARC-AGI, Sudoku-Extreme, and Maze-Hard depend heavily on protocol:
> pass@1 vs. pass@2, test-time augmentation and voting, sampled trajectories and selectors, test-time
> depth, puzzle-identity embeddings, training on evaluation-task demonstrations, and training-set size.
> Every result in the [results tables](#-protocol-annotated-results) carries its protocol; please do
> not rank across protocols.
>
> **Dates** are the first public version we could document (arXiv v1, OpenReview public date, or the
> publisher); venue and status come from the official record. Merged versions of one study appear as
> extra links on a single entry.

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

Numbers are copied from the cited papers (not reproduced by us), with the precision the source
prints. Rows are grouped by protocol, not ranked; numbers from different protocols, training sets,
or model classes are not comparable.

- **Metric.** *exact accuracy* = whole puzzle/grid correct (not cell or token accuracy); *pass@k* = a
  task counts as solved if any of k submitted attempts is correct; *definition not determined* = the
  source text read for this list (often an abstract) gives a percentage without defining it.
- **Protocol.** *single trajectory* = one recursion trajectory per input (it can contain many
  recursive updates); *extended test-time depth* = more recursion steps at test time than in
  training; *multiple trajectories + selection/vote* = several sampled or perturbed trajectories,
  then a selector or vote; *test-time augmentation + vote* = predictions on augmented views
  (vote@A) aggregated by voting; *lattice + learned search* = structured search over a solution
  lattice. *Not determined* means the protocol could not be determined from the source text read
  for this list — not that the paper fails to report it.
- **Params.** As stated by the source for the reported model (“—” = not recorded here). TRM's 7M is
  the shared network; per-task identity embeddings for ARC can add hundreds of millions of
  parameters (e.g. a 448M task table on top of a 6.8M network in
  [arXiv:2609.33270, Table 10](https://arxiv.org/abs/2609.33270)) and are not included unless noted.
- **Dates and versions.** A score may come from a later revision than the record's first public
  version, so these tables are not a historical leaderboard. Shared-block call counts, where papers
  report them, are not FLOPs, latency, or dollar cost.

{{RESULTS}}

## 🧰 Code and implementations

{{REPOS}}

## 🤝 Contributing

Additions and corrections are welcome. Add new papers to `data/extra_papers.yaml`; record fixes to
exported entries in `data/corrections.yaml` with their primary source (`data/papers.yaml` and
`data/results.yaml` are regenerated from the maintainers' knowledge base). Run
`python scripts/build_readme.py` and open a pull request; CI checks the data and that the README
matches it. See [CONTRIBUTING.md](CONTRIBUTING.md) for the schema and inclusion rules.

## License

[CC0 1.0](LICENSE). Paper titles, abstracts, and figures belong to their authors.
