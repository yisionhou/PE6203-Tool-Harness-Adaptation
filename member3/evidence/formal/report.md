# 成员 3：评测结果与证据核对

数据用途：**six-official-task-three-fresh-repetition-study**。实际纳入 162 条任务记录；计划重复 3 次。

NA 表示预定条件不完整，不填零、不删案例。observed_mean 仅在 JSON 中保留为探索性描述。

| 策略 | 有效/预定 | 平均 TF | 平均 PE | 平均 ECS |
| --- | ---: | ---: | ---: | ---: |
| no_update | 54/54 | 9.80 | 7.44 | 9.51 |
| full_rewrite | 54/54 | 10.00 | 7.57 | 10.00 |
| selective_patch | 54/54 | 10.00 | 8.02 | 10.00 |

ECS 按每个任务、每次重复计算：三版本 TF 均值减总体标准差；再对预定任务与重复等权平均。
重复波动使用各次重复均值的样本标准差；只有一次运行时不报告重复波动。

## 更新成本（按 update_id 去重）

| 策略 | 更新 token | 更新时间/秒 | 重建工具 | 重建规则 |
| --- | ---: | ---: | ---: | ---: |
| no_update | 0 | 0.000000 | 0 | 0 |
| full_rewrite | 0 | 1.722880 | 68 | 86 |
| selective_patch | 0 | 1.085716 | 23 | 34 |

更新时间不含磁盘读写、共同初始化、任务推理和评分。历史单次时间不能解释为稳定加速比例。

## 缺失评分


## 使用限制

正式任务集包含 3、24、28、90、144、156；任务 90 的 Late 版本删除 get_daily_challenge，需迁移到 get_problem(daily=true)。任务 24 保留原有 read_text_file，是保留能力对照。
这份表只汇总本次全新运行；不含历史先导分数。全量与选择性知识若等价，不因随机分数差异认定某方法更优。
时钟服务曾出现一小时不一致；正式时钟实验前需检查服务输出。
未执行的重复或扩充任务不会出现在实际结果中。

## 已记录用量

```json
{
  "judge_completion_tokens": 1060148,
  "judge_prompt_tokens": 1292652,
  "judge_total_tokens": 2352800,
  "task_completion_tokens": 252356,
  "task_prompt_tokens": 2404514,
  "task_total_tokens": 2656870,
  "task_all_attempts_total_tokens": 2656870,
  "superseded_account_aborted_task_attempts": 4,
  "judge_all_attempts_completion_tokens": 1189812,
  "judge_all_attempts_prompt_tokens": 1339530,
  "judge_all_attempts_total_tokens": 2529342,
  "judge_recorded_requests_including_technical_failures": 175,
  "judge_receipts_without_usage": 3,
  "setup_probe_total_tokens_separate_from_experiment": 94
}
```

用量来自保存的 model_usage 与 judge 回执；无回执请求的未知费用不视为零。

## 逐条件结果

| 重复 | 策略 | 版本 | 任务 | TF | PE | 工具调用 | 评分状态 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | no_update | Early | 28 | 10.00 | 8.00 | 5 | completed |
| 1 | full_rewrite | Early | 28 | 10.00 | 7.00 | 5 | completed |
| 1 | selective_patch | Early | 28 | 10.00 | 7.00 | 5 | completed |
| 1 | no_update | Early | 144 | 10.00 | 5.00 | 4 | completed |
| 1 | full_rewrite | Early | 144 | 10.00 | 5.00 | 4 | completed |
| 1 | selective_patch | Early | 144 | 10.00 | 10.00 | 2 | completed |
| 1 | no_update | Early | 156 | 10.00 | 5.00 | 3 | completed |
| 1 | full_rewrite | Early | 156 | 10.00 | 5.00 | 3 | completed |
| 1 | selective_patch | Early | 156 | 10.00 | 5.00 | 3 | completed |
| 1 | no_update | Middle | 28 | 10.00 | 7.00 | 5 | completed |
| 1 | full_rewrite | Middle | 28 | 10.00 | 10.00 | 5 | completed |
| 1 | selective_patch | Middle | 28 | 10.00 | 10.00 | 5 | completed |
| 1 | no_update | Middle | 144 | 10.00 | 10.00 | 2 | completed |
| 1 | full_rewrite | Middle | 144 | 10.00 | 5.00 | 4 | completed |
| 1 | selective_patch | Middle | 144 | 10.00 | 5.00 | 4 | completed |
| 1 | no_update | Middle | 156 | 10.00 | 4.00 | 3 | completed |
| 1 | full_rewrite | Middle | 156 | 10.00 | 5.00 | 3 | completed |
| 1 | selective_patch | Middle | 156 | 10.00 | 5.00 | 3 | completed |
| 1 | no_update | Late | 28 | 10.00 | 7.00 | 5 | completed |
| 1 | full_rewrite | Late | 28 | 10.00 | 10.00 | 5 | completed |
| 1 | selective_patch | Late | 28 | 10.00 | 10.00 | 5 | completed |
| 1 | no_update | Late | 144 | 10.00 | 5.00 | 4 | completed |
| 1 | full_rewrite | Late | 144 | 10.00 | 5.00 | 4 | completed |
| 1 | selective_patch | Late | 144 | 10.00 | 5.00 | 4 | completed |
| 1 | no_update | Late | 156 | 10.00 | 10.00 | 2 | completed |
| 1 | full_rewrite | Late | 156 | 10.00 | 10.00 | 2 | completed |
| 1 | selective_patch | Late | 156 | 10.00 | 5.00 | 3 | completed |
| 2 | no_update | Late | 28 | 10.00 | 10.00 | 4 | completed |
| 2 | no_update | Middle | 28 | 10.00 | 5.00 | 6 | completed |
| 2 | no_update | Early | 28 | 10.00 | 10.00 | 5 | completed |
| 2 | full_rewrite | Late | 28 | 10.00 | 7.00 | 6 | completed |
| 2 | full_rewrite | Middle | 28 | 10.00 | 10.00 | 4 | completed |
| 2 | full_rewrite | Early | 28 | 10.00 | 10.00 | 6 | completed |
| 2 | selective_patch | Late | 28 | 10.00 | 7.00 | 5 | completed |
| 2 | selective_patch | Middle | 28 | 10.00 | 10.00 | 5 | completed |
| 2 | selective_patch | Early | 28 | 10.00 | 10.00 | 5 | completed |
| 2 | no_update | Late | 144 | 10.00 | 5.00 | 4 | completed |
| 2 | no_update | Early | 144 | 10.00 | 4.00 | 4 | completed |
| 2 | no_update | Middle | 144 | 10.00 | 5.00 | 4 | completed |
| 2 | full_rewrite | Late | 144 | 10.00 | 10.00 | 2 | completed |
| 2 | full_rewrite | Early | 144 | 10.00 | 5.00 | 4 | completed |
| 2 | full_rewrite | Middle | 144 | 10.00 | 5.00 | 4 | completed |
| 2 | selective_patch | Late | 144 | 10.00 | 5.00 | 4 | completed |
| 2 | selective_patch | Early | 144 | 10.00 | 5.00 | 4 | completed |
| 2 | selective_patch | Middle | 144 | 10.00 | 5.00 | 4 | completed |
| 2 | no_update | Late | 156 | 10.00 | 5.00 | 3 | completed |
| 2 | no_update | Early | 156 | 10.00 | 5.00 | 3 | completed |
| 2 | full_rewrite | Late | 156 | 10.00 | 6.00 | 3 | completed |
| 2 | no_update | Middle | 156 | 10.00 | 10.00 | 2 | completed |
| 2 | full_rewrite | Early | 156 | 10.00 | 5.00 | 3 | completed |
| 2 | selective_patch | Late | 156 | 10.00 | 10.00 | 2 | completed |
| 2 | full_rewrite | Middle | 156 | 10.00 | 5.00 | 3 | completed |
| 2 | selective_patch | Early | 156 | 10.00 | 6.00 | 3 | completed |
| 2 | selective_patch | Middle | 156 | 10.00 | 10.00 | 2 | completed |
| 3 | no_update | Late | 28 | 10.00 | 5.00 | 5 | completed |
| 3 | no_update | Middle | 28 | 10.00 | 8.00 | 6 | completed |
| 3 | no_update | Early | 28 | 10.00 | 10.00 | 5 | completed |
| 3 | full_rewrite | Late | 28 | 10.00 | 7.00 | 5 | completed |
| 3 | full_rewrite | Early | 28 | 10.00 | 10.00 | 5 | completed |
| 3 | full_rewrite | Middle | 28 | 10.00 | 10.00 | 5 | completed |
| 3 | selective_patch | Late | 28 | 10.00 | 10.00 | 7 | completed |
| 3 | selective_patch | Early | 28 | 10.00 | 8.00 | 6 | completed |
| 3 | selective_patch | Middle | 28 | 10.00 | 10.00 | 5 | completed |
| 3 | no_update | Late | 144 | 10.00 | 5.00 | 4 | completed |
| 3 | no_update | Early | 144 | 10.00 | 5.00 | 4 | completed |
| 3 | no_update | Middle | 144 | 10.00 | 5.00 | 4 | completed |
| 3 | full_rewrite | Early | 144 | 10.00 | 6.00 | 3 | completed |
| 3 | full_rewrite | Late | 144 | 10.00 | 5.00 | 3 | completed |
| 3 | full_rewrite | Middle | 144 | 10.00 | 5.00 | 4 | completed |
| 3 | selective_patch | Early | 144 | 10.00 | 5.00 | 4 | completed |
| 3 | selective_patch | Late | 144 | 10.00 | 5.00 | 4 | completed |
| 3 | selective_patch | Middle | 144 | 10.00 | 5.00 | 4 | completed |
| 3 | no_update | Early | 156 | 10.00 | 5.00 | 3 | completed |
| 3 | no_update | Late | 156 | 10.00 | 5.00 | 3 | completed |
| 3 | no_update | Middle | 156 | 10.00 | 10.00 | 2 | completed |
| 3 | full_rewrite | Early | 156 | 10.00 | 5.00 | 3 | completed |
| 3 | full_rewrite | Late | 156 | 10.00 | 5.00 | 3 | completed |
| 3 | full_rewrite | Middle | 156 | 10.00 | 10.00 | 2 | completed |
| 3 | selective_patch | Early | 156 | 10.00 | 10.00 | 2 | completed |
| 3 | selective_patch | Late | 156 | 10.00 | 5.00 | 3 | completed |
| 3 | selective_patch | Middle | 156 | 10.00 | 10.00 | 2 | completed |
| 1 | no_update | Early | 3 | 10.00 | 10.00 | 5 | completed |
| 1 | full_rewrite | Early | 3 | 10.00 | 5.00 | 7 | completed |
| 1 | selective_patch | Early | 3 | 10.00 | 7.00 | 5 | completed |
| 1 | no_update | Early | 24 | 10.00 | 5.00 | 5 | completed |
| 1 | full_rewrite | Early | 24 | 10.00 | 10.00 | 3 | completed |
| 1 | selective_patch | Early | 24 | 10.00 | 10.00 | 3 | completed |
| 1 | no_update | Middle | 3 | 10.00 | 7.00 | 6 | completed |
| 1 | full_rewrite | Middle | 3 | 10.00 | 7.00 | 6 | completed |
| 1 | selective_patch | Middle | 3 | 10.00 | 7.00 | 5 | completed |
| 1 | no_update | Middle | 24 | 10.00 | 10.00 | 3 | completed |
| 1 | full_rewrite | Middle | 24 | 10.00 | 10.00 | 3 | completed |
| 1 | selective_patch | Middle | 24 | 10.00 | 10.00 | 3 | completed |
| 1 | no_update | Late | 3 | 10.00 | 10.00 | 5 | completed |
| 1 | full_rewrite | Late | 3 | 10.00 | 10.00 | 5 | completed |
| 1 | selective_patch | Late | 3 | 10.00 | 10.00 | 4 | completed |
| 1 | no_update | Late | 24 | 10.00 | 10.00 | 3 | completed |
| 1 | full_rewrite | Late | 24 | 10.00 | 7.00 | 4 | completed |
| 1 | selective_patch | Late | 24 | 10.00 | 10.00 | 3 | completed |
| 2 | no_update | Late | 3 | 10.00 | 5.00 | 5 | completed |
| 2 | no_update | Early | 3 | 10.00 | 8.00 | 5 | completed |
| 2 | no_update | Middle | 3 | 10.00 | 8.00 | 6 | completed |
| 2 | full_rewrite | Late | 3 | 10.00 | 10.00 | 5 | completed |
| 2 | full_rewrite | Early | 3 | 10.00 | 5.00 | 6 | completed |
| 2 | full_rewrite | Middle | 3 | 10.00 | 7.00 | 5 | completed |
| 2 | selective_patch | Late | 3 | 10.00 | 7.00 | 5 | completed |
| 2 | selective_patch | Early | 3 | 10.00 | 10.00 | 5 | completed |
| 2 | selective_patch | Middle | 3 | 10.00 | 7.00 | 7 | completed |
| 2 | no_update | Early | 24 | 10.00 | 10.00 | 3 | completed |
| 2 | no_update | Late | 24 | 10.00 | 7.00 | 4 | completed |
| 2 | no_update | Middle | 24 | 10.00 | 10.00 | 3 | completed |
| 2 | full_rewrite | Early | 24 | 10.00 | 10.00 | 3 | completed |
| 2 | full_rewrite | Late | 24 | 10.00 | 10.00 | 3 | completed |
| 2 | full_rewrite | Middle | 24 | 10.00 | 10.00 | 3 | completed |
| 2 | selective_patch | Late | 24 | 10.00 | 10.00 | 3 | completed |
| 2 | selective_patch | Early | 24 | 10.00 | 10.00 | 3 | completed |
| 2 | selective_patch | Middle | 24 | 10.00 | 10.00 | 3 | completed |
| 3 | no_update | Middle | 3 | 10.00 | 10.00 | 5 | completed |
| 3 | no_update | Early | 3 | 10.00 | 5.00 | 5 | completed |
| 3 | no_update | Late | 3 | 10.00 | 6.00 | 6 | completed |
| 3 | full_rewrite | Early | 3 | 10.00 | 5.00 | 5 | completed |
| 3 | full_rewrite | Middle | 3 | 10.00 | 7.00 | 5 | completed |
| 3 | full_rewrite | Late | 3 | 10.00 | 8.00 | 6 | completed |
| 3 | selective_patch | Early | 3 | 10.00 | 10.00 | 5 | completed |
| 3 | selective_patch | Middle | 3 | 10.00 | 10.00 | 5 | completed |
| 3 | selective_patch | Late | 3 | 10.00 | 10.00 | 4 | completed |
| 3 | no_update | Early | 24 | 10.00 | 10.00 | 3 | completed |
| 3 | no_update | Middle | 24 | 10.00 | 10.00 | 3 | completed |
| 3 | no_update | Late | 24 | 10.00 | 10.00 | 3 | completed |
| 3 | full_rewrite | Early | 24 | 10.00 | 10.00 | 3 | completed |
| 3 | full_rewrite | Middle | 24 | 10.00 | 10.00 | 3 | completed |
| 3 | full_rewrite | Late | 24 | 10.00 | 10.00 | 3 | completed |
| 3 | selective_patch | Early | 24 | 10.00 | 7.00 | 4 | completed |
| 3 | selective_patch | Late | 24 | 10.00 | 10.00 | 3 | completed |
| 3 | selective_patch | Middle | 24 | 10.00 | 10.00 | 3 | completed |
| 1 | no_update | Early | 90 | 10.00 | 10.00 | 4 | completed |
| 1 | no_update | Middle | 90 | 10.00 | 10.00 | 4 | completed |
| 1 | no_update | Late | 90 | 7.00 | 4.00 | 7 | completed |
| 1 | full_rewrite | Early | 90 | 10.00 | 10.00 | 4 | completed |
| 1 | full_rewrite | Middle | 90 | 10.00 | 10.00 | 4 | completed |
| 1 | full_rewrite | Late | 90 | 10.00 | 5.00 | 6 | completed |
| 1 | selective_patch | Middle | 90 | 10.00 | 7.00 | 4 | completed |
| 1 | selective_patch | Early | 90 | 10.00 | 8.00 | 4 | completed |
| 1 | selective_patch | Late | 90 | 10.00 | 7.00 | 5 | completed |
| 2 | no_update | Middle | 90 | 10.00 | 10.00 | 4 | completed |
| 2 | no_update | Early | 90 | 10.00 | 10.00 | 4 | completed |
| 2 | no_update | Late | 90 | 6.00 | 4.00 | 7 | completed |
| 2 | full_rewrite | Middle | 90 | 10.00 | 7.00 | 4 | completed |
| 2 | full_rewrite | Late | 90 | 10.00 | 7.00 | 5 | completed |
| 2 | full_rewrite | Early | 90 | 10.00 | 7.00 | 5 | completed |
| 2 | selective_patch | Middle | 90 | 10.00 | 10.00 | 4 | completed |
| 2 | selective_patch | Early | 90 | 10.00 | 7.00 | 4 | completed |
| 2 | selective_patch | Late | 90 | 10.00 | 7.00 | 5 | completed |
| 3 | no_update | Middle | 90 | 10.00 | 10.00 | 4 | completed |
| 3 | no_update | Early | 90 | 10.00 | 10.00 | 4 | completed |
| 3 | no_update | Late | 90 | 6.00 | 5.00 | 6 | completed |
| 3 | full_rewrite | Middle | 90 | 10.00 | 7.00 | 4 | completed |
| 3 | full_rewrite | Late | 90 | 10.00 | 10.00 | 4 | completed |
| 3 | full_rewrite | Early | 90 | 10.00 | 7.00 | 4 | completed |
| 3 | selective_patch | Middle | 90 | 10.00 | 7.00 | 4 | completed |
| 3 | selective_patch | Early | 90 | 10.00 | 10.00 | 4 | completed |
| 3 | selective_patch | Late | 90 | 10.00 | 7.00 | 5 | completed |

## 分组与复现边界

- Tasks 3 and 24 selected before their first model outcomes.
- Original, expanded and migration cohorts use separate runner roots/ports.
- Expanded runner adds only service manifest entries and per-case filesystem argv.
- No historical pilot scores are pooled with these new results.
- Task 24 retains its original read_text_file route; the deleted filesystem route is read_file. Earlier reversed metadata is superseded by migration-direction-correction.json.
- Task 90 selected before its first outcomes; its deleted get_daily_challenge route and get_problem(daily=true) replacement were confirmed by discovery and public API probes.
- Task 24 is a retention control alongside a real route deletion in its service; no claim of no changes anywhere.
- Later independent conditions use bounded parallel execution; model/prompt settings unchanged; execution amendments saved per cohort.
- After explicit user account replenishment, four AccountOverdue-aborted task attempts were replaced in new directories; unchanged successful runs/scores were reused by exact hashes. Failed attempts and their known usage remain archived.
- No method-specific over-update damage is inferred from identical model-visible knowledge.
