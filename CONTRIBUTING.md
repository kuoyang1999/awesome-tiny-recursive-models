# Contributing

Thank you for helping keep this list accurate. The README is generated, so edit YAML and rebuild:
add new papers to `data/extra_papers.yaml` (`data/papers.yaml` is regenerated from the maintainers'
knowledge base and would overwrite hand edits), and corrections to existing entries as an issue or
a pull request that says what the primary source shows.

```bash
pip install pyyaml
python scripts/build_readme.py          # regenerate README.md
python scripts/build_readme.py --check  # what CI runs
```

## Inclusion rules

1. **Recursive reasoning models (RRMs)** — work that proposes, modifies, analyzes, audits,
   compresses, or applies HRM, TRM, URM, or another small weight-tied iterative reasoner — goes in
   the main sections.
2. **Related looped models** (looped/recurrent-depth language models, equilibrium models) are
   listed when they bear on an RRM design question: state, supervision, exploration/selection,
   depth/stability/stopping, scaling, or compression. Broader looped-transformer catalogs are linked
   in the surveys section.
3. **Boundary** entries (agent loops, harness engineering, recursive self-improvement) are kept short
   and are never described as TRM descendants.
4. Every entry needs a primary link (arXiv, OpenReview, proceedings, or official page). Social posts
   and generated summaries are not sources.
5. Venue/status must come from a primary record. Use `U` for submissions under review (e.g. ICLR
   2027 OpenReview submissions) and `W` for non-archival workshops.

## `data/papers.yaml` schema

```yaml
- id: trm-2025                # unique, lowercase
  title: "Less is More: Recursive Reasoning with Tiny Networks"
  short: TRM                  # optional acronym
  authors: ["Alexia Jolicoeur-Martineau"]
  date: 2025-10-06            # first public version (YYYY-MM-DD or YYYY-MM)
  venue: "arXiv"              # human-readable venue or status
  status: P                   # V venue · W workshop · U under review · P preprint · O report · B blog
  section: lineage            # lineage | architecture | training | search | depth | analysis |
                              # efficiency | applications | benchmarks | foundations | looped |
                              # surveys | boundary
  app: control                # only for section: applications
                              # (control | vision | language | tabular | science | combinatorial | other)
  also: [benchmarks]          # optional extra sections
  must_read: true             # optional; shows in "Start here"
  links:
    paper: https://arxiv.org/abs/2510.04871
    code: https://github.com/SamsungSAILMontreal/TinyRecursiveModels
    openreview: null
  tldr: "One 2-layer network recursively updates a latent z and an answer y..."
```

## `data/results.yaml` schema

```yaml
- benchmark: Sudoku-Extreme
  system: TRM-MLP
  value: 87.4
  metric: exact accuracy (%)
  params: 5M
  protocol: "pass@1; no TTA; trained on 1K puzzles x 1000 augmentations"
  source_short: Jolicoeur-Martineau 2025
  source: https://arxiv.org/abs/2510.04871
```

Only copy numbers that the cited paper states explicitly, and record the protocol fields the paper
reports (attempts, augmentations/voting, identity embeddings, sampled trajectories, training data).
