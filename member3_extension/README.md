# Expanded tasks and shared postprocessing

This directory contains the tasks 3/24 cohort and the current six-task result aggregation and cost-reporting implementation. The cohort produced 54 valid scores; the full study produced 162.

- `merge_results.py`: restore evidence first, then freshly audit all nine batches and aggregate TF, PE, ECS, recorded usage and deduplicated update costs.
- `benchmark_update_cost.py`: perform a separate local 30-repeat benchmark with no model calls. Existing published measurements remain in `member3/evidence/formal/cost-comparison/benchmark.json`; new measurements are a separate run.
- `cost_report.py`: share cost-section rendering and verify figure/benchmark fingerprints before publication.
- `plot_update_cost.py` and `deliver.py`: rebuild the historical report while retaining the measured cost figure and table. The historical report text is in Chinese; English submission documents are under `docs/member3-report-en.*`.
- Other scripts: original setup, bounded execution scheduling, progress monitoring and technical judge recovery. Execution scripts can call paid models and are not used by the offline validation command.

`workspace/` is a historical execution workspace, not a second supported source tree. Frozen source copies, task manifests, snapshots and knowledge are preserved byte-for-byte. Original model inputs and labels were not translated or modified.

Task 24 retained `read_text_file`; the deleted legacy tool was `read_file`. It is a retention/service-coverage case, not mandatory migration. The historical direction correction is recorded in `migration-direction-correction.json`. Task 90 supplies the confirmed mandatory migration case in the separate migration cohort.

See [Member 3 README](../member3/README.md) for offline reproduction and limitations.
