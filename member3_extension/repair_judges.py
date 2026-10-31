"""Retry only technical missing scores, preserving all earlier attempts.

Valid scores, including low scores, are never requested again. The model,
prompt, judge protocol and token limit stay identical. At most two extra
requests per missing trajectory; account/auth failures stop the repair.
"""
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from member1.scoring_bridge import run_judge,parse_scores,SCORES
from member3.analyze import read,save


def recover_scores(raw):
    if not isinstance(raw,str):return None
    text=raw.strip()
    if text.startswith('```') and text.endswith('```'):
        text=text.split('\n',1)[1].rsplit('```',1)[0].strip()
    if not text.startswith('{') or text.endswith('}'):return None
    try:return parse_scores(text+'}')
    except (ValueError,TypeError):return None


def offline_recovery(folder,selected,attempts):
    evaluation=read(selected/'evaluation.json')
    if any(c.get('judge_status')=='not_run' for c in evaluation['cases']):
        raise ValueError('Judge batch still in progress; refusing concurrent repair')
    changes=[]
    for case in evaluation['cases']:
        if case.get('judge_status')=='completed':continue
        file=selected/'cases'/case['case_id']/'judge-1.json'
        if file.exists():
            receipt=read(file)
            scores=recover_scores(receipt.get('raw_response'))
            if scores is not None:changes.append((case['case_id'],receipt,scores))
    if not changes:return selected,attempts
    target=folder/f'scoring-offline-recovery-{len(attempts)}'
    shutil.copytree(selected,target,ignore=shutil.ignore_patterns('workers'))
    for case_id,receipt,scores in changes:
        receipt.update(status='completed',scores=scores,
            offline_recovery={'operation':'append exactly one missing final JSON object brace for parsing only',
                              'raw_response_preserved':True,'additional_model_requests':0})
        save(target/'cases'/case_id/'judge-1.json',receipt)
        item=next(c for c in evaluation['cases'] if c['case_id']==case_id)
        item.update(judge_status='completed',scores={k:scores[k] for k in SCORES})
    save(target/'evaluation.json',evaluation)
    print('Offline syntax recovery:',len(changes),'no model requests',flush=True)
    return target,attempts+[target]


def repair(base,repeats=(1,2,3)):
    for repeat in repeats:
        folder=base/f'repeat-{repeat}'
        selection=folder/'judge-selection.json'
        previous=read(selection) if selection.exists() else None
        selected=folder/previous['selected'] if previous else folder/'scoring'
        attempts=[folder/p for p in previous['attempt_directories']] if previous else [selected]
        selected,attempts=offline_recovery(folder,selected,attempts)
        used_rounds=sum('scoring-technical-retry-' in p.name for p in attempts)
        for attempt in range(used_rounds+1,3):
            evaluation=read(selected/'evaluation.json')
            missing=[c for c in evaluation['cases'] if c.get('judge_status')!='completed' and c['status']=='ready']
            if not missing:break
            if evaluation.get('stopped_reason'):raise RuntimeError('Judge stopped for account/infrastructure reason; no automatic paid retry')
            for case in missing:
                for file in (selected/'cases'/case['case_id']).glob('judge-*.json'):
                    receipt=read(file)
                    error=receipt.get('error','').lower()
                    if any(word in error for word in ('accountoverdue','authentication','api key','unauthorized','permissiondenied','insufficient')):
                        raise RuntimeError('Account/authentication error requires external resolution')
            target=folder/f'scoring-technical-retry-{attempt}'
            shutil.copytree(selected,target,ignore=shutil.ignore_patterns('workers'))
            for case in missing:
                for index,prompt in enumerate(case['prompts'],1):
                    file=target/'cases'/case['case_id']/f'judge-{index}.json'
                    if file.exists():
                        receipt=read(file)
                        if receipt.get('status')!='completed':file.unlink()
            print('Technical retry',base.name,repeat,attempt,'missing',len(missing),flush=True)
            result=run_judge(target,ROOT/'.env')
            attempts.append(target);selected=target
            if result.get('stopped_reason'):break
        save(folder/'judge-selection.json',{'selected':selected.relative_to(folder).as_posix(),
            'attempt_directories':[p.relative_to(folder).as_posix() for p in attempts],
            'policy':'At most two extra attempts for missing technical scores; identical prompt/protocol; valid low scores never retried.'})


if __name__=='__main__':
    for folder in (ROOT/'outputs/member3-replication-v2',ROOT/'member3_extension/workspace/outputs/member3-expansion-v1',
                   ROOT/'member3_migration/workspace/outputs/member3-migration-v1'):
        repair(folder)
