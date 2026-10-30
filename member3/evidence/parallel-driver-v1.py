"""Complete remaining frozen conditions with bounded, disjoint-port concurrency.

Existing in-flight children remain owned by their original schedulers. Those
schedulers are suspended before this driver starts, so no conditions are rerun.
Task code, inputs, model settings and judge prompts are unchanged.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from queue import Queue
import shutil
import sys
import threading
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--study',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--first-repeat',choices=['wait-for-existing-judge','judge-existing-live'],required=True)
    args=parser.parse_args()
    root=args.root.resolve();sys.path[:0]=[str(root),str(root/'src')]
    from member1.run_comparison import prepare, audit_comparison
    from member1.run_versions import run_one
    from member1.scoring_bridge import prepare_evaluation, run_judge
    from member1.protocol import canonical_hash
    from member3.experiment import verify_study
    from member3.analyze import read,save
    study_dir=(root/args.study).resolve();output=(root/args.output).resolve()
    verify_study(study_dir)
    plan,config,packets=prepare(study_dir/'comparison.json')
    amendment={'kind':'execution order amendment; no model/protocol/input changes',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'task_workers':3,'judge_workers':4,'task_order_within_version':'task ID list then original strategy order',
        'no_duplicate_policy':'Original schedulers suspended; first-repeat children finish; new live directories must not exist',
        'study_sha256':read(study_dir/'study.json')['sha256']}
    save(output/'execution-amendment.json',amendment)
    def wait_for(path):
        deadline=time.monotonic()+7200
        while not path.exists():
            if time.monotonic()>deadline:raise TimeoutError('Existing child did not finish')
            time.sleep(2)

    def live_repeat(repeat):
        live=output/f'repeat-{repeat}/live'
        live.mkdir(parents=True,exist_ok=False)
        save(live/'run_config.json',config)
        record={'schema_version':1,'comparison_id':f'{output.name}-repeat-{repeat}',
            'purpose':plan['purpose'],'mode':'live_model','versions':plan['versions'],
            'task_ids':plan['task_ids'],'run_config':config,'run_config_sha256':canonical_hash(config),
            'inputs':{},'runs':[],'execution_amendment_sha256':canonical_hash(amendment)}
        for (strategy,version,task),packet in packets.items():
            relative=f'knowledge_inputs/{strategy}/{version}/{task}.json'
            target=live/relative;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(packet['raw_bytes'])
            record['inputs'][f'{strategy}/{version}/{task}']={'snapshot':relative,
                'sha256':packet['sha256'],'test_fixture':bool(packet['packet'].get('test_fixture'))}
        for strategy in plan['knowledge_dirs']:(live/strategy).mkdir()
        save(live/'comparison.json',record)
        queue=Queue()
        def version_worker(version):
            for task in plan['task_ids']:
                for strategy in ('no_update','full_rewrite','selective_patch'):
                    supplied=record['inputs'][f'{strategy}/{version}/{task}']
                    result=run_one(version,task,live/strategy,False,
                        live/supplied['snapshot'],live/'run_config.json',args.env_file.resolve())
                    queue.put({'strategy':strategy,'version':version,'task_id':task,
                        'case_path':f'{strategy}/{version}-task-{task}','status':result['status']})
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures=[executor.submit(version_worker,v) for v in plan['versions']]
            expected=len(packets)
            while len(record['runs'])<expected:
                if all(f.done() for f in futures) and queue.empty():break
                try:item=queue.get(timeout=1)
                except Exception:continue
                record['runs'].append(item);save(live/'comparison.json',record)
            for future in futures:future.result()
        audit=audit_comparison(live);save(live/'fairness_audit.json',audit)
        if not audit['passed']:raise ValueError('Parallel live fairness audit failed')
        print('Live cohort/repeat complete:',root.name,repeat,len(record['runs']),flush=True)
        return live

    def score_repeat(repeat):
        live=output/f'repeat-{repeat}/live';scoring=output/f'repeat-{repeat}/scoring'
        if scoring.exists():raise ValueError('Refusing to collide with an existing judge')
        prepare_evaluation(live,scoring,read(study_dir/'judge-config.json'))
        master=read(scoring/'evaluation.json');stop=threading.Event()
        def worker(index,item):
            if stop.is_set():return index,None,None
            shard=scoring/'workers'/item['case_id'];shard.mkdir(parents=True,exist_ok=False)
            shutil.copy2(scoring/'protocol.json',shard/'protocol.json')
            shutil.copytree(scoring/'cases'/item['case_id'],shard/'cases'/item['case_id'])
            save(shard/'evaluation.json',{**master,'cases':[copy.deepcopy(item)]})
            result=run_judge(shard,args.env_file.resolve())
            if result.get('stopped_reason'):stop.set()
            return index,result,shard
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures=[executor.submit(worker,i,copy.deepcopy(item)) for i,item in enumerate(master['cases'])]
            for future in as_completed(futures):
                index,result,shard=future.result()
                if result is None:continue
                item=result['cases'][0]
                for file in (shard/'cases'/item['case_id']).glob('judge-*.json'):
                    target=scoring/'cases'/item['case_id']/file.name
                    if target.exists():raise ValueError('Duplicate judge receipt')
                    shutil.copy2(file,target)
                master['cases'][index]=item
                if result.get('stopped_reason'):master['stopped_reason']=result['stopped_reason']
                save(scoring/'evaluation.json',master)
        if master.get('stopped_reason'):raise RuntimeError('Judge account/infrastructure stop')
        print('Judge cohort/repeat complete:',root.name,repeat,flush=True)

    if args.first_repeat=='judge-existing-live':
        wait_for(output/'repeat-1/live/fairness_audit.json')
        if not read(output/'repeat-1/live/fairness_audit.json')['passed']:raise ValueError('First live audit failed')
        score_repeat(1)
    # First original-cohort judge runs independently, on unchanged code.
    for repeat in (2,3):
        live_repeat(repeat);score_repeat(repeat)
    first=output/'repeat-1/scoring/evaluation.json'
    wait_for(first)
    while any(c.get('judge_status')=='not_run' for c in read(first)['cases']):
        if read(first).get('stopped_reason'):raise RuntimeError('Existing judge stopped')
        time.sleep(2)
    save(output/'parallel-complete.json',{'status':'completed','fresh_repetitions':3,
        'actual_task_cases':3*len(packets),'execution_amendment':amendment})
    print('All cohort conditions complete:',output,flush=True)


if __name__=='__main__':main()
