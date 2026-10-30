"""Freeze and run three externally supplied strategies under one protocol."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from member1.knowledge import STRATEGIES, load_knowledge
from member1.protocol import canonical_hash, validate_config
from member1.run_versions import run_one
from member1.stage2 import manifest


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(plan_path):
    path = Path(plan_path).resolve()
    plan = json.loads(path.read_text(encoding='utf-8-sig'))
    if plan.get('schema_version') != 1 or plan.get('purpose') not in ('interface_smoke', 'strategy_comparison'):
        raise ValueError('schema_version=1 and an explicit purpose are required')
    config = validate_config(plan['run_config'])
    versions, tasks = plan['versions'], plan['task_ids']
    allowed = manifest()
    if not versions or len(versions) != len(set(versions)) or not set(versions) <= set(allowed['versions']):
        raise ValueError('Select unique Early/Middle/Late versions')
    if not tasks or any(type(t) is not int for t in tasks) or len(tasks) != len(set(tasks)) or not set(tasks) <= {t['id'] for t in allowed['tasks']}:
        raise ValueError('Select unique task IDs from the frozen manifest')
    if set(plan['knowledge_dirs']) != set(STRATEGIES):
        raise ValueError('All three strategy inputs are required')
    packets = {}
    for strategy in STRATEGIES:
        mapping = plan['knowledge_dirs'][strategy]
        if set(mapping) != set(versions):
            raise ValueError(f'{strategy} must specify each selected version')
        for version in versions:
            for task in tasks:
                packet = load_knowledge(path.parent / mapping[version] / f'{task}.json', task)
                if packet['packet']['strategy'] != strategy:
                    raise ValueError(f'Knowledge strategy mismatch: {strategy}/{version}/{task}')
                if plan['purpose'] == 'strategy_comparison' and packet['packet'].get('test_fixture'):
                    raise ValueError('Test fixtures cannot be used as formal strategy results')
                packets[strategy, version, task] = packet
    for task in tasks:
        if len({packets['no_update', v, task]['sha256'] for v in versions}) != 1:
            raise ValueError('no_update must reuse identical input bytes across versions')
    return plan, config, packets


def audit_comparison(root):
    root = Path(root).resolve()
    record = json.loads((root / 'comparison.json').read_text(encoding='utf-8'))
    issues, workspaces, signatures, inputs = [], [], {}, {}
    expected = {(s, v, t) for s in STRATEGIES for v in record['versions'] for t in record['task_ids']}
    observed = []
    checks = []
    try:
        config = validate_config(record['run_config'])
        if canonical_hash(config) != record['run_config_sha256']:
            raise ValueError('Comparison configuration fingerprint mismatch')
        if json.loads((root / 'run_config.json').read_text(encoding='utf-8')) != config:
            raise ValueError('Saved comparison configuration differs from manifest')
    except (OSError, ValueError, KeyError) as exc:
        issues.append({'error': str(exc)})
    for run in record['runs']:
        key = (run['strategy'], run['version'], run['task_id'])
        observed.append(key)
        case = root / run['case_path']
        try:
            if not case.resolve().is_relative_to(root):
                raise ValueError('Case path escapes the comparison directory')
            summary = json.loads((case / 'run_summary.json').read_text(encoding='utf-8'))
            result = case / 'result'
            knowledge = load_knowledge(result / 'knowledge.json', key[2])
            frozen = root / record['inputs'][f'{key[0]}/{key[1]}/{key[2]}']['snapshot']
            if not frozen.resolve().is_relative_to(root):
                raise ValueError('Frozen input path escapes the comparison directory')
            if knowledge['raw_bytes'] != frozen.read_bytes():
                raise ValueError('Knowledge differs from frozen input')
            if knowledge['sha256'] != record['inputs'][f'{key[0]}/{key[1]}/{key[2]}']['sha256'] or knowledge['sha256'] != summary.get('knowledge', {}).get('sha256'):
                raise ValueError('Knowledge fingerprint differs from the recorded input')
            if summary.get('strategy') != key[0] or knowledge['packet']['strategy'] != key[0]:
                raise ValueError('Strategy identity does not match input')
            if summary.get('version') != key[1] or summary.get('task_id') != key[2]:
                raise ValueError('Task or environment identity mismatch')
            if summary.get('run_config_sha256') != record['run_config_sha256']:
                raise ValueError('Inference config fingerprint mismatch')
            if any(summary.get(k) != v for k, v in record['run_config'].items()):
                raise ValueError('Effective inference settings differ')
            if json.loads((result / 'run_config.json').read_text(encoding='utf-8')) != record['run_config']:
                raise ValueError('Saved case configuration differs from comparison')
            tools = json.loads((result / 'tools.json').read_text(encoding='utf-8'))
            if tools != knowledge['tools']:
                raise ValueError('Model-visible tools differ from supplied knowledge')
            if record['mode'] == 'live_model':
                events = [json.loads(line) for line in (result / 'events.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
                started = next((e for e in events if e['event'] == 'task_started'), None)
                if started is None:
                    raise ValueError('No model execution start event')
                if knowledge['instructions'] and not started['data']['system_prompt']['content'].endswith(knowledge['instructions']):
                    raise ValueError('Supplied usage instructions did not reach the model')
            context = json.loads((result / 'runtime_context.json').read_text(encoding='utf-8'))
            if context['snapshot'] != manifest()['versions'][key[1]]['snapshot']:
                raise ValueError('Wrong server snapshot')
            required_state = {*manifest()['fixtures'], '.task-sources.json'}
            if set(context.get('workspace_initial_sha256', {})) != required_state:
                raise ValueError('Missing initial workspace fingerprints')
            workspaces.append(context['workspace'])
            from member1.run_task import load_task
            task = json.loads((result / 'task.json').read_text(encoding='utf-8'))
            if task != load_task(key[2]):
                raise ValueError('Task content differs from the fixed benchmark task')
            signature = canonical_hash({
                'services': {k: v['entry_sha256'] for k, v in context['services'].items()},
                'initial_state': context.get('workspace_initial_sha256'),
                'task': task, 'runner': summary.get('runner_sha256'), 'agent': summary.get('agent_sha256'),
                'manifest': summary.get('manifest_sha256'), 'artifact': summary.get('artifact_revision'),
            })
            signatures.setdefault((key[1], key[2]), set()).add(signature)
            inputs.setdefault((key[0], key[2]), set()).add(knowledge['sha256'])
            if summary.get('mode') != record['mode']:
                raise ValueError('Execution mode mismatch')
            if not summary.get('process_stopped'):
                raise ValueError('Owned server process was not stopped')
            checks.append({'strategy': key[0], 'version': key[1], 'task_id': key[2],
                'status': summary['status'], 'knowledge_sha256': knowledge['sha256'], 'passed': True})
        except (OSError, ValueError, KeyError) as exc:
            issues.append({'case': run['case_path'], 'error': str(exc)})
    if set(observed) != expected or len(observed) != len(expected):
        issues.append({'error': 'Missing or duplicate strategy/version/task cases'})
    if len(workspaces) != len(set(workspaces)):
        issues.append({'error': 'A workspace was reused'})
    if any(len(values) != 1 for values in signatures.values()):
        issues.append({'error': 'Task, environment, initial state or runner differs across strategies'})
    if any(len(values) != 1 for (strategy, task), values in inputs.items() if strategy == 'no_update'):
        issues.append({'error': 'no_update knowledge differs between versions'})
    return {'schema_version': 1, 'passed': not issues, 'purpose': record['purpose'],
        'mode': record['mode'], 'expected_cases': len(expected), 'observed_cases': len(observed),
        'checks': checks, 'issues': issues,
        'scope': 'Protocol/input isolation check; not proof of strategy quality or task fulfillment.'}


def run_comparison(plan_path, output=None, env_file=None, check_tools=False):
    plan, config, packets = prepare(plan_path)  # Read ALL inputs before starting any case.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    root = Path(output).resolve() if output else ROOT / 'outputs' / f'stage4-{stamp}-{uuid.uuid4().hex[:8]}'
    root.mkdir(parents=True, exist_ok=False)
    save(root / 'run_config.json', config)
    record = {'schema_version': 1, 'comparison_id': root.name, 'purpose': plan['purpose'],
        'mode': 'tools_only' if check_tools else 'live_model', 'versions': plan['versions'],
        'task_ids': plan['task_ids'], 'run_config': config, 'run_config_sha256': canonical_hash(config),
        'inputs': {}, 'runs': []}
    for (strategy, version, task), packet in packets.items():
        relative = f'knowledge_inputs/{strategy}/{version}/{task}.json'
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(packet['raw_bytes'])
        record['inputs'][f'{strategy}/{version}/{task}'] = {'snapshot': relative,
            'sha256': packet['sha256'], 'test_fixture': bool(packet['packet'].get('test_fixture'))}
    save(root / 'comparison.json', record)
    for strategy in STRATEGIES:
        (root / strategy).mkdir()
    for version in plan['versions']:
        for task in plan['task_ids']:
            for strategy in STRATEGIES:
                input_record = record['inputs'][f'{strategy}/{version}/{task}']
                result = run_one(version, task, root / strategy, check_tools,
                    root / input_record['snapshot'], root / 'run_config.json',
                    Path(env_file).resolve() if env_file else None)
                record['runs'].append({'strategy': strategy, 'version': version, 'task_id': task,
                    'case_path': f'{strategy}/{version}-task-{task}', 'status': result['status']})
                save(root / 'comparison.json', record)
    audit = audit_comparison(root)
    save(root / 'fairness_audit.json', audit)
    print(f'Comparison output: {root}', flush=True)
    return root, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--plan', type=Path)
    choice.add_argument('--audit', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--check-tools', action='store_true')
    args = parser.parse_args()
    if args.audit:
        audit = audit_comparison(args.audit)
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        _, audit = run_comparison(args.plan, args.output_dir, args.env_file, args.check_tools)
    return 0 if audit['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
