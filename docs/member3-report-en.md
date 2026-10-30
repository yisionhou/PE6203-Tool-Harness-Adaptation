# Member 3 experimental evaluation

Selective patch and full rewrite both achieved TF and ECS of 10.00 on six official tasks. Selective patch rebuilt fewer knowledge entries and used 30.7% less mean processing time in a separate local cost benchmark. No salary or human labor saving was measured.

## Experimental setup

Tasks 3, 24, 28, 90, 144 and 156 were run under Early, Middle and Late with no update, full rewrite and selective patch. Three fresh repetitions produced 162 valid scored conditions; historical pilot scores were excluded. The agent and judge used deepseek-v4-flash-ga-260731. Agent temperature was 0.2, with at most 10 rounds and 4,096 output tokens per round; judge temperature was zero with a 16,384 output-token limit. Tasks, reference labels, input files and scoring protocols were shared across strategies. Nine batches passed fresh fairness audits. Existing run manifests preserve exact configuration and execution-order revisions.

## Metrics and statistics

TF and PE use a 1-10 scale. For each task and repetition, ECS equals the mean of the three version TF scores minus their population standard deviation. Task and repetition ECS values are then averaged with equal weights. Overall uncertainty is the sample standard deviation of three repetition means. Missing planned conditions are retained and make the corresponding aggregate unavailable; missing scores are never replaced by zero. Costs are deduplicated by adaptation.update_id.

## Main results

| Strategy | Valid / planned | TF mean +/- SD | PE mean +/- SD | ECS mean +/- SD |
| --- | --- | --- | --- | --- |
| No update | 54 / 54 | 9.80 +/- 0.03 | 7.44 +/- 0.17 | 9.51 +/- 0.08 |
| Full rewrite | 54 / 54 | 10.00 +/- 0.00 | 7.57 +/- 0.03 | 10.00 +/- 0.00 |
| Selective patch | 54 / 54 | 10.00 +/- 0.00 | 8.02 +/- 0.32 | 10.00 +/- 0.00 |

## Report Table 3 across versions

| Strategy | Early TF | Early PE | Middle TF | Middle PE | Late TF | Late PE | ECS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| No update | 10.00 | 7.50 | 10.00 | 8.28 | 9.39 | 6.56 | 9.51 |
| Full rewrite | 10.00 | 7.06 | 10.00 | 7.78 | 10.00 | 7.89 | 10.00 |
| Selective patch | 10.00 | 8.06 | 10.00 | 8.22 | 10.00 | 7.78 | 10.00 |

Each version mean uses 18 scored conditions per strategy. Both update strategies supplied identical model-visible tools and instructions in 18 of 18 matched task/version pairs; PE differences do not establish an algorithm effect.

## Recovery and retention

| Group | Version | Task count | Runs / strategy | No update | Full rewrite | Selective patch |
| --- | --- | --- | --- | --- | --- | --- |
| Migration diagnostic | Early | 1 | 3 | 10.00 | 10.00 | 10.00 |
| Migration diagnostic | Middle | 1 | 3 | 10.00 | 10.00 | 10.00 |
| Migration diagnostic | Late | 1 | 3 | 6.33 | 10.00 | 10.00 |
| Retention observation | Middle | 5 | 15 | 10.00 | 10.00 | 10.00 |
| Retention observation | Late | 5 | 15 | 10.00 | 10.00 | 10.00 |

The groups above are descriptive and were defined for this summary after the saved study. Task 90 is the confirmed mandatory route-migration diagnostic in Late; Early and Middle provide its reference. The other five tasks form a retention observation group, without claiming that their entire environments were unchanged. Task 24 retained read_text_file; read_file was the removed legacy route. The results show retained TF in this group and restored TF on task 90. They do not prove universal preservation or recovery.

## Update cost

| Strategy | Processing seconds mean +/- SD | Tool records rebuilt | Rule blocks rebuilt | Update tokens / API fee |
| --- | --- | --- | --- | --- |
| No update | 0.1244 +/- 0.0277 | 0 | 0 | 0 / 0 |
| Full rewrite | 0.8849 +/- 0.1335 | 68 | 86 | 0 / 0 |
| Selective patch | 0.6130 +/- 0.1140 | 23 | 34 | 0 / 0 |

The separate offline benchmark used the same computer, one warmup, 30 repetitions and 18 knowledge conditions per repetition. Strategy and condition order were interleaved using seed 6203. Time includes the full adapt() call: input validation, detection, copying, generation, retention checks and final integrity verification. It excludes loading, shared initialization, disk/export, task execution and judging. No-update time is validation/copy overhead, while its rewriting cost remains zero. Error bars are sample SD across 30 repetitions. The 90 strategy/repetition samples preserve the original measurements.

Selective patch used 30.7% less mean processing time, 66.2% fewer rebuilt tool records and 60.5% fewer rebuilt rule blocks than full rewrite. Both achieved TF = 10.00 in the formal task evaluation. All update stages used zero model tokens and zero model API fees, so no update API fee difference was observed. Task inference and judging are separate costs: 2,656,870 recorded agent tokens plus 2,529,342 recorded judge tokens, with three judge requests lacking complete usage receipts. Unknown usage is not treated as zero. No monetary bill, employee hours or salary was measured.

## Real trace and limitations

Task 90 / Late / no update / repetition 1 generated four obsolete get_daily_challenge call errors. Its saved MCP log states "Unknown tool: leetcode_1mcp_get_daily_challenge". Its scores were TF 7, PE 4 and Grounding 7; Late TF across repetitions was 7, 6 and 6. The new route is get_problem(daily=true). Both update strategies achieved Late TF 10.00. Source paths and exact excerpts appear in screenshot 05 and evidence/case-review.json.

No over-update damage was observed in these formal runs. The group assignment still requires a concrete over-update failure analysis; this package does not invent a trajectory to satisfy it. Member 5 and the group must address that gap separately and distinguish any additional diagnostic from the formal study. The six-task subset, three repetitions, use of one model for both agent and judge, changes in execution concurrency and observed clock-service timestamp discrepancies limit generalization. A tool error followed by recovery is not automatically task failure.

## Validation

The saved offline fix validation records 112 passing tests, nine freshly audited batches and zero real HTTP attempts or new model requests. All 162 formal scores and published numerical aggregates remained unchanged. Four regressions were fixed: report rebuilding now preserves the cost figure and measurement table; receipt scores are checked against original response text; imports recompute fairness audits; valid scores are restricted to 1-10. Raw evidence and historical frozen study sources were preserved.

## Two minute presentation script

I was responsible for integrating the three update strategies into a common experiment and evaluation pipeline. We tested six official tasks across Early, Middle and Late environments, using three fresh repetitions for each strategy and condition. This produced 162 valid scored runs, with saved task traces and judge receipts.

We report task fulfillment, planning effectiveness, cross-version ECS and knowledge-update cost. No update achieved TF 9.80 and ECS 9.51. Full rewrite and selective patch both achieved TF and ECS of 10.00. Task 90 provides a real migration example: the Late environment removed the old daily-challenge route. No update kept calling it, while updated knowledge supplied the replacement route.

Selective patch rebuilt 23 tool records and 34 rule blocks, compared with 68 and 86 for full rewrite. In a separate same-machine benchmark with 30 repetitions, its average processing time was 0.6130 seconds, compared with 0.8849 seconds for full rewrite, a reduction of 30.7 percent. These are program processing times, not employee hours or salary savings.

The two update strategies exposed identical knowledge in all 18 matched conditions, so their small planning-score difference does not establish an algorithm advantage. We did not observe over-update damage in the formal runs. The supported conclusion is that selective patch matched task completion with a smaller rebuild scope and lower measured local processing time in this implementation.
