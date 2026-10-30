"""Freeze a repeated experiment, check prerequisites, then run and score it.

The default freeze and preflight commands never call a model. The existing
three-task design is a replication study, not a completed expanded benchmark.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from member1.protocol import canonical_hash
from member3.analyze import read, save, STRATEGIES, VERSIONS


def candidate_tasks():
    tasks = read(ROOT/'src/custom/data/test_cases/test_cases.json')
    chosen = {t['idx'] for t in read(ROOT/'src/custom/data/test_cases/chosen_idx.json')['samples']}
    manifest = read(ROOT/'member1/tasks_manifest.json')
    supported = set(manifest['services'])
    selected = {t['id'] for t in manifest['tasks']}
    candidates = []
    for task in tasks:
        if task['idx'] not in chosen or task['idx'] in selected:
            continue
        missing = sorted(set(task['servers']) - supported)
        candidates.append({'task_id': task['idx'], 'question': task['question'],
            'services': sorted(task['servers']), 'missing_services': missing,
            'required_tool_names': task['servers'], 'status': 'requires_service_and_snapshot_validation',
            'selection_basis': 'official selected task; ranked by missing service count, then task ID; no scores or reference answers used'})
    return sorted(candidates, key=lambda x: (len(x['missing_services']), x['task_id']))


def freeze(output, repetitions):
    if repetitions < 2:
        raise ValueError('A repetition study needs at least two fresh repetitions')
    from member1.run_comparison import prepare
    plan_path = ROOT/'member2/evidence/adaptation/comparison.json'
    plan, config, packets = prepare(plan_path)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    knowledge_dirs = {s: {} for s in STRATEGIES}
    hashes = {}
    for (s, v, t), packet in packets.items():
        relative = f'knowledge/{s}/{v}/{t}.json'
        path = output/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(packet['raw_bytes'])
        hashes[relative] = hashlib.sha256(packet['raw_bytes']).hexdigest()
        knowledge_dirs[s][v] = f'knowledge/{s}/{v}'
    frozen_plan = {**plan, 'knowledge_dirs': knowledge_dirs}
    save(output/'comparison.json', frozen_plan)
    save(output/'judge-config.json', read(ROOT/'member2/evidence/pre_handoff/judge-config-v2.json'))
    schedule = [{'repeat': rep, 'strategy': s, 'version': v, 'task_id': t}
        for rep, v, t, s in itertools.product(range(1, repetitions+1),
            VERSIONS, plan['task_ids'], STRATEGIES)]
    study = {'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'study_kind': 'fresh_repetitions_of_existing_official_subset',
        'scope': 'Replication only; expanded migration and retention coverage remain pending.',
        'task_ids': plan['task_ids'], 'repetitions': repetitions, 'conditions': len(schedule),
        'schedule': schedule, 'run_config': config, 'knowledge_sha256': hashes,
        'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
            for p in ('member1/tasks_manifest.json', 'src/custom/data/test_cases/test_cases.json',
                      'src/custom/data/test_cases/chosen_idx.json',
                      'src/custom/agents/SimpleOpenAIAgent.py', 'src/custom/prompt/eval_error_prompt.py',
                      'member1/snapshots/provenance.json', 'member1/requirements-lock.txt', 'package-lock.json')},
        'code_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('member1', 'member2', 'member3') for p in sorted((ROOT/folder).glob('*.py'))},
        'historical_pilot_included': False, 'judge_repeats_per_trajectory': 1,
        'missing_policy': 'retain null and reason; no zero fill or partial overall mean',
        'ecs_formula': 'per repetition/task mean(TF across versions) - population_sd(TF); equal task/repetition mean',
        'variation': 'sample SD of complete repetition means; no SD with only one repetition',
        'cost_policy': 'unique adaptation.update_id only; inference and judging separately',
        'known_confounders': ['fixed strategy execution order in member1 runner',
            'real-time clocks differ across cases', 'clock service consistency must be checked',
            'same model for task and judge', 'optional changes do not force migration'],
        'paid_requests_executed_at_freeze': 0}
    # Freeze every file consumed later, including the judge and runner plan.
    study['input_sha256'] = {p: hashlib.sha256((output/p).read_bytes()).hexdigest()
                            for p in ('comparison.json', 'judge-config.json')}
    study['sha256'] = canonical_hash(study)
    save(output/'study.json', study)
    save(output/'expansion-candidates.json', {'screened_official_tasks': 201,
        'currently_supported_ids': plan['task_ids'], 'candidates': candidate_tasks(),
        'rule': 'Do not include candidates in scored results until services, official snapshots, fixtures and task-specific knowledge are verified.'})
    return study


def verify_study(directory):
    directory = Path(directory).resolve()
    study = read(directory/'study.json')
    fingerprint = study.pop('sha256')
    if canonical_hash(study) != fingerprint:
        raise ValueError('Study configuration was modified')
    for mapping, base in ((study['input_sha256'], directory),
                          (study['knowledge_sha256'], directory),
                          (study['source_sha256'], ROOT), (study['code_sha256'], ROOT)):
        for relative, digest in mapping.items():
            path = (base/relative).resolve()
            if not path.is_relative_to(base) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError(f'Frozen input/source changed: {relative}; freeze a new study')
    study['sha256'] = fingerprint
    return study


def preflight(directory, env_file):
    study = verify_study(directory)
    from dotenv import dotenv_values
    env = dotenv_values(env_file) if Path(env_file).is_file() else {}
    checks = {'api_key_present': bool(os.environ.get('ARK_API_KEY') or env.get('ARK_API_KEY')),
        'node_available': bool(shutil.which('node')),
        'mcp_python_services': all((Path(sys.executable).parent/(s + ('.exe' if os.name == 'nt' else ''))).exists()
                                  for s in ('mcp-server-time', 'mcp-server-calculator')),
        'python_dependencies': all(importlib.util.find_spec(m) is not None
                                  for m in ('openai', 'mcp', 'jsonschema', 'backoff', 'tqdm'))}
    manifest = read(ROOT/'member1/tasks_manifest.json')
    for service in manifest['services'].values():
        if service['kind'] == 'node':
            checks['node_package:' + service['package']] = (ROOT/'node_modules'/service['package']/'package.json').is_file()
    return {'ready': all(checks.values()), 'checks': checks,
            'planned_fresh_task_runs': study['conditions'],
            'planned_judge_requests': study['conditions'],
            'paid_requests_executed': 0}


def execute(directory, output, env_file):
    directory, output = Path(directory).resolve(), Path(output).resolve()
    check = preflight(directory, env_file)
    if not check['ready']:
        raise ValueError('Preflight incomplete: ' + ', '.join(k for k, v in check['checks'].items() if not v))
    study = verify_study(directory)
    output.mkdir(parents=True, exist_ok=False)
    save(output/'study.json', study)
    def call(*args):
        subprocess.run([sys.executable, '-X', 'utf8', *map(str, args)], cwd=ROOT, check=True)
    live_dirs, score_dirs = [], []
    for repeat in range(1, study['repetitions']+1):
        live, scoring = output/f'repeat-{repeat}'/'live', output/f'repeat-{repeat}'/'scoring'
        call('member1/run_comparison.py', '--plan', directory/'comparison.json',
             '--env-file', Path(env_file).resolve(), '--output-dir', live)
        call('member1/scoring_bridge.py', 'prepare', live, '--output-dir', scoring,
             '--judge-config', directory/'judge-config.json')
        call('member1/scoring_bridge.py', 'judge', scoring, '--env-file', Path(env_file).resolve())
        live_dirs.extend(['--live', str(live)]); score_dirs.extend(['--scoring', str(scoring)])
        if read(scoring/'evaluation.json').get('stopped_reason'):
            save(output/'stopped.json', {'repeat': repeat, 'reason': 'judge stopped; no further batches requested'})
            break
    call('member3/analyze.py', *live_dirs, *score_dirs, '--adaptation', ROOT/'member2/evidence/adaptation',
         '--task-ids', *study['task_ids'], '--expected-repetitions', study['repetitions'],
         '--label', 'fresh-replication-study', '--output-dir', output/'analysis')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    freeze_parser = sub.add_parser('freeze')
    freeze_parser.add_argument('--output-dir', type=Path, required=True)
    freeze_parser.add_argument('--repetitions', type=int, default=3)
    for name in ('preflight', 'run'):
        p = sub.add_parser(name)
        p.add_argument('--study', type=Path, required=True)
        p.add_argument('--env-file', type=Path, default=ROOT/'.env')
        if name == 'run': p.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'freeze':
        result = freeze(args.output_dir, args.repetitions)
        print(json.dumps({'conditions': result['conditions'], 'paid_requests': 0, 'study': str(args.output_dir)}, ensure_ascii=False))
    elif args.command == 'preflight':
        result = preflight(args.study, args.env_file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['ready'] else 2
    else:
        execute(args.study, args.output_dir, args.env_file)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
