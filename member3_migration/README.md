# Task 90 migration cohort

This cohort uses official task 90, pinned Early/Middle/Late service snapshots and three fresh repetitions. It produced 27 valid scored conditions.

The Late snapshot removes `get_daily_challenge`; its replacement is `get_problem(daily=true)`. No update retained the obsolete route and achieved Late TF 6.33. Full rewrite and selective patch both achieved Late TF 10.00. Saved router diagnostics identify the unknown old tool route.

`configure.py` and `prepare.py` record setup and service probing. `recover_account.py` documents the bounded recovery of account-blocked runs. These historical execution operations are distinct from offline result auditing and can invoke external services or paid models when explicitly run.

`workspace/` contains preserved manifests, knowledge and historical execution sources. Run `python member3/restore_evidence.py` at the repository root to restore the compressed raw traces. Do not modify frozen history to match current postprocessing code.
