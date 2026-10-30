# Member 3 evaluation and experiments

Six official tasks (3, 24, 28, 90, 144 and 156), three strategies, three versions and three fresh repetitions produced **162 valid scored conditions**. Historical pilot scores were excluded.

## Start here

- [English report](../docs/member3-report-en.md)
- [English Word report with editable charts](../docs/member3-report-en.docx)
- [Formal machine-readable results](evidence/formal/results.json)
- [Real trace review candidates](evidence/formal/case-review.json)
- [Saved 30-repeat cost measurements](evidence/formal/cost-comparison/benchmark.json)
- [Publication and reproduction notes](../docs/member3-publication.md)

Full rewrite and selective patch both achieved TF and ECS of 10.00. No update achieved TF 9.80 and ECS 9.51. Selective patch rebuilt 23 tool records and 34 rule blocks, versus 68 and 86 for full rewrite. Its mean local processing time was 30.7% lower in a separate 30-repeat benchmark. This does not measure employee time or salary. All update stages used zero model tokens and zero update API fees.

The updated strategies exposed identical model-visible knowledge in all 18 task/version pairs; their PE difference does not establish an algorithm advantage. No over-update damage was observed in the formal runs. The group must address its required over-update failure analysis separately.

## Offline validation

Install Node.js and Python, then install the pinned dependencies with `npm ci` and `python -m pip install -r member1/requirements-lock.txt`. No API key is required for these commands. From the repository root:

```powershell
python -X utf8 member3/restore_evidence.py --check-only
python -X utf8 member3/offline_checks.py
python -X utf8 member3_extension/merge_results.py --output-dir outputs/member3-independent-recompute
```

The check runner restores exact saved evidence, removes usable model-key environment variables and blocks real HTTP in the tests. It writes a fresh validation record to `.tmp/publication-validation.json`, leaving the historical validation record untouched. The result aggregation requires a new output directory and performs nine fresh fairness audits without model calls.

## Source layout

| Path | Purpose |
| --- | --- |
| `analyze.py` | Original-response score verification, TF/PE/ECS, missing-score policy and update deduplication |
| `experiment.py` | Freeze, preflight and execute the original three-task repetition design |
| `restore_evidence.py` | Verify and restore the archived formal trajectories without overwriting different files |
| `offline_checks.py` | Run the full local test suite with real HTTP disabled |
| `tests/` | Statistics, audit regressions and archive-restoration tests |
| `../member3_extension/` | Tasks 3/24, result merging, recovery, cost measurement and report rendering |
| `../member3_migration/` | Task 90 migration study and pinned snapshots |

The original three-task design, expanded tasks and migration study use separate frozen workspaces. Historical source copies and study manifests are retained for evidence integrity. Current supported postprocessing code is in the root `member3` and `member3_extension` directories. A new model experiment requires a new frozen study; do not reuse old source hashes as if they described a modified execution.

## Raw evidence

`evidence/raw-runs.zip` stores 4,115 exact raw files once, avoiding thousands of generated files in the source tree. The adjacent SHA-256 file and internal manifest are checked before restoration. Repeated restoration is idempotent; differing existing evidence is rejected. The selected-run files preserve account-recovery choices, failed attempts and judge retries. Valid low scores were never discarded or rescored.

The archive restores `outputs/member3-replication-v2`, `member3_extension/workspace/outputs/member3-expansion-v1` and `member3_migration/workspace/outputs/member3-migration-v1`. Installed dependencies, local credentials and runtime state are excluded.
