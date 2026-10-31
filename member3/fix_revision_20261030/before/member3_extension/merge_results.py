"""Audit disjoint task cohorts and aggregate the prespecified five-task design."""
from collections import Counter
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from member3.analyze import audit_batch, aggregate, update_costs, read, save, render_report
from member1.protocol import canonical_hash


def main(output_dir=None):
    output = Path(output_dir).resolve() if output_dir else ROOT/'member3/evidence/formal'
    cohorts = [
        ('original', ROOT/'outputs/member3-replication-v2', ROOT/'member2/evidence/adaptation', [28,144,156]),
        ('expanded', ROOT/'member3_extension/workspace/outputs/member3-expansion-v1',
         ROOT/'member3_extension/workspace/member2/evidence/adaptation', [3,24]),
        ('migration', ROOT/'member3_migration/workspace/outputs/member3-migration-v1',
         ROOT/'member3_migration/workspace/member2/evidence/adaptation', [90]),
    ]
    cases, usage, hashes, protocols, configs = [], Counter(), {}, set(), set()
    cost = {s:Counter() for s in ('no_update','full_rewrite','selective_patch')}
    provenance, failures, ids = [], [], set()
    all_judge_receipts={}
    for name, base, adaptation, task_ids in cohorts:
        for file in base.glob('repeat-*/scoring*/cases/*/judge-*.json'):
            receipt=read(file)
            identity=receipt.get('response_id') or canonical_hash(receipt)
            all_judge_receipts[identity]=receipt
        for strategy, value in update_costs(adaptation).items(): cost[strategy].update(value)
        for repeat in (1,2,3):
            repeat_root=base/f'repeat-{repeat}'
            live, scoring = repeat_root/'live', repeat_root/'scoring'
            live_selection=repeat_root/'live-selection.json'
            if live_selection.exists():
                live=(repeat_root/read(live_selection)['selected']).resolve()
                if not live.is_relative_to(repeat_root.resolve()):raise ValueError('Selected live path escapes repetition')
            selection=repeat_root/'judge-selection.json'
            if selection.exists():
                scoring=(repeat_root/read(selection)['selected']).resolve()
                if not scoring.is_relative_to(repeat_root.resolve()):raise ValueError('Selected judge path escapes repetition')
            fairness = read(live/'fairness_audit.json')
            if not fairness['passed']: raise ValueError(f'Fairness audit failed: {name}/{repeat}')
            rows, tokens, protocol, config, source_hashes = audit_batch(live,scoring,repeat)
            if {r['task_id'] for r in rows} != set(task_ids): raise ValueError('Cohort task scope changed')
            for row in rows:
                if row['run_id'] in ids: raise ValueError('Run ID reused')
                ids.add(row['run_id']);row['cohort']=name
                case_path = live/row['strategy']/f"{row['version']}-task-{row['task_id']}"
                event_file = case_path/'result/events.jsonl'
                if event_file.exists():
                    events = [json.loads(line) for line in event_file.read_text(encoding='utf-8').splitlines() if line.strip()]
                    errors = []
                    for event in events:
                        if event['event'] in ('tool_error','model_error'):
                            errors.append({'event':event['event'],'data':event['data']})
                        elif event['event']=='tool_result' and isinstance(event['data'].get('result'),dict) and event['data']['result'].get('isError'):
                            errors.append({'event':'tool_result_isError','data':event['data']})
                    if errors or row['run_status']!='completed' or (row['scores'] and row['scores']['task_fulfillment']<10):
                        log=case_path/'mcp.log'
                        diagnostics=[line for line in log.read_text(encoding='utf-8').splitlines()
                                     if 'Unknown tool:' in line] if log.exists() else []
                        failures.append({'repeat':repeat,'cohort':name,'strategy':row['strategy'],
                            'version':row['version'],'task_id':row['task_id'],'run_status':row['run_status'],
                            'scores':row['scores'],'errors':errors,'routing_diagnostics':diagnostics,
                            'source':case_path.relative_to(ROOT).as_posix()})
            cases.extend(rows);usage.update(tokens);hashes.update(source_hashes)
            protocols.add(protocol['sha256']);configs.add(canonical_hash(config))
            provenance.append({'cohort':name,'repeat':repeat,'task_ids':task_ids,
                'live':live.relative_to(ROOT).as_posix(),'scoring':scoring.relative_to(ROOT).as_posix(),
                'fairness_audit_passed':True})
    if len(protocols)!=1 or len(configs)!=1:raise ValueError('Cannot pool different model/judge protocols')
    superseded_task_usage=Counter();superseded_ids=set()
    for _,base,_,_ in cohorts:
        for file in base.glob('repeat-*/live*/*/*/run_summary.json'):
            summary=read(file);run_id=summary.get('run_id')
            if not run_id or run_id in ids or run_id in superseded_ids:continue
            if summary.get('status')!='model_error' or 'AccountOverdueError' not in summary.get('error',''):
                raise ValueError('Unexpected superseded task attempt')
            superseded_ids.add(run_id)
            events=file.parent/'result/events.jsonl'
            if events.exists():
                for line in events.read_text(encoding='utf-8').splitlines():
                    event=json.loads(line)
                    if event['event']=='model_usage':
                        superseded_task_usage.update({k:v for k,v in event['data'].items()
                            if k in ('prompt_tokens','completion_tokens','total_tokens') and type(v) is int})
    for key,value in superseded_task_usage.items():usage['task_superseded_account_attempts_'+key]=value
    usage['task_all_attempts_total_tokens']=usage.get('task_total_tokens',0)+superseded_task_usage.get('total_tokens',0)
    usage['superseded_account_aborted_task_attempts']=len(superseded_ids)
    all_attempt_usage=Counter()
    for receipt in all_judge_receipts.values():
        all_attempt_usage.update({k:v for k,v in (receipt.get('usage') or {}).items()
                                  if k in ('prompt_tokens','completion_tokens','total_tokens') and type(v) is int})
    usage.update({'judge_all_attempts_'+k:v for k,v in all_attempt_usage.items()})
    usage['judge_recorded_requests_including_technical_failures']=len(all_judge_receipts)
    usage['judge_receipts_without_usage']=sum(not r.get('usage') for r in all_judge_receipts.values())
    probe=ROOT/'member3/evidence/api-connection.json'
    if probe.exists():usage['setup_probe_total_tokens_separate_from_experiment']=(read(probe).get('usage') or {}).get('total_tokens',0)
    result = {'schema_version':1,'label':'six-official-task-three-fresh-repetition-study',
        'created_utc':datetime.now(timezone.utc).isoformat(),'expected_repetitions':3,
        'task_ids':[3,24,28,90,144,156],'cases':cases,'usage':dict(usage),
        'aggregate':aggregate(cases,[3,24,28,90,144,156],3),
        'update_costs':{k:dict(v) for k,v in cost.items()},
        'judge_protocol_sha256':next(iter(protocols)),'run_config_sha256':next(iter(configs)),
        'source_sha256':hashes,'cohorts':provenance,
        'audit':'Each cohort/repetition audited; all raw record, prompt, knowledge and judge receipt hashes verified.',
        'scope_notes':['Tasks 3 and 24 selected before their first model outcomes.',
            'Original, expanded and migration cohorts use separate runner roots/ports.',
            'Expanded runner adds only service manifest entries and per-case filesystem argv.',
            'No historical pilot scores are pooled with these new results.',
            'Task 24 retains its original read_text_file route; the deleted filesystem route is read_file. Earlier reversed metadata is superseded by migration-direction-correction.json.',
            'Task 90 selected before its first outcomes; its deleted get_daily_challenge route and get_problem(daily=true) replacement were confirmed by discovery and public API probes.',
            'Task 24 is a retention control alongside a real route deletion in its service; no claim of no changes anywhere.',
            'Later independent conditions use bounded parallel execution; model/prompt settings unchanged; execution amendments saved per cohort.',
            'After explicit user account replenishment, four AccountOverdue-aborted task attempts were replaced in new directories; unchanged successful runs/scores were reused by exact hashes. Failed attempts and their known usage remain archived.',
            'No method-specific over-update damage is inferred from identical model-visible knowledge.']}
    output.mkdir(parents=True,exist_ok=False)
    save(output/'results.json',result)
    save(output/'case-review.json',{'kind':'real trajectory review candidates','cases':failures,
        'policy':'Review errors in context; service defects and reference-route deletion are not automatically selective-update failures.'})
    report = render_report(result)
    report = report.replace('当前任务集主要包含可选参数与说明变化；新增工具未必是完成任务的必要条件。',
        '正式任务集包含 3、24、28、90、144、156；任务 90 的 Late 版本删除 get_daily_challenge，需迁移到 get_problem(daily=true)。任务 24 保留原有 read_text_file，是保留能力对照。')
    report = report.replace('现有先导实验不构成强制工具迁移验证；不能据此认定选择性修补优于全量重写。',
        '这份表只汇总本次全新运行；不含历史先导分数。全量与选择性知识若等价，不因随机分数差异认定某方法更优。')
    report += '\n## 分组与复现边界\n\n'
    report += '\n'.join('- '+note for note in result['scope_notes'])+'\n'
    (output/'report.md').write_text(report,encoding='utf-8')
    print(json.dumps({'actual_cases':len(cases),'valid_scores':sum(r['scores'] is not None for r in cases),
        'output':str(output),'review_candidates':len(failures)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path)
    main(parser.parse_args().output_dir)
