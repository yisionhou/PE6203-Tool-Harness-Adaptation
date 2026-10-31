"""Freeze observed catalogs, generate actual strategy packages, and hand off a plan."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from member1.knowledge import load_knowledge
from member1.protocol import DEFAULTS
from member1.run_comparison import prepare
from member1.stage2 import manifest
from member2.adapt import METHOD_VERSION, STRATEGIES, adapt, packet
from member2.catalog import fingerprint, identity, read_catalog
from member2.knowledge_base import seed_knowledge

VERSIONS = ('Early', 'Middle', 'Late')


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(json_bytes(value))


def build(catalog_root, output, task_ids=(28, 144, 156)):
    catalog_root, output = Path(catalog_root).resolve(), Path(output).resolve()
    allowed = {t['id']: t for t in manifest()['tasks']}
    tasks = list(task_ids)
    if not tasks or any(type(t) is not int or t not in allowed for t in tasks) or len(tasks) != len(set(tasks)):
        raise ValueError('Use unique tasks from the frozen member 1 manifest')
    # Validate/freeze every observation in memory before creating any output.
    catalogs, sources, raw_sources = {}, {}, {}
    for version in VERSIONS:
        for task in tasks:
            path = catalog_root / f'{version}-task-{task}/result/tools.json'
            tools, sha, raw = read_catalog(path)
            if not {t['source_server'] for t in tools} <= set(allowed[task]['services']):
                raise ValueError('Catalog contains a server outside the fixed task scope')
            catalogs[version, task] = tools
            key = f'{version}/{task}'
            raw_sources[key] = raw
            sources[key] = {'source_file': str(path), 'sha256': sha,
                'frozen_path': f'observations/{version}/{task}.json',
                'policy': 'saved member1 model-visible catalog with official description layers; no answer or trajectory input'}
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'status': 'building', 'method_version': METHOD_VERSION,
        'backend': 'deterministic_templates', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(), 'task_ids': tasks, 'versions': list(VERSIONS),
        'transition_policy': 'independent Early -> target', 'sources': sources,
        'code_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))},
        'initialization': [], 'updates': [], 'paid_model_requests': 0,
        'scope': 'Actual deterministic adaptation artifacts and interface validation; no TF/PE/ECS claims.'}
    try:
        for key, info in sources.items():
            path = output / info['frozen_path']; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw_sources[key])
        bases, frozen_no_update = {}, {}
        for task in tasks:
            started = time.perf_counter()
            bases[task] = seed_knowledge(catalogs['Early', task], task)
            report['initialization'].append({'task_id': task, 'seconds': time.perf_counter()-started,
                'tokens': 0, 'shared_across_strategies': True})
            save(output / f'initial/{task}.json', bases[task])
            initial, record = adapt(bases[task], None, 'no_update', 'Early')
            raw = json_bytes(packet(initial, 'no_update', record))
            frozen_no_update[task] = raw
            for rel in (f'initial_packets/{task}.json', f'knowledge/no_update/{task}.json'):
                path = output / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        directories = {strategy: {} for strategy in STRATEGIES}
        for version in VERSIONS:
            for strategy in STRATEGIES:
                directory = 'knowledge/no_update' if strategy == 'no_update' else f'knowledge/{strategy}/{version}'
                directories[strategy][version] = directory
                for task in tasks:
                    kb, record = adapt(bases[task], catalogs[version, task], strategy, version)
                    target = output / directory / f'{task}.json'
                    if strategy == 'no_update':
                        if target.read_bytes() != frozen_no_update[task]:
                            raise ValueError('No-update baseline bytes changed')
                    else:
                        save(target, packet(kb, strategy, record))
                    loaded = load_knowledge(target, task)
                    record.update(knowledge_path=target.relative_to(output).as_posix(),
                        knowledge_sha256=loaded['sha256'], observation_ref=f'{version}/{task}',
                        record_path=f'updates/{strategy}/{version}/{task}.json')
                    save(output / record['record_path'], record)
                    report['updates'].append({k: record[k] for k in ('update_id', 'task_id', 'strategy',
                        'target_version', 'knowledge_path', 'knowledge_sha256', 'record_path', 'update_cost')})
        plan = {'schema_version': 1, 'purpose': 'strategy_comparison', 'task_ids': tasks,
            'versions': list(VERSIONS), 'run_config': dict(DEFAULTS), 'knowledge_dirs': directories}
        save(output / 'comparison.json', plan)
        _, _, inputs = prepare(output / 'comparison.json')
        report.update(status='completed', validated_conditions=len(inputs),
            totals_by_strategy={s: {'tokens': sum(r['update_cost']['tokens'] for r in report['updates'] if r['strategy']==s),
                'seconds': sum(r['update_cost']['seconds'] for r in report['updates'] if r['strategy']==s)} for s in STRATEGIES},
            cost_aggregation='Each nonzero adaptation update_id is counted once; reusing a package for repeated task runs does not repeat its update cost. No-update records share zero-cost baseline IDs.')
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        save(output / 'build_report.json', report)
        raise
    save(output / 'build_report.json', report)
    return output / 'comparison.json', report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog-root', type=Path, default=ROOT/'member1/evidence/stage2/validation')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--task-ids', type=int, nargs='+', default=[28,144,156])
    args = parser.parse_args()
    path, report = build(args.catalog_root, args.output_dir, args.task_ids)
    print(json.dumps({'plan': str(path), 'status': report['status'],
        'validated_conditions': report['validated_conditions'], 'paid_model_requests': 0,
        'update_cost': report['totals_by_strategy']}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
