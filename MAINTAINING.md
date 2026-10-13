# Maintaining the list

`data/papers.yaml` and `data/results.yaml` are exported from the maintainers' survey knowledge base
(a separate, private repository). Everything added by hand or by contributors goes in
`data/extra_papers.yaml`, which `build_readme.py` merges at render time, so a re-export never
overwrites it.

## Weekly (about 20 minutes)

```bash
python scripts/find_new.py --since $(date -d '-8 days' +%F) > candidates.md   # OpenReview, then arXiv
```

If arXiv answers HTTP 429 ("Rate exceeded"), the script skips the remaining arXiv queries and says so
in `candidates.md`; rerun later rather than retrying in a loop. `candidates*.md` is git-ignored.

For each candidate, read the abstract and apply the inclusion rules in `CONTRIBUTING.md`:
1. RRM work (HRM/TRM/URM or a small weight-tied iterative reasoner) → a main section.
2. Looped/recurrent-depth model that answers an RRM design question → `looped`.
3. Agent or harness loop → `boundary` (keep short).
Add an entry to `data/extra_papers.yaml` (venue/status from the primary record only), then:

```bash
python scripts/build_readme.py && python scripts/plot_timeline.py
```

## Monthly

- Re-check venue status of `U` and `P` entries (ICLR, ICML, NeurIPS, ACL decisions) on OpenReview,
  the ACL Anthology, PMLR, or the publisher; never upgrade an entry from an arXiv comment alone.
- Add protocol-annotated numbers to `data/results.yaml` only when the paper states them explicitly;
  record attempts (pass@k), augmentation/voting, identity embeddings, sampled trajectories, and
  training data. Use `protocol: not stated` rather than guessing.
- Run `python scripts/build_readme.py --check` (CI does this on every push and pull request).

## Syncing from the knowledge base

After a knowledge-base refresh, the maintainers run `knowledge_base/scripts/export_awesome.py` in the
survey repository, rebuild, and copy `data/papers.yaml`, `data/results.yaml`, `README.md`, and
`assets/` here. Entries that graduate from `extra_papers.yaml` into the knowledge base are removed
from `extra_papers.yaml` in the same change.
