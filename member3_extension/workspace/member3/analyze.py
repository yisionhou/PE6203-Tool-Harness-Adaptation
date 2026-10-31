"""Audit raw runs against judge receipts and export reproducible result tables.

Only Python's standard library is required. Archived pilot evidence stays separate
from newly collected repetitions. Missing scores never become zero or vanish.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import itertools
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from member1.protocol import canonical_hash
from member1.read_results import read_results

STRATEGIES = ('no_update', 'full_rewrite', 'selective_patch')
VERSIONS = ('Early', 'Middle', 'Late')
METRICS = ('task_fulfillment', 'planning_and_efficiency', 'grounding')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                   allow_nan=False) + '\n', encoding='utf-8')


def bounded(base, relative):
    path = (Path(base).resolve() / relative).resolve()
    if not path.is_relative_to(Path(base).resolve()):
        raise ValueError('Evidence path escapes its batch')
    return path


def valid_scores(scores):
    return isinstance(scores, dict) and all(
        type(scores.get(k)) in (int, float) and math.isfinite(scores[k])
        and 0 <= scores[k] <= 10 for k in METRICS)


def aggregate(rows, task_ids, repetitions):
    """Aggregate only a complete prespecified design; retain observed summaries."""
    expected = set(itertools.product(range(1, repetitions + 1), STRATEGIES,
                                     VERSIONS, task_ids))
    keys = [(r['repeat'], r['strategy'], r['version'], r['task_id']) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate repetition/strategy/version/task')
    if not set(keys) <= expected:
        raise ValueError('Unexpected cases outside the prespecified design')
    indexed = dict(zip(keys, rows))
    summaries, task_ecs = {}, []
    for strategy in STRATEGIES:
        group = [indexed.get(k) for k in sorted(expected) if k[1] == strategy]
        complete = all(r is not None and valid_scores(r.get('scores')) for r in group)
        observed = [r for r in group if r and valid_scores(r.get('scores'))]
        metrics = {}
        for metric in METRICS:
            values = [r['scores'][metric] for r in observed]
            metrics[metric] = {
                'mean': statistics.mean(values) if complete else None,
                'observed_mean': statistics.mean(values) if values else None,
                'observed_n': len(values), 'expected_n': len(group),
                'repeat_means': [], 'repeat_sample_sd': None,
            }
            if complete:
                repeat_means = [statistics.mean(r['scores'][metric] for r in group
                                if r['repeat'] == rep) for rep in range(1, repetitions + 1)]
                metrics[metric]['repeat_means'] = repeat_means
                metrics[metric]['repeat_sample_sd'] = (
                    statistics.stdev(repeat_means) if repetitions > 1 else None)
        for repeat, task in itertools.product(range(1, repetitions + 1), task_ids):
            triplet = [indexed.get((repeat, strategy, v, task)) for v in VERSIONS]
            missing = [v for v, r in zip(VERSIONS, triplet)
                       if r is None or not valid_scores(r.get('scores'))]
            values = [r['scores']['task_fulfillment'] for r in triplet] if not missing else []
            task_ecs.append({'strategy': strategy, 'repeat': repeat, 'task_id': task,
                'ecs': statistics.mean(values) - statistics.pstdev(values) if values else None,
                'missing_versions': missing})
        ecs = [r['ecs'] for r in task_ecs if r['strategy'] == strategy]
        ecs_repeat_means = [statistics.mean(r['ecs'] for r in task_ecs
                            if r['strategy'] == strategy and r['repeat'] == rep)
                            for rep in range(1, repetitions + 1)] if all(v is not None for v in ecs) else []
        summaries[strategy] = {'complete': complete, 'metrics': metrics,
            'ecs_mean': statistics.mean(ecs) if all(v is not None for v in ecs) else None,
            'ecs_repeat_means': ecs_repeat_means,
            'ecs_repeat_sample_sd': statistics.stdev(ecs_repeat_means) if len(ecs_repeat_means) > 1 else None,
            'expected_cases': len(group), 'scored_cases': len(observed)}
    missing = [dict(zip(('repeat', 'strategy', 'version', 'task_id'), k))
               for k in sorted(expected - set(keys))]
    return {'strategies': summaries, 'task_ecs': task_ecs, 'absent_cases': missing}


def audit_batch(live, scoring, repeat):
    live, scoring = Path(live).resolve(), Path(scoring).resolve()
    comparison, evaluation = read(live/'comparison.json'), read(scoring/'evaluation.json')
    protocol = read(scoring/'protocol.json')
    supplied_hash = protocol.pop('sha256')
    if canonical_hash(protocol) != supplied_hash or evaluation['protocol_sha256'] != supplied_hash:
        raise ValueError('Judge protocol fingerprint mismatch')
    protocol['sha256'] = supplied_hash
    if protocol['trajectory_policy'] != 'model_visible_tool_results_v2':
        raise ValueError('Only the corrected model-visible judge protocol is accepted')
    rows = list(read_results(live))
    by_key = {(r['strategy'], r['version'], r['task_id']): r for r in rows}
    if len(by_key) != len(rows):
        raise ValueError('Duplicate raw run')
    expected = set(itertools.product(STRATEGIES, VERSIONS, comparison['task_ids']))
    if set(by_key) != expected:
        raise ValueError('Raw batch is incomplete or has unexpected conditions')
    judged = {(r['strategy'], r['version'], r['task_id']): r for r in evaluation['cases']}
    if len(judged) != len(evaluation['cases']) or set(judged) != expected:
        raise ValueError('Judge manifest does not match raw batch')
    results, usage = [], Counter()
    source_hashes = {}
    for path in (live/'comparison.json', scoring/'evaluation.json', scoring/'protocol.json'):
        source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    for key, raw in by_key.items():
        item = judged[key]
        if raw['read_errors'] or canonical_hash(raw) != item['source_record_sha256']:
            raise ValueError(f'Raw evidence differs from judge input: {key}')
        summary = raw['summary']
        if summary['mode'] != 'live_model' or summary['run_config_sha256'] != comparison['run_config_sha256']:
            raise ValueError(f'Wrong execution mode/config: {key}')
        if canonical_hash(comparison['run_config']) != comparison['run_config_sha256']:
            raise ValueError('Run config fingerprint mismatch')
        inp = comparison['inputs']['/'.join(map(str, key))]
        if hashlib.sha256(bounded(live, inp['snapshot']).read_bytes()).hexdigest() != inp['sha256']:
            raise ValueError(f'Knowledge fingerprint mismatch: {key}')
        if summary['knowledge']['sha256'] != inp['sha256']:
            raise ValueError('Run knowledge does not match frozen input')
        prompts = item['prompts']
        receipts = []
        for index, prompt in enumerate(prompts, 1):
            prompt_path = bounded(scoring, prompt['path'])
            # Match the producer's hash of UTF-8 text before Windows CRLF IO.
            if hashlib.sha256(prompt_path.read_text(encoding='utf-8').encode('utf-8')).hexdigest() != prompt['sha256']:
                raise ValueError('Judge prompt fingerprint mismatch')
            receipt_path = prompt_path.parent / f'judge-{index}.json'
            receipt = read(receipt_path) if receipt_path.exists() else {
                'status': 'not_requested', 'error': 'No judge receipt; request not recorded'}
            if receipt_path.exists() and (receipt['protocol_sha256'] != supplied_hash or receipt['prompt_sha256'] != prompt['sha256']):
                raise ValueError('Judge receipt fingerprint mismatch')
            receipts.append(receipt)
            usage.update({'judge_' + k: v for k, v in (receipt.get('usage') or {}).items()
                          if type(v) is int and k in ('prompt_tokens', 'completion_tokens', 'total_tokens')})
        scores = None
        if item['judge_status'] == 'completed':
            if not receipts or not all(r['status'] == 'completed' and valid_scores(r.get('scores')) for r in receipts):
                raise ValueError('Completed judge case has no valid receipts')
            scores = {k: statistics.mean(r['scores'][k] for r in receipts) for k in METRICS}
            if scores != item['scores']:
                raise ValueError('Aggregated scores disagree with raw judge receipts')
        for event in raw['events']:
            if event['event'] == 'model_usage':
                usage.update({'task_' + k: v for k, v in event['data'].items()
                              if type(v) is int and k in ('prompt_tokens', 'completion_tokens', 'total_tokens')})
        results.append({'repeat': repeat, 'strategy': key[0], 'version': key[1],
            'task_id': key[2], 'run_id': summary['run_id'], 'run_status': raw['status'],
            'judge_status': item['judge_status'], 'scores': scores,
            'tool_calls': summary.get('tool_calls'), 'case_id': item['case_id'],
            'source_record_sha256': item['source_record_sha256'],
            'missing_reason': None if scores else [r.get('error', r.get('finish_reason', r['status'])) for r in receipts]})
    for task in comparison['task_ids']:
        hashes = {comparison['inputs'][f'no_update/{v}/{task}']['sha256'] for v in VERSIONS}
        if len(hashes) != 1:
            raise ValueError('Frozen no-update baseline differs across versions')
    return results, dict(usage), protocol, comparison['run_config'], source_hashes


def update_costs(adaptation):
    seen, totals = {}, {s: Counter() for s in STRATEGIES}
    for path in sorted((Path(adaptation)/'updates').rglob('*.json')):
        rec = read(path)
        signature = (rec['strategy'], rec['task_id'], rec['update_cost'])
        uid = rec['update_id']
        if uid in seen:
            if seen[uid] != signature:
                raise ValueError('Inconsistent duplicate update_id')
            continue
        seen[uid] = signature
        totals[rec['strategy']].update(rec['update_cost'])
        totals[rec['strategy']].update({'unique_updates': 1,
            'regenerated_tools': len(rec.get('regenerated_tools', [])),
            'regenerated_blocks': len(rec.get('regenerated_blocks', []))})
    if not seen:
        raise ValueError('No update records found')
    return {s: dict(v) for s, v in totals.items()}


def render_report(result):
    def fmt(v): return 'NA' if v is None else f'{v:.2f}'
    lines = ['# 成员 3：评测结果与证据核对', '',
        f"数据用途：**{result['label']}**。实际纳入 {len(result['cases'])} 条任务记录；"
        f"计划重复 {result['expected_repetitions']} 次。", '',
        'NA 表示预定条件不完整，不填零、不删案例。observed_mean 仅在 JSON 中保留为探索性描述。', '',
        '| 策略 | 有效/预定 | 平均 TF | 平均 PE | 平均 ECS |',
        '| --- | ---: | ---: | ---: | ---: |']
    for s, v in result['aggregate']['strategies'].items():
        m = v['metrics']
        lines.append(f"| {s} | {v['scored_cases']}/{v['expected_cases']} | {fmt(m['task_fulfillment']['mean'])} | {fmt(m['planning_and_efficiency']['mean'])} | {fmt(v['ecs_mean'])} |")
    lines += ['', 'ECS 按每个任务、每次重复计算：三版本 TF 均值减总体标准差；再对预定任务与重复等权平均。',
        '重复波动使用各次重复均值的样本标准差；只有一次运行时不报告重复波动。', '',
        '## 更新成本（按 update_id 去重）', '',
        '| 策略 | 更新 token | 更新时间/秒 | 重建工具 | 重建规则 |',
        '| --- | ---: | ---: | ---: | ---: |']
    for s, c in result['update_costs'].items():
        lines.append(f"| {s} | {c.get('tokens', 0)} | {c.get('seconds', 0):.6f} | {c.get('regenerated_tools', 0)} | {c.get('regenerated_blocks', 0)} |")
    lines += ['', '更新时间不含磁盘读写、共同初始化、任务推理和评分。历史单次时间不能解释为稳定加速比例。', '',
        '## 缺失评分', '']
    for r in result['cases']:
        if r['scores'] is None:
            lines.append(f"- repeat {r['repeat']} / {r['case_id']}: {r['judge_status']}; {r['missing_reason']}")
    lines += ['', '## 使用限制', '',
        '本扩充批次为官方任务 3 与 24；任务 24 在 Late 存在必需读档工具删除及迁移。',
        '请依据实际轨迹核对迁移成败；全量与选择性知识等价时不能由随机差异推出方法优劣。',
        '时钟服务曾出现一小时不一致；正式时钟实验前需检查服务输出。',
        '未执行的重复或扩充任务不会出现在实际结果中。', '',
        '## 已记录用量', '', '```json', json.dumps(result['usage'], ensure_ascii=False, indent=2), '```', '',
        '用量来自保存的 model_usage 与 judge 回执；无回执请求的未知费用不视为零。', '',
        '## 逐条件结果', '', '| 重复 | 策略 | 版本 | 任务 | TF | PE | 工具调用 | 评分状态 |',
        '| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |']
    for r in result['cases']:
        scores = r['scores'] or {}
        lines.append(f"| {r['repeat']} | {r['strategy']} | {r['version']} | {r['task_id']} | {fmt(scores.get('task_fulfillment'))} | {fmt(scores.get('planning_and_efficiency'))} | {r['tool_calls']} | {r['judge_status']} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', type=Path, action='append', required=True)
    parser.add_argument('--scoring', type=Path, action='append', required=True)
    parser.add_argument('--adaptation', type=Path, required=True)
    parser.add_argument('--task-ids', type=int, nargs='+', required=True)
    parser.add_argument('--expected-repetitions', type=int, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if len(args.live) != len(args.scoring) or not 1 <= len(args.live) <= args.expected_repetitions:
        parser.error('Provide paired live/scoring directories within the repetition count')
    if len(set(args.task_ids)) != len(args.task_ids) or not args.task_ids:
        parser.error('Task IDs must be unique')
    cases, usage, hashes = [], Counter(), {}
    protocols, configs, run_ids = set(), set(), set()
    for rep, (live, scoring) in enumerate(zip(args.live, args.scoring), 1):
        rows, cost, protocol, config, source_hashes = audit_batch(live, scoring, rep)
        for row in rows:
            if row['run_id'] in run_ids:
                raise ValueError('A historical run was reused as a new repetition')
            run_ids.add(row['run_id'])
        cases.extend(rows); usage.update(cost); hashes.update(source_hashes)
        protocols.add(protocol['sha256']); configs.add(canonical_hash(config))
    if len(protocols) != 1 or len(configs) != 1:
        raise ValueError('Mixed task or judge protocols cannot be pooled')
    result = {'schema_version': 1, 'label': args.label,
        'expected_repetitions': args.expected_repetitions, 'task_ids': args.task_ids,
        'aggregate': aggregate(cases, args.task_ids, args.expected_repetitions),
        'cases': cases, 'usage': dict(usage), 'update_costs': update_costs(args.adaptation),
        'judge_protocol_sha256': next(iter(protocols)), 'run_config_sha256': next(iter(configs)),
        'source_sha256': hashes,
        'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'audit': 'passed: raw record, frozen knowledge, prompt and judge receipt fingerprints verified'}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    save(args.output_dir/'results.json', result)
    report = render_report(result)
    (args.output_dir/'report.md').write_text(report, encoding='utf-8')
    (args.output_dir/'report.html').write_text('<!doctype html><html lang="zh"><meta charset="utf-8">'
        '<title>Member 3 results</title><style>body{max-width:1100px;margin:40px auto;padding:20px;'
        'font:16px/1.6 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
        '<pre>'+html.escape(report)+'</pre></html>', encoding='utf-8')
    print(json.dumps({'audit': 'passed', 'actual_cases': len(cases), 'output': str(args.output_dir)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
