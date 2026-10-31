"""Offline paired cost benchmark over the frozen six-task knowledge corpus."""
from datetime import datetime,timezone
import hashlib
from pathlib import Path
import platform
import random
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from member2.adapt import adapt,STRATEGIES
from member3.analyze import read,save


def main():
    output=ROOT/'member3/evidence/formal/cost-comparison'
    output.mkdir(parents=True,exist_ok=False)
    cohorts=[(ROOT/'member2/evidence/adaptation',[28,144,156]),
        (ROOT/'member3_extension/workspace/member2/evidence/adaptation',[3,24]),
        (ROOT/'member3_migration/workspace/member2/evidence/adaptation',[90])]
    cases=[];sources={}
    for folder,tasks in cohorts:
        for task in tasks:
            initial=folder/f'initial/{task}.json';base=read(initial)
            sources[initial.relative_to(ROOT).as_posix()]=hashlib.sha256(initial.read_bytes()).hexdigest()
            for version in ('Early','Middle','Late'):
                catalog=folder/f'observations/{version}/{task}.json'
                sources[catalog.relative_to(ROOT).as_posix()]=hashlib.sha256(catalog.read_bytes()).hexdigest()
                expected={}
                for strategy in STRATEGIES:
                    path=folder/'knowledge'/strategy/f'{task}.json' if strategy=='no_update' else folder/'knowledge'/strategy/version/f'{task}.json'
                    expected[strategy]=read(path)['adaptation']['knowledge_sha256']
                cases.append((task,version,base,read(catalog),expected))
    # One unreported warm-up block. No network/model calls exist in this path.
    for _,version,base,catalog,_ in cases:
        for strategy in STRATEGIES:adapt(base,catalog,strategy,version)
    rng=random.Random(6203);samples=[]
    for repeat in range(1,31):
        strategies=list(STRATEGIES);rng.shuffle(strategies)
        order=list(cases);rng.shuffle(order)
        for strategy in strategies:
            wall=update=overhead=0.0;tools=blocks=0
            for task,version,base,catalog,expected in order:
                start=time.perf_counter()
                _,record=adapt(base,catalog,strategy,version)
                wall+=time.perf_counter()-start
                if record['output_sha256']!=expected[strategy]:raise ValueError('Benchmark output differs from frozen method')
                update+=record['update_cost']['seconds']
                overhead+=record.get('harness_overhead_seconds',0)
                tools+=len(record['regenerated_tools']);blocks+=len(record['regenerated_blocks'])
            samples.append({'repeat':repeat,'strategy':strategy,'case_count':len(cases),
                'processing_wall_seconds':wall,'update_seconds':update,
                'reported_no_update_harness_seconds':overhead,
                'regenerated_tools':tools,'regenerated_blocks':blocks,'update_tokens':0})
        if repeat%5==0:print('Offline cost repetitions:',repeat,'/30',flush=True)
    summaries={}
    for strategy in STRATEGIES:
        group=[r for r in samples if r['strategy']==strategy]
        summaries[strategy]={'repetitions':30,'conditions_per_repetition':18,
            'processing_wall_mean_seconds':statistics.mean(r['processing_wall_seconds'] for r in group),
            'processing_wall_sample_sd_seconds':statistics.stdev(r['processing_wall_seconds'] for r in group),
            'update_mean_seconds':statistics.mean(r['update_seconds'] for r in group),
            'update_sample_sd_seconds':statistics.stdev(r['update_seconds'] for r in group),
            'regenerated_tools':group[0]['regenerated_tools'],'regenerated_blocks':group[0]['regenerated_blocks'],
            'update_tokens':0,'update_model_requests':0,'update_api_fee':0}
        if len({(r['regenerated_tools'],r['regenerated_blocks']) for r in group})!=1:
            raise ValueError('Nondeterministic regeneration counts')
    full=summaries['full_rewrite'];patch=summaries['selective_patch']
    result={'kind':'offline paired update-cost microbenchmark, distinct from 162 model-task evaluations',
        'created_utc':datetime.now(timezone.utc).isoformat(),'task_ids':[3,24,28,90,144,156],
        'versions':['Early','Middle','Late'],'seed':6203,'repetitions':30,'warmup_blocks':1,
        'processing_scope':'wall time inside adapt() including input validation, detection/copy, generation, retention checks and final input-integrity check; excludes loading, shared seeding, disk/export, task inference and judging',
        'update_scope':'adapter-reported update algorithm time; no_update is policy-zero and its validation/copy overhead is separate',
        'order_policy':'shuffle strategy block order and case order per repetition; all strategies share each repetition case order',
        'machine':{'python':platform.python_version(),'platform':platform.platform()},
        'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'member2').glob('*.py')},
        'source_sha256':sources,'summaries':summaries,'samples':samples,
        'processing_time_reduction_percent':100*(1-patch['processing_wall_mean_seconds']/full['processing_wall_mean_seconds']),
        'tool_record_reduction_percent':100*(1-patch['regenerated_tools']/full['regenerated_tools']),
        'rule_block_reduction_percent':100*(1-patch['regenerated_blocks']/full['regenerated_blocks']),
        'paid_model_requests':0,'human_labor_or_salary_measured':False}
    save(output/'benchmark.json',result)
    print({s:{k:round(v,6) if isinstance(v,float) else v for k,v in a.items()} for s,a in summaries.items()},flush=True)


if __name__=='__main__':main()
