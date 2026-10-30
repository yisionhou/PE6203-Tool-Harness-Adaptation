# Member 3 publication and reproduction

This delivery adds the formal six-task evaluation, the four offline code fixes, source tests, pinned execution workspaces, the English report and exact archived evidence. It builds on repository commit `3e2b851640fe7015ef36f7d74930b51cdcdbf143` and preserves the existing upstream project and Member 1/2 source.

## Entry points

Start at [member3/README.md](../member3/README.md). The English report and editable Word document are `docs/member3-report-en.md` and `docs/member3-report-en.docx`. Saved numerical results are in `member3/evidence/formal/results.json`. The cost chart is also available as `member3/evidence/formal/cost-comparison/update_cost_comparison_en.png` and SVG.

## Offline reproduction

1. Install the existing locked dependencies using the main repository setup instructions.
2. Run `python -X utf8 member3/offline_checks.py`. This verifies/restores the raw archive and blocks real HTTP during tests.
3. Run `python -X utf8 member3_extension/merge_results.py --output-dir outputs/member3-independent-recompute` with a new output directory. It freshly audits all nine batches and recreates 162 scored cases.
4. Compare `cases`, `aggregate`, `usage` and `update_costs` with the published results. Provenance timestamps and local path context can differ; no model rerun is required.

The published 30-repeat cost measurements remain unchanged. Running a new benchmark measures a new machine/load condition; it does not reproduce identical wall times. No local `.env`, installed dependencies, runtime caches, editor state or generated test workspaces are included.

## Historical evidence and current code

The original offline fix validation had 112 passing tests and zero model API requests. Four additional archive-restoration tests cover idempotence, fingerprint tampering, conflicting existing files and path traversal. Fresh publication validation is recorded separately so historical results are not overwritten.

The original execution workspaces and frozen studies preserve historical sources and absolute path strings for traceability. Frozen paid-experiment manifests are historical records, not a portable promise that the old experiment can be resumed after code changes. New paid experiments require a new freeze. Offline auditing uses the correct cohort manifests and the current root postprocessing code.

Source and report fingerprints under `member3/fix_revision_20261030` describe the earlier correction step. Publication adds documentation and evidence-restoration helpers without changing the 162 scores, measured cost samples or current audit algorithms.

## Scope

Only six of the 201 officially selected tasks and three repetitions were evaluated. Full rewrite and selective patch exposed equivalent knowledge in all matched conditions. No human labor or salary saving was measured and no update API fee difference was observed. A real over-update damage case was not observed; the required group failure analysis remains separate work.
