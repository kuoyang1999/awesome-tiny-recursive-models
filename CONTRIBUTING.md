# Contributing

Thank you for helping keep this list accurate. The README is generated, so edit YAML and rebuild:
add new papers to `data/extra_papers.yaml` (`data/papers.yaml` and `data/results.yaml` are
regenerated from the maintainers' knowledge base and would overwrite hand edits), and send
corrections to existing entries as an issue or a pull request against `data/corrections.yaml` that
says what the primary source shows (page, table, or record field).

```bash
pip install pyyaml
python scripts/build_readme.py          # regenerate README.md
python scripts/build_readme.py --check  # what CI runs (data checks + README freshness)
```

## Inclusion rules

1. **Recursive reasoning models (RRMs)** — work that proposes, modifies, analyzes, audits,
   compresses, or applies HRM, TRM, URM, or another small weight-tied iterative reasoner — goes in
   the main sections.
2. **Related looped models** (looped/recurrent-depth language models, equilibrium models) are
   listed when they bear on an RRM design question: state, supervision, exploration/selection,
   depth/stability/stopping, scaling, or compression. Broader looped-transformer catalogs are linked
   in the surveys section.
3. **Boundary** entries (text-candidate iteration with a standard pretrained LLM, agent loops,
   harness engineering, recursive self-improvement) are kept short and are never described as TRM
   descendants.
4. Every entry needs a primary link (arXiv, OpenReview, proceedings, or official page). Social posts
   and generated summaries are not sources.
5. Venue/status must come from a primary record. Use `U` for submissions under review (e.g. ICLR
   2027 OpenReview submissions), `W` for workshop papers, and `P` for public manuscripts without an
   acceptance (including withdrawn or rejected submissions). Do not upgrade a status from an arXiv
   comment or a project page alone.
6. One entry per study. Versions of the same study (workshop, conference, arXiv) are listed as
   `versions` of one entry, matched on authors, abstract, method, and results, not on a similar
   title alone. Never link an anonymous submission to named authors by inference.

## `data/papers.yaml` schema

```yaml
- id: '2510.04871'            # unique; arXiv id or openreview-<forum>
  title: "Less is More: Recursive Reasoning with Tiny Networks"
  short: TRM                  # optional acronym
  date: '2025-10-06'          # first public version we could document (quoted YYYY-MM-DD or YYYY-MM)
  venue: "arXiv"              # human-readable venue or status, from the official record
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
  versions:                   # optional: other public versions of the same study
    - {label: "ICLR 2026 Workshop (LIT) version", url: "https://openreview.net/forum?id=..."}
  tldr: "One 2-layer network recursively updates a latent z and an answer y..."
```

## `data/results.yaml` schema

```yaml
- benchmark: Sudoku-Extreme
  system: TRM-MLP
  value: '87.4'                 # quoted, with the precision the source prints
  metric: exact accuracy (%)    # exact accuracy (%) | pass@1 (%) | pass@2 (%) |
                                # accuracy (%), definition not determined
  params: 5M                    # as stated by the source; '—' if not recorded
  protocol: single trajectory   # single trajectory | extended test-time depth |
                                # multiple trajectories + selection/vote | test-time augmentation + vote |
                                # lattice + learned search | not determined
  scope: rrm                    # optional: rrm (default) | related | boundary, matching the paper's section
  note: "trained on 1K puzzles x 1000 augmentations"   # optional comparison limits
  source_short: '2510.04871'
  source: https://arxiv.org/abs/2510.04871
```

Only copy numbers that the cited paper states explicitly, and record the protocol fields the paper
reports (attempts, augmentations/voting, identity embeddings, sampled trajectories, test-time depth,
training data). *Not determined* means the text you read does not settle the field; it is not a claim
that the paper omits it. Different protocols, training sets, and model classes are not comparable.

## `data/corrections.yaml`

Fixes to exported entries, each with `source` (primary URL), `basis` (what the source shows), and
`checked` (who checked it and when; AI-assisted checks are labelled as such). See `MAINTAINING.md`.
