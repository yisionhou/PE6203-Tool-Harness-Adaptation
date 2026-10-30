"""After explicit account replenishment, request only missing judge receipts."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import copy
import hashlib
from datetime import datetime,timezone
from pathlib import Path
import shutil
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from member1.scoring_bridge import run_judge,SCORES
from member3.analyze import read,save
from member3_extension.repair_judges import recover_scores


def main():
    recovery=ROOT/'member3_migration/workspace/outputs/member3-migration-v1/repeat-3/judge-selection.json'
    deadline=time.monotonic()+1800
    while not recovery.exists():
        if time.monotonic()>deadline:raise TimeoutError('Account-aborted task recovery not ready')
        time.sleep(2)
    bases=[ROOT/'outputs/member3-replication-v2',ROOT/'member3_extension/workspace/outputs/member3-expansion-v1',
           ROOT/'member3_migration/workspace/outputs/member3-migration-v1']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    batches=[];jobs=[];offline=0
    for base in bases:
        for repeat in (1,2,3):
            folder=base/f'repeat-{repeat}';selection_file=folder/'judge-selection.json'
            selection=read(selection_file) if selection_file.exists() else {'selected':'scoring','attempt_directories':['scoring']}
            source=folder/selection['selected'];old=read(source/'evaluation.json')
            if all(c.get('judge_status')=='completed' or c['status']!='ready' for c in old['cases']):continue
            target=folder/f'scoring-account-resume-{stamp}'
            shutil.copytree(source,target,ignore=shutil.ignore_patterns('workers'))
            master=read(target/'evaluation.json');master.pop('stopped_reason',None)
            for index,item in enumerate(master['cases']):
                if item.get('judge_status')=='completed' or item['status']!='ready':continue
                receipt_file=target/'cases'/item['case_id']/'judge-1.json'
                if receipt_file.exists():
                    receipt=read(receipt_file);scores=recover_scores(receipt.get('raw_response'))
                    if scores is not None:
                        receipt.update(status='completed',scores=scores,offline_recovery={
                            'operation':'append one missing final JSON object brace for parsing only',
                            'raw_response_preserved':True,'additional_model_requests':0})
                        save(receipt_file,receipt);item.update(judge_status='completed',scores={k:scores[k] for k in SCORES})
                        offline+=1;continue
                    receipt_file.unlink()  # Only the copy; original failed receipt is retained.
                item['judge_status']='not_run';item.pop('scores',None)
                jobs.append((len(batches),index,copy.deepcopy(item)))
            save(target/'evaluation.json',master)
            batches.append({'root':target,'master':master})
            save(selection_file,{'selected':target.name,
                'attempt_directories':selection['attempt_directories']+[target.name],
                'policy':'Explicit user account replenishment; original failures immutable; valid scores never requested again; identical protocol/prompt'})
    print('Missing judge requests after account restoration:',len(jobs),'offline recovered:',offline,flush=True)
    stop=threading.Event();requested=0
    def worker(job):
        batch_index,index,item=job
        if stop.is_set():return job,None,None
        target=batches[batch_index]['root'];master=batches[batch_index]['master']
        short=hashlib.sha256(str(target).encode()).hexdigest()[:10]
        case_hash=hashlib.sha256(item['case_id'].encode()).hexdigest()[:8]
        shard=ROOT/'.tmp/jr'/f'{stamp}-{short}-{case_hash}'
        shard.mkdir(parents=True,exist_ok=False)
        shutil.copyfile(target/'protocol.json',shard/'protocol.json')
        shutil.copytree(target/'cases'/item['case_id'],shard/'cases'/item['case_id'],copy_function=shutil.copyfile)
        save(shard/'evaluation.json',{**master,'cases':[item]})
        result=run_judge(shard,ROOT/'.env')
        if result.get('stopped_reason'):stop.set()
        return job,result,shard
    worker_errors=[]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures=[executor.submit(worker,job) for job in jobs]
        for future in as_completed(futures):
            try:job,result,shard=future.result()
            except Exception as exc:
                worker_errors.append(str(exc));continue
            if result is None:continue
            requested+=1;batch_index,index,_=job
            batch=batches[batch_index];item=result['cases'][0]
            for file in (shard/'cases'/item['case_id']).glob('judge-*.json'):
                dest=batch['root']/'cases'/item['case_id']/file.name
                if dest.exists():raise ValueError('Refusing to overwrite an existing receipt')
                shutil.copyfile(file,dest)
            batch['master']['cases'][index]=item
            if result.get('stopped_reason'):batch['master']['stopped_reason']=result['stopped_reason']
            save(batch['root']/'evaluation.json',batch['master'])
    save(ROOT/'member3/evidence/resume-after-recharge.json',{'user_confirmed_replenishment':True,
        'scheduled_missing_requests':len(jobs),'actual_requests':requested,'offline_recovered':offline,
        'account_stopped_again':stop.is_set(),'max_concurrent_requests':4,'worker_errors':worker_errors})
    if stop.is_set():raise RuntimeError('Account stopped again; pending requests not issued')
    if worker_errors:raise RuntimeError('Worker consolidation error; receipts preserved for offline recovery')
    print('Account restoration scoring pass complete',flush=True)


if __name__=='__main__':main()
