"""Replace only four AccountOverdue-aborted task attempts in a new live batch."""
import copy
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'member3_migration/workspace'
sys.path[:0]=[str(WORK),str(WORK/'src')]
from member1.run_versions import run_one
from member1.run_comparison import audit_comparison
from member1.scoring_bridge import prepare_evaluation
from member3.analyze import read,save


def main():
    repeat=WORK/'outputs/member3-migration-v1/repeat-3'
    source=repeat/'live';target=repeat/'live-account-recovery'
    original=read(source/'comparison.json')
    if target.exists():
        record=read(target/'comparison.json')
        if record['comparison_id']!=original['comparison_id']+'-account-recovery':raise ValueError('Unexpected recovery output')
    else:
        record=copy.deepcopy(original);record['comparison_id']+='-account-recovery'
        record['runs']=[];record['replaced_account_attempts']=[]
        target.mkdir(parents=True,exist_ok=False)
        shutil.copy2(source/'run_config.json',target/'run_config.json')
        shutil.copytree(source/'knowledge_inputs',target/'knowledge_inputs')
        for strategy in ('no_update','full_rewrite','selective_patch'):(target/strategy).mkdir()
        save(target/'comparison.json',record)
    completed={(r['strategy'],r['version'],r['task_id']) for r in record['runs']}
    for case in original['runs']:
        if (case['strategy'],case['version'],case['task_id']) in completed:continue
        summary=read(source/case['case_path']/'run_summary.json')
        if summary['status']=='model_error' and 'AccountOverdueError' in summary.get('error',''):
            frozen=original['inputs'][f"{case['strategy']}/{case['version']}/{case['task_id']}"]
            result=run_one(case['version'],case['task_id'],target/case['strategy'],False,
                target/frozen['snapshot'],target/'run_config.json',ROOT/'.env')
            record['replaced_account_attempts'].append({'strategy':case['strategy'],'version':case['version'],
                'task_id':case['task_id'],'previous_run_id':summary['run_id'],'new_run_id':result.get('run_id'),
                'reason':'User confirmed account replenished; previous attempt ended on AccountOverdueError'})
            record['runs'].append({**case,'status':result['status']})
            save(target/'comparison.json',record)
            if result['status']=='model_error' and 'AccountOverdueError' in result.get('error',''):
                raise RuntimeError('Account still overdue; remaining task retries not requested')
        else:
            # Session locks/OAuth runtime caches are transient, not experiment evidence.
            shutil.copytree(source/case['case_path'],target/case['case_path'],
                            dirs_exist_ok=True,ignore=shutil.ignore_patterns('runtime'))
            record['runs'].append(case)
            save(target/'comparison.json',record)
    audit=audit_comparison(target);save(target/'fairness_audit.json',audit)
    if not audit['passed']:raise ValueError('Recovered task batch audit failed')
    save(repeat/'live-selection.json',{'selected':target.name,'original':source.name,
        'reason':'Only AccountOverdue-aborted attempts replaced; successful task runs reused unchanged'})
    scoring=repeat/'scoring-account-recovery-live'
    prepare_evaluation(target,scoring,read(WORK/'member3/studies/migration-v1/judge-config.json'))
    new=read(scoring/'evaluation.json');old=read(repeat/'scoring/evaluation.json')
    previous={(c['strategy'],c['version'],c['task_id']):c for c in old['cases']}
    reused=0
    for item in new['cases']:
        before=previous[item['strategy'],item['version'],item['task_id']]
        if item['run_id']==before['run_id'] and before.get('judge_status')=='completed':
            if item['prompts'][0]['sha256']!=before['prompts'][0]['sha256']:
                raise ValueError('Unchanged successful task produced a different judge prompt')
            source_receipt=repeat/'scoring/cases'/before['case_id']/'judge-1.json'
            receipt=read(source_receipt)
            if receipt['protocol_sha256']!=new['protocol_sha256']:raise ValueError('Protocol mismatch')
            shutil.copy2(source_receipt,scoring/'cases'/item['case_id']/'judge-1.json')
            item.update(judge_status='completed',scores=before['scores']);reused+=1
    save(scoring/'evaluation.json',new)
    save(repeat/'judge-selection.json',{'selected':scoring.name,
        'attempt_directories':['scoring',scoring.name],
        'policy':'Account recovery: rejudge only replaced infrastructure-aborted tasks; unchanged successful task scores reused by exact prompt/protocol hash'})
    print(json.dumps({'replaced_tasks':len(record['replaced_account_attempts']),'reused_valid_scores':reused,'new_scores_needed':len(new['cases'])-reused}),flush=True)


if __name__=='__main__':main()
