import copy
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_three_strategy_inputs_are_validated_before_any_execution(tmp_path):
    from member1.build_handoff_demo import build
    from member1.run_comparison import prepare
    plan = build(tmp_path / 'demo')
    _, _, packets = prepare(plan)
    assert len(packets) == 9
    assert len({packets['no_update', v, 156]['sha256'] for v in ('Early', 'Middle', 'Late')}) == 1
    bad = tmp_path / 'demo/full_rewrite/Late/156.json'
    packet = json.loads(bad.read_text(encoding='utf-8'))
    packet['strategy'] = 'selective_patch'
    bad.write_text(json.dumps(packet), encoding='utf-8')
    with pytest.raises(ValueError, match='mismatch'):
        prepare(plan)


def test_demo_cannot_masquerade_as_formal_strategy_comparison(tmp_path):
    from member1.build_handoff_demo import build
    from member1.run_comparison import prepare
    path = build(tmp_path / 'demo')
    plan = json.loads(path.read_text())
    plan['purpose'] = 'strategy_comparison'
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match='fixtures'):
        prepare(path)


@pytest.mark.parametrize('change', [{'api_key': 'not-allowed'}, {'max_round': 0}, {'temperature': float('nan')}])
def test_public_run_config_rejects_credentials_and_invalid_budgets(change):
    from member1.protocol import DEFAULTS, validate_config
    with pytest.raises(ValueError):
        validate_config({**DEFAULTS, **change})


def test_prepare_scoring_is_offline_and_keeps_all_nine_real_cases(tmp_path):
    from member1.scoring_bridge import prepare_evaluation, alignment_report
    config = json.loads((ROOT / 'member1/judge_config.example.json').read_text())
    out = tmp_path / 'eval'
    record = prepare_evaluation(ROOT / 'member1/evidence/stage3/handoff_validation', out, config)
    assert len(record['cases']) == 9
    assert all(c['status'] == 'ready' and c['judge_status'] == 'not_run' for c in record['cases'])
    assert all(c['ecs'] is None for c in alignment_report(record)['tasks'])
    # A later prepare cannot silently overwrite prompts/scores.
    with pytest.raises(FileExistsError):
        prepare_evaluation(ROOT / 'member1/evidence/stage3/handoff_validation', out, config)


def test_full_tool_results_are_joined_by_call_id_and_system_rules_are_excluded():
    from member1.read_results import read_results
    from member1.scoring_bridge import evidence_for_judge
    row = list(read_results(ROOT / 'member1/evidence/stage3/handoff_validation/Early-task-156'))[0]
    event = next(e for e in row['events'] if e['event'] == 'tool_result')
    event['data']['result'] = {'content': [{'type': 'text', 'text': 'FULL-EVIDENCE-' + 'x' * 2000}]}
    row['trajectory_messages'][0]['content'] = 'STRATEGY-SECRET-INSTRUCTION'
    evidence = evidence_for_judge(row)
    assert 'FULL-EVIDENCE-' + 'x' * 2000 in evidence['trajectory']
    assert 'STRATEGY-SECRET-INSTRUCTION' not in evidence['trajectory']


def test_failed_model_run_with_trajectory_remains_scorable(tmp_path):
    from member1.scoring_bridge import prepare_evaluation
    from shutil import copytree
    source = ROOT / 'member1/evidence/stage3/handoff_validation/Early-task-156'
    case = tmp_path / 'case'
    copytree(source, case)
    path = case / 'run_summary.json'
    summary = json.loads(path.read_text(encoding='utf-8'))
    summary['status'] = 'tool_error'
    path.write_text(json.dumps(summary))
    config = json.loads((ROOT / 'member1/judge_config.example.json').read_text())
    record = prepare_evaluation(case, tmp_path / 'evaluation', config)
    assert record['cases'][0]['run_status'] == 'tool_error'
    assert record['cases'][0]['status'] == 'ready'


def test_infrastructure_failure_is_kept_unscored_not_dropped_or_given_zero(tmp_path):
    from member1.scoring_bridge import prepare_evaluation
    case = tmp_path / 'case'
    case.mkdir()
    (case / 'summary.json').write_text(json.dumps({'task_id': 156, 'version': 'Early',
        'strategy': 'no_update', 'status': 'startup_error', 'mode': 'live_model'}))
    config = json.loads((ROOT / 'member1/judge_config.example.json').read_text())
    record = prepare_evaluation(case, tmp_path / 'evaluation', config)
    assert len(record['cases']) == 1
    assert record['cases'][0]['status'] == 'unscorable'
    assert 'scores' not in record['cases'][0]


@pytest.mark.parametrize('bad', [0, 11, True, 8.5, '8'])
def test_judge_scores_must_be_valid_integer_scores(bad):
    from member1.scoring_bridge import parse_scores, SCORES, REASONS
    data = {**{k: 8 for k in SCORES}, **{k: 'reason' for k in REASONS}}
    data['task_fulfillment'] = bad
    with pytest.raises(ValueError):
        parse_scores(json.dumps(data))


def test_ecs_aligns_task_ids_and_refuses_missing_duplicate_or_unscored_versions():
    from member1.scoring_bridge import alignment_report
    cases = [{'task_id': 156, 'strategy': 'no_update', 'version': v, 'status': 'ready',
        'judge_status': 'completed', 'scores': {'task_fulfillment': score}}
        for v, score in zip(('Early', 'Middle', 'Late'), (9, 6, 3))]
    result = alignment_report({'cases': cases})['tasks'][0]
    assert result['ecs'] == pytest.approx(6 - (6 ** .5))
    assert alignment_report({'cases': cases[:2]})['tasks'][0]['ecs'] is None
    assert alignment_report({'cases': cases + [cases[0]]})['tasks'][0]['ecs'] is None
    failed = copy.deepcopy(cases)
    failed[1]['judge_status'] = 'judge_error'
    assert alignment_report({'cases': failed})['tasks'][0]['ecs'] is None


def test_entire_comparison_freezes_inputs_before_first_case(tmp_path, monkeypatch):
    from member1.build_handoff_demo import build
    from member1 import run_comparison as module
    path = build(tmp_path / 'demo')
    _, _, packets = module.prepare(path)
    observed = []
    def fake_run(version, task, suite, check_tools, knowledge_file, config, env_file):
        packet = json.loads(knowledge_file.read_text(encoding='utf-8'))
        strategy = packet['strategy']
        observed.append((strategy, version, knowledge_file.read_bytes()))
        # A member 2 file changed after launch must not change later inputs.
        (tmp_path / 'demo/selective_patch/Late/156.json').write_text('{}')
        return {'status': 'completed'}
    monkeypatch.setattr(module, 'run_one', fake_run)
    monkeypatch.setattr(module, 'audit_comparison', lambda path: {'passed': True})
    root, _ = module.run_comparison(path, tmp_path / 'run')
    assert len(observed) == 9
    for strategy, version, raw in observed:
        assert raw == packets[strategy, version, 156]['raw_bytes']
    assert len(json.loads((root / 'comparison.json').read_text())['runs']) == 9


def test_live_audit_detects_state_reuse_and_config_or_knowledge_tampering(tmp_path):
    from member1.run_comparison import audit_comparison
    from shutil import copytree
    # Portable real integration evidence is supplied with the handoff.
    source = ROOT / 'member1/evidence/stage4/interface_validation'
    if not source.exists():
        pytest.skip('Stage 4 evidence has not been archived yet')
    root = tmp_path / 'archive'
    copytree(source, root)
    assert audit_comparison(root)['passed']
    case = root / 'full_rewrite/Early-task-156'
    path = case / 'run_summary.json'
    summary = json.loads(path.read_text(encoding='utf-8'))
    summary['temperature'] = 1.5
    path.write_text(json.dumps(summary))
    assert not audit_comparison(root)['passed']
    copytree(source, root, dirs_exist_ok=True)
    path = case / 'result/knowledge.json'
    path.write_bytes(path.read_bytes() + b' ')
    assert not audit_comparison(root)['passed']
    copytree(source, root, dirs_exist_ok=True)
    path = case / 'result/runtime_context.json'
    context = json.loads(path.read_text(encoding='utf-8'))
    other = json.loads((root / 'no_update/Early-task-156/result/runtime_context.json').read_text(encoding='utf-8'))
    context['workspace'] = other['workspace']
    path.write_text(json.dumps(context))
    assert not audit_comparison(root)['passed']


def test_source_archive_without_git_metadata_does_not_block_execution(monkeypatch):
    from member1 import run_task
    def missing(*args, **kwargs):
        raise FileNotFoundError('git unavailable in exported source archive')
    monkeypatch.setattr(run_task.subprocess, 'check_output', missing)
    assert run_task.project_commit() is None


def test_judge_preserves_empty_response_and_never_recharges_saved_attempts(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import openai
    from member1.scoring_bridge import prepare_evaluation, run_judge, SCORES, REASONS
    config = json.loads((ROOT / 'member1/judge_config.example.json').read_text())
    directory = tmp_path / 'judge'
    prepare_evaluation(ROOT / 'member1/evidence/stage3/handoff_validation', directory, config)
    requests = []
    value = {**{k: 8 for k in SCORES}, **{k: 'evidence-based reason' for k in REASONS}}
    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs['max_retries'] == 0
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def create(self, **kwargs):
            requests.append(kwargs)
            empty = len(requests) == 2
            return SimpleNamespace(id='fake', model='test', usage=None, choices=[SimpleNamespace(
                message=SimpleNamespace(content='' if empty else json.dumps(value)),
                finish_reason='length' if empty else 'stop')])
        def close(self): pass
    monkeypatch.setenv('JUDGE_API_KEY', 'dummy-test-value')
    monkeypatch.setattr(openai, 'OpenAI', FakeClient)
    first = run_judge(directory)
    assert len(requests) == 9
    assert first['cases'][1]['judge_status'] == 'judge_error'
    assert 'scores' not in first['cases'][1]
    result = directory / 'cases' / first['cases'][1]['case_id'] / 'judge-1.json'
    saved = result.read_bytes()
    assert json.loads(saved)['finish_reason'] == 'length'
    run_judge(directory)
    assert len(requests) == 9 and result.read_bytes() == saved
    prompt = directory / first['cases'][0]['prompts'][0]['path']
    prompt.write_text('tampered')
    with pytest.raises(ValueError, match='modified'):
        run_judge(directory)
    assert len(requests) == 9
