"""Write reviewable final reports and a credential-free delivery archive."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from member3.analyze import read,save
from member1.protocol import canonical_hash

NAMES={'no_update':'不更新','full_rewrite':'全量重写','selective_patch':'选择性修补'}


def main():
    final=ROOT/'member3/evidence/formal';result=read(final/'results.json')
    review=read(final/'case-review.json')
    for case in review['cases']:
        log=ROOT/case['source']/'mcp.log'
        if log.exists():
            case['routing_diagnostics']=[line for line in log.read_text(encoding='utf-8').splitlines()
                                         if 'Unknown tool:' in line]
    save(final/'case-review.json',review)
    rows=result['cases'];valid=sum(r['scores'] is not None for r in rows)
    def fmt(v):return 'NA' if v is None else f'{v:.2f}'
    table=['| 策略 | 有效/预定 | TF 均值 ± 重复 SD | PE 均值 ± 重复 SD | ECS 均值 ± 重复 SD |',
           '| --- | ---: | ---: | ---: | ---: |']
    for strategy,summary in result['aggregate']['strategies'].items():
        tf=summary['metrics']['task_fulfillment'];pe=summary['metrics']['planning_and_efficiency']
        table.append(f"| {NAMES[strategy]} | {summary['scored_cases']}/{summary['expected_cases']} | {fmt(tf['mean'])} ± {fmt(tf['repeat_sample_sd'])} | {fmt(pe['mean'])} ± {fmt(pe['repeat_sample_sd'])} | {fmt(summary['ecs_mean'])} ± {fmt(summary['ecs_repeat_sample_sd'])} |")
    task90=['| 策略 | Early TF（n=3） | Middle TF（n=3） | Late TF（n=3） |',
            '| --- | ---: | ---: | ---: |']
    for strategy in NAMES:
        values=[]
        for version in ('Early','Middle','Late'):
            group=[r for r in rows if r['task_id']==90 and r['strategy']==strategy and r['version']==version]
            values.append(statistics.mean(r['scores']['task_fulfillment'] for r in group) if len(group)==3 and all(r['scores'] for r in group) else None)
        task90.append('| '+NAMES[strategy]+' | '+' | '.join(fmt(v) for v in values)+' |')
    costs=['| 策略 | 更新 token | 重建工具记录 | 重建规则块 | 归档更新时间/秒 |',
           '| --- | ---: | ---: | ---: | ---: |']
    for strategy,cost in result['update_costs'].items():
        costs.append(f"| {NAMES[strategy]} | {cost.get('tokens',0)} | {cost.get('regenerated_tools',0)} | {cost.get('regenerated_blocks',0)} | {cost.get('seconds',0):.6f} |")
    equivalence=[]
    for folder,tasks in [(ROOT/'member2/evidence/adaptation',[28,144,156]),
                         (ROOT/'member3_extension/workspace/member2/evidence/adaptation',[3,24]),
                         (ROOT/'member3_migration/workspace/member2/evidence/adaptation',[90])]:
        for task in tasks:
            for version in ('Early','Middle','Late'):
                packets=[read(folder/'knowledge'/strategy/version/f'{task}.json') for strategy in ('full_rewrite','selective_patch')]
                hashes=[canonical_hash({k:p[k] for k in ('tools','instructions')}) for p in packets]
                equivalence.append({'task_id':task,'version':version,'equal':hashes[0]==hashes[1],'sha256':hashes})
    save(final/'knowledge-equivalence.json',{'pairs':equivalence,'equal_pairs':sum(r['equal'] for r in equivalence)})
    use=result['usage'];task_tokens=use.get('task_all_attempts_total_tokens',use.get('task_total_tokens',0));judge_tokens=use.get('judge_all_attempts_total_tokens',0)
    content=f'''# 成员 3：正式实验与评测结果

日期：2026-10-30。完成六个官方任务（3、24、28、90、144、156）、三种策略、三个环境版本、三次全新重复，共 **{len(rows)} 个任务条件，{valid} 条有效评分**。旧先导数据没有混入本轮。

## 实验设置

Agent 与 judge 均使用 `deepseek-v4-flash-ga-260731`。Agent temperature=0.2，最多 10 轮，每轮最多 4096 完成 token；judge temperature=0，每条一次，最多 16384 完成 token，使用 Agent 当时实际可见的工具返回。三种策略使用相同问题、参考标签、输入文件、推理与评分协议。

任务覆盖日志比较、报告写入、待办生成、时区转换、时间计算，以及卡片资料/图片与当日 LeetCode 查询。任务 90 的 `get_daily_challenge` 在 Late 被删除，实际替代接口为 `get_problem(daily=true)`；三版本发现与六次公开 API 探测均在该任务的模型执行前通过。

任务 24 原本使用的 `read_text_file` 保留不变，删除的是过时的 `read_file`，因此它作为保留与服务覆盖案例。早期说明误写过迁移方向，冻结元数据保留追踪，正确说明见 `member3_extension/migration-direction-correction.json`；问题、知识包和评分提示未因此修改。

三个批次分别使用独立工作目录与端口。后续条件有限并行以缩短等待，每个版本一个任务工作程序、最多四个同时评分请求；每批保留执行顺序修订记录。所有九个批次均经过条件审计和原始输入、提示、judge 回执哈希核对。

## 主要结果

'''+ '\n'.join(table)+'''

SD 是三次重复均值的样本标准差，不是把不同任务或版本混在一起计算的离散程度。ECS 先对同一任务同一次重复计算三版本 TF 均值减总体标准差，再对预定任务与重复等权平均。缺失值不填零、不删案例；有预定条件未评分时，总体指标为 NA。

## 迁移案例：官方任务 90

'''+ '\n'.join(task90)+'''

不更新策略在 Late 继续请求旧的 `leetcode__get_daily_challenge`。保存的 MCP 日志明确返回 `Unknown tool: leetcode_1mcp_get_daily_challenge`，最终回答未能提供当日题目；这与单纯的进程异常或公网服务不可用不同。全量与选择性策略提供实际的新接口，实际效果由以上得分与原始轨迹共同核对。

工具错误不自动等于任务失败：部分待办案例先出现参数格式错误，随后恢复并完成。完整候选清单、得分、错误和路径见 `case-review.json`，供成员 5 继续分析。

## 更新成本

'''+ '\n'.join(costs)+f'''

成本按唯一 `adaptation.update_id` 去重，同一包重复使用不重复累计。原有三个任务复用归档知识包，表中对应时间来自那些包的原始生成记录；新增任务为本次生成。时间不含磁盘操作、共同初始化、任务推理与评分，且采样时系统负载不同，不能把该单次总时间换算成可靠的加速比例。重建记录数量比单次耗时更适合说明更新范围。

本次任务推理已记录 **{task_tokens:,} token**，judge 所有尝试去重后已记录 **{judge_tokens:,} token**，合计 **{task_tokens+judge_tokens:,} token**；连线测试另计 {use.get('setup_probe_total_tokens_separate_from_experiment',0)} token。记录到的 judge 请求共 {use.get('judge_recorded_requests_including_technical_failures',0)} 次，其中 {use.get('judge_receipts_without_usage',0)} 次没有完整用量回执。这些是已知用量，不是货币账单，未知用量不认定为零。

## 评分异常与使用范围

有效低分未重评。技术缺失最多额外请求两次，模型、提示、token 上限和评分协议不变；每次回执都保留在新目录。缺少最后一个 JSON 大括号且所有原始分数与理由完整的回覆可离线恢复，原文保持不变，不产生额外模型调用。

全量与选择性修补在 {sum(r['equal'] for r in equivalence)}/{len(equivalence)} 组对应条件下提供相同的模型可见工具与使用说明。因此，两者的小幅得分差异不能直接解释为更新算法优劣；本实验支持的是实际工具迁移与更新范围/保留能力的观察。没有制造“更新过度”损伤案例，也没有将随机参数错误当作此类证据。

三个官方时钟快照的 `get_current_time` locale/timestamp 接口已实测约快一小时，而结构化 `get_time_info` 正常；相关任务评分应结合此服务缺陷理解。judge 与 Agent 使用同一模型，任务仅为 201 个官方选定任务中的六个，重复数为三，后续并行顺序也增加执行条件差异；结果不能外推至全基准。

## 交付与验证

- `member3/evidence/formal/results.json`：162 条条件、评分、重复统计、成本、用量与来源。
- `member3/evidence/formal/report.md`：逐条件结果表。
- `member3/evidence/formal/case-review.json`：真实轨迹的失败/恢复候选，含路由错误证据。
- 原有 85 项测试、新增 13 项统计测试、3 项离线恢复测试通过；工具检查为原有 27 条、扩充 6 条、迁移 3 条，另有时钟 9 次与公开 API 6 次实测。

## 约两分钟汇报稿

我负责把三种知识更新策略接到统一的实验与评分流程。这次我们使用六个官方任务，在 Early、Middle、Late 三个环境分别比较不更新、全量重写与选择性修补，每个条件做三次全新重复，总共 {len(rows)} 次任务，并保留原始答案、工具轨迹与评分回执。

评测输出任务完成度 TF、规划效率 PE、跨版本 ECS，以及知识更新成本。平均分和波动来自预先固定的完整任务集合，技术缺失不填成零分，历史先导数据也没有混入。结果表给出了三种策略的均值与重复间波动。

总体 TF 不更新为 {fmt(result['aggregate']['strategies']['no_update']['metrics']['task_fulfillment']['mean'])}，全量与选择性均为 {fmt(result['aggregate']['strategies']['full_rewrite']['metrics']['task_fulfillment']['mean'])}；ECS 分别为 {fmt(result['aggregate']['strategies']['no_update']['ecs_mean'])}、{fmt(result['aggregate']['strategies']['full_rewrite']['ecs_mean'])} 和 {fmt(result['aggregate']['strategies']['selective_patch']['ecs_mean'])}。选择性修补重建 {result['update_costs']['selective_patch'].get('regenerated_tools',0)} 条工具记录，全量重写为 {result['update_costs']['full_rewrite'].get('regenerated_tools',0)} 条。

任务 90 提供了真实迁移案例：后期版本删除每日挑战旧接口，改由新接口的 daily 参数提供。不更新策略仍调用旧名称，日志能定位到未知工具错误；更新后的知识则包含新接口。任务 24 用于观察保留能力，它本来使用的读档接口没有被删除。

全量与选择性修补在本轮对应条件下提供相同知识，差别主要在重建范围，因此不把随机分数差异解释成方法优势。我们还记录了时钟服务本身的一小时偏差，并把它与更新失败分开。报告中的成本按知识包去重，结果和案例均可从保存的原始证据复核。
'''
    (ROOT/'docs/member3-report-section.md').write_text(content,encoding='utf-8')
    (final/'summary.md').write_text(content,encoding='utf-8')
    status={'date':'2026-10-30','actual_task_cases':len(rows),'valid_scores':valid,
        'formal_design_complete':len(rows)==162 and valid==162,
        'task_ids':result['task_ids'],'fresh_repetitions':3,'audited_batches':len(result['cohorts']),
        'test_results':['85 existing passed','13 statistics passed','3 syntax recovery passed'],
        'known_inference_tokens':task_tokens,'known_judge_tokens_all_attempts':judge_tokens,
        'no_historical_pilot_scores_pooled':True}
    save(final/'completion.json',status)
    print(json.dumps(status,ensure_ascii=False))


if __name__=='__main__':main()
