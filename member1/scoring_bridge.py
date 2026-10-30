"""Offline scoring inputs and an explicit live-judge smoke test for member 3."""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from member1.protocol import canonical_hash
from member1.read_results import read_results
from member1.run_task import load_task
from member1.stage2 import apply_description_layers, manifest
from custom.prompt.eval_error_prompt import build_mcp_bench_judge_prompt

SCORES = ('task_fulfillment', 'grounding', 'planning_and_efficiency')
REASONS = ('task_fulfillment_reasoning', 'grounding_reasoning', 'planning_efficiency_reasoning')
VERSIONS = ('Early', 'Middle', 'Late')


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def evidence_for_judge(row):
    """Restore complete tool results by call ID, without exposing reference answers."""
    messages = copy.deepcopy(row['trajectory_messages'])
    results = {}
    for event in row['events']:
        if event.get('event') == 'tool_result':
            data = event['data']
            call_id = data.get('tool_call_id')
            if call_id:
                results[call_id] = data['result']
    for message in messages:
        if message.get('role') == 'tool' and message.get('tool_call_id') in results:
            message['content'] = json.dumps(results[message['tool_call_id']], ensure_ascii=False)
    # The system prompt contains strategy-specific instructions, not judge evidence.
    messages = [m for m in messages if m.get('role') != 'system']
    catalog = row.get('runtime_tools')
    if not isinstance(catalog, dict) or not isinstance(catalog.get('tools'), list):
        raise ValueError('Saved environment tool catalog is missing')
    services = manifest()['services']
    tools = []
    for raw in catalog['tools']:
        alias, separator, name = raw['name'].partition('_1mcp_')
        server = next((s for s, info in services.items() if info['alias'] == alias), None)
        if not separator or server is None:
            continue
        tool = apply_description_layers({'name': name, 'description': raw.get('description', ''),
            'inputSchema': raw['inputSchema']}, server, row['version'])
        tool['name'] = alias + '__' + name
        tools.append(tool)
    if not tools:
        raise ValueError('Saved environment catalog has no recognized benchmark tools')
    answer = row['answer_record']
    # Original task question is admissible. Its stored answers/tool_calls are not.
    task = load_task(row['task_id'])['question']
    return {'task': task, 'available_tools': json.dumps(tools, ensure_ascii=False, indent=2),
        'trajectory': json.dumps(messages, ensure_ascii=False, indent=2),
        'answer': answer.get('answer', '') if answer else ''}


def prepare_evaluation(source, output, judge_config):
    required = {'model', 'base_url', 'temperature', 'max_completion_tokens', 'num_runs', 'seed'}
    if not isinstance(judge_config, dict) or set(judge_config) != required:
        raise ValueError('Judge config has missing/unknown fields')
    for key in ('model', 'base_url'):
        if not isinstance(judge_config[key], str) or not judge_config[key].strip():
            raise ValueError(f'Judge {key} must be nonempty')
    for key in ('max_completion_tokens', 'num_runs'):
        if type(judge_config[key]) is not int or judge_config[key] < 1:
            raise ValueError(f'Judge {key} must be a positive integer')
    if type(judge_config['seed']) is not int or type(judge_config['temperature']) not in (int, float) or not 0 <= judge_config['temperature'] <= 2:
        raise ValueError('Invalid judge seed or temperature')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    rubric = ROOT / 'src/custom/prompt/eval_error_prompt.py'
    protocol = {'schema_version': 1, 'rubric_sha256': hashlib.sha256(rubric.read_bytes()).hexdigest(),
        'judge_config': judge_config, 'trajectory_policy': 'full_saved_tool_results_v1',
        'catalog_policy': 'saved_actual_environment_with_description_layers_v1'}
    protocol['sha256'] = canonical_hash(protocol)
    write_json(output / 'protocol.json', protocol)
    items = []
    for index, row in enumerate(read_results(source)):
        item = {'case_id': f'{index:04d}-{row["strategy"]}-{row["version"]}-{row["task_id"]}',
            'task_id': row['task_id'], 'version': row['version'], 'strategy': row['strategy'],
            'run_id': row['summary'].get('run_id'), 'purpose': row.get('purpose', 'historical_handoff'),
            'run_status': row['status'], 'source_files': row['source_files'],
            'source_record_sha256': canonical_hash(row), 'status': 'ready', 'judge_status': 'not_run',
            'read_errors': row['read_errors']}
        try:
            if row['summary'].get('mode') != 'live_model':
                raise ValueError('Tool probes are not model task results')
            if row['read_errors']:
                raise ValueError('Corrupt evidence requires review before scoring')
            if not any(m.get('role') == 'assistant' for m in row['trajectory_messages']):
                raise ValueError('No model trajectory; retain as unscored infrastructure failure')
            evidence = evidence_for_judge(row)
            case_dir = output / 'cases' / item['case_id']
            case_dir.mkdir(parents=True)
            write_json(case_dir / 'evidence.json', evidence)
            item['prompts'] = []
            for repeat in range(judge_config['num_runs']):
                order = [0, 1, 2]
                # Same task/repetition uses the same rubric order across strategies/versions.
                random.Random(judge_config['seed'] + row['task_id'] * 1009 + repeat).shuffle(order)
                prompt = build_mcp_bench_judge_prompt(**evidence, dimension_order=tuple(order))
                target = case_dir / f'prompt-{repeat + 1}.txt'
                target.write_text(prompt, encoding='utf-8')
                item['prompts'].append({'path': target.relative_to(output).as_posix(),
                    'sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(), 'dimension_order': order})
        except (KeyError, ValueError) as exc:
            item.update(status='unscorable', reason=str(exc))
        items.append(item)
    record = {'schema_version': 1, 'protocol_sha256': protocol['sha256'], 'cases': items}
    write_json(output / 'evaluation.json', record)
    return record


def parse_scores(raw):
    stripped = raw.strip()
    if stripped.startswith('```') and stripped.endswith('```'):
        stripped = stripped.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError('Judge must return a JSON object')
    for metric in SCORES:
        if type(value.get(metric)) is not int or not 1 <= value[metric] <= 10:
            raise ValueError(f'{metric} must be an integer in [1, 10]')
    if any(not isinstance(value.get(k), str) or not value[k].strip() for k in REASONS):
        raise ValueError('Judge reasoning is required for every score')
    return value


def run_judge(directory, env_file=None):
    from dotenv import load_dotenv
    from openai import OpenAI
    if env_file:
        load_dotenv(env_file, override=False)
    key = os.environ.get('JUDGE_API_KEY') or os.environ.get('ARK_API_KEY')
    if not key:
        raise ValueError('Set JUDGE_API_KEY or ARK_API_KEY locally')
    root = Path(directory).resolve()
    protocol = json.loads((root / 'protocol.json').read_text(encoding='utf-8'))
    fingerprint = protocol.pop('sha256')
    if canonical_hash(protocol) != fingerprint:
        raise ValueError('Judge protocol was modified after preparation')
    config = protocol['judge_config']
    record = json.loads((root / 'evaluation.json').read_text(encoding='utf-8'))
    if record['protocol_sha256'] != fingerprint:
        raise ValueError('Evaluation protocol fingerprint mismatch')
    client = OpenAI(api_key=key, base_url=config['base_url'], timeout=90, max_retries=0)
    for item in record['cases']:
        if item['status'] != 'ready':
            continue
        run_results = []
        for repeat, entry in enumerate(item['prompts'], 1):
            result_path = root / 'cases' / item['case_id'] / f'judge-{repeat}.json'
            prompt = (root / entry['path']).read_text(encoding='utf-8')
            if hashlib.sha256(prompt.encode('utf-8')).hexdigest() != entry['sha256']:
                raise ValueError('Judge prompt was modified after preparation')
            if result_path.exists():
                saved = json.loads(result_path.read_text(encoding='utf-8'))
                if saved['protocol_sha256'] != fingerprint or saved['prompt_sha256'] != entry['sha256']:
                    raise ValueError('Saved judge result does not match this protocol/prompt')
                run_results.append(saved)
                continue
            payload = {'protocol_sha256': fingerprint, 'prompt_sha256': entry['sha256'],
                'started_utc': datetime.now(timezone.utc).isoformat()}
            try:
                response = client.chat.completions.create(model=config['model'], temperature=config['temperature'],
                    max_completion_tokens=config['max_completion_tokens'], messages=[{'role': 'user', 'content': prompt}])
                raw = response.choices[0].message.content or ''
                payload.update(raw_response=raw, response_model=response.model,
                    finish_reason=response.choices[0].finish_reason, response_id=response.id,
                    usage=response.usage.model_dump() if response.usage else None)
                if not raw.strip():
                    raise ValueError('Judge returned no score text; inspect usage and finish_reason')
                payload['scores'] = parse_scores(raw)
                payload['status'] = 'completed'
            except Exception as exc:
                payload.update(status='judge_error', error=str(exc))
            # Never overwrite previous judge attempts; failed attempts remain evidence.
            text = json.dumps(payload, ensure_ascii=False, indent=2).replace(key, '[REDACTED]')
            with result_path.open('x', encoding='utf-8') as stream:
                stream.write(text + '\n')
            run_results.append(payload)
        valid = [r['scores'] for r in run_results if r['status'] == 'completed']
        item['judge_status'] = 'completed' if len(valid) == config['num_runs'] else 'judge_error'
        if item['judge_status'] == 'completed':
            item['scores'] = {k: statistics.mean(r[k] for r in valid) for k in SCORES}
        write_json(root / 'evaluation.json', record)
        print(item['case_id'], item['judge_status'], flush=True)
    client.close()
    return record


def alignment_report(record):
    """Strict three-version joins. Failed/missing scores remain explicit, never zero."""
    groups = {}
    for item in record['cases']:
        groups.setdefault((item['strategy'], item['task_id']), {}).setdefault(item['version'], []).append(item)
    rows = []
    for (strategy, task), versions in sorted(groups.items()):
        issues = []
        for version in VERSIONS:
            entries = versions.get(version, [])
            if len(entries) != 1:
                issues.append(f'{version}: expected one case, found {len(entries)}')
            elif entries[0].get('judge_status') != 'completed':
                issues.append(f'{version}: no complete judge score ({entries[0].get("judge_status", entries[0]["status"])})')
        row = {'strategy': strategy, 'task_id': task, 'issues': issues, 'ecs': None}
        if not issues:
            tf = [versions[v][0]['scores']['task_fulfillment'] for v in VERSIONS]
            row.update(tf_by_version=dict(zip(VERSIONS, tf)), ecs=statistics.mean(tf) - statistics.pstdev(tf))
        rows.append(row)
    return {'schema_version': 1, 'ecs_definition': 'per task: mean(TF_Early,TF_Middle,TF_Late) - population_stddev',
        'tasks': rows, 'unscored_cases': sum(c.get('judge_status') != 'completed' for c in record['cases']),
        'note': 'Interface-smoke scores are integration evidence, not formal strategy-performance conclusions.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('source', type=Path)
    prep.add_argument('--output-dir', type=Path, required=True)
    prep.add_argument('--judge-config', type=Path, required=True)
    judge = sub.add_parser('judge')
    judge.add_argument('directory', type=Path)
    judge.add_argument('--env-file', type=Path)
    align = sub.add_parser('align')
    align.add_argument('directory', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        record = prepare_evaluation(args.source, args.output_dir,
            json.loads(args.judge_config.read_text(encoding='utf-8-sig')))
        print(f'Prepared {len(record["cases"])} cases; {sum(c["status"] == "ready" for c in record["cases"])} ready')
        return 0
    if args.command == 'judge':
        record = run_judge(args.directory, args.env_file)
    else:
        record = json.loads((args.directory / 'evaluation.json').read_text(encoding='utf-8'))
    report = alignment_report(record)
    write_json(args.directory / 'alignment.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if args.command == 'align' or all(c.get('judge_status') == 'completed' for c in record['cases']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
