# Maintaining the list

`data/papers.yaml` and `data/results.yaml` are exported from the maintainers' survey knowledge base
(a separate, private repository). Everything added by hand or by contributors goes in
`data/extra_papers.yaml`, which `build_readme.py` merges at render time, so a re-export never
overwrites it. Fixes to exported entries go in `data/corrections.yaml` (see below).

## Weekly (about 20 minutes)

The `weekly-candidates` workflow runs every Monday (and on demand from the Actions tab). It searches
arXiv and OpenReview from three days before `searched_through` in `data/coverage.yaml` up to the run
date, drops papers already in the catalog or already listed in an earlier `candidates` issue, and opens
an issue labelled `candidates`. The issue is a list of **unscreened** candidates, not a set of accepted
papers, and the catalog is not updated until a maintainer screens them.

If a query fails or arXiv answers HTTP 429, the issue title starts with `[incomplete search]`, the
search log in the issue says which queries failed, and the run is marked as failed. Because the
window starts from `data/coverage.yaml`, the next run searches the same weeks again. Do not treat a
quiet week as covered unless the run was complete. OpenReview terms are searched as quoted phrases
(unquoted, the search matches any of the words and returns thousands of records ranked by relevance,
not date); up to four pages of 1,000 are read, and a term with more matches is listed as capped
(reported, not fatal). OpenReview sometimes answers HTTP 403 (a bot challenge) to GitHub-hosted
runners: the run then reports an incomplete search. Rerun it later or run `scripts/find_new.py` and
`scripts/check_status.py` from a machine that OpenReview answers normally; never try to get around
the challenge.

To run the same search locally:

```bash
python scripts/find_new.py --since 2026-11-09 --json candidates.json > candidates.md
```

The workflow can also be started by hand with `open_issue` off (report only: see the run summary and
the `candidates` artifact). `candidates*.md`, `candidates*.json`, and `status*.*` are git-ignored.

For each candidate, read at least the abstract (the full text when the mechanism, loop level, or
numbers are unclear) and apply the inclusion rules in `CONTRIBUTING.md`:
1. RRM work (HRM/TRM/URM or a small weight-tied iterative reasoner) → a main section.
2. Looped/recurrent-depth model that answers an RRM design question → `looped`.
3. Text-candidate iteration with a standard LLM, agent or harness loop → `boundary` (keep short).
Record the decision in the issue (including "deferred" and why). Add accepted papers to
`data/extra_papers.yaml` (venue/status from the primary record only), then:

```bash
python scripts/build_readme.py && python scripts/plot_timeline.py && python scripts/build_readme.py --check
```

After a complete pass, set `searched_through` in `data/coverage.yaml` to the last arXiv submission
date the pass covered and add a `passes` entry with the sources, window, and any failures.

## Monthly

- The first Monday run of each month also runs `scripts/check_status.py`, which compares catalog
  statuses with OpenReview decisions (withdrawn, rejected, accepted). Confirm each change on the
  official record (OpenReview, ACL Anthology, PMLR, the publisher) before editing; never upgrade an
  entry from an arXiv comment or a project page alone. Author-uploaded (`OpenReview.net/Archive`) and
  DBLP mirror records are not decisions, and neither is a workshop record whose venue id still ends in
  `/Submission` (some workshops never post decisions on OpenReview: check the workshop's accepted list)
  or an ACL Rolling Review record (acceptance shows on the ACL Anthology of the venue it was committed to).
- Add protocol-annotated numbers to `data/results.yaml` only when the paper states them explicitly;
  record attempts (pass@k), augmentation/voting, sampled trajectories, test-time depth, identity
  embeddings, and training data. Write `value` as a quoted string with the source's precision
  (`'79.90'`, not `79.9`). Use `not determined` when the text you read does not settle the protocol
  or metric; it means "not determined here", not "not reported by the paper".
- Run `python scripts/build_readme.py --check` (CI does this on every push and pull request).

## Corrections to exported entries

Fix exported entries through `data/corrections.yaml`, never only in `papers.yaml`/`results.yaml`:
each entry names the field values, the primary source, the evidence (page, table, or record field),
and who checked it and when. `python scripts/apply_corrections.py` applies the ledger;
`build_readme.py --check` fails while any recorded fix is missing. Versions of one study are merged
with a `merges` entry: the alias disappears and its link is listed on the canonical entry.

Do not publicly link an anonymous submission to named authors. When an anonymous record and a named
record are the same study and their titles differ, keep the named record, drop the anonymous one,
and do not record the pairing here. Identical titles and abstracts posted by the authors
themselves (e.g. an arXiv version of an ICLR submission) may be linked.

## Syncing from the knowledge base

After a knowledge-base refresh, the maintainers run `knowledge_base/scripts/export_awesome.py` in the
survey repository, then here:

```bash
python scripts/apply_corrections.py && python scripts/build_readme.py && python scripts/plot_timeline.py
python scripts/build_readme.py --check
```

Check the export diff before committing. The exporter must (a) write result values as the source's
strings (a `float()` conversion turns `79.90` into `79.9` and `100` into `100.0`; CI rejects
non-string values), (b) keep an unresolved protocol or metric as "not determined", not "not stated",
and (c) never fill a missing date with a placeholder (CI rejects future dates). Result rows for papers
outside the core RRM sections must carry `scope: related` (looped, benchmark, foundation papers) or
`scope: boundary` (CI enforces this). Entries that
graduate from `extra_papers.yaml` into the knowledge base are removed from `extra_papers.yaml` in the
same change, and `data/repos.yaml` is maintained by hand (the exporter does not update it).
