"""Offline regressions for the four reviewed defects; no model calls."""
import copy
import json
from pathlib import Path
import shutil

import pytest

from member3.analyze import audit_batch, read, save, verify_receipt_scores
from member3_extension.merge_results import fresh_fairness_audit
import member3_extension.deliver as deliver

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def saved_task28(tmp_path_factory):
    folder = tmp_path_factory.mktemp('a')
    source = ROOT/'outputs/member3-replication-v2/repeat-1'
    selected = read(source/'judge-selection.json')['selected']
    live, scoring = folder/'live', folder/'scoring'
    live.mkdir();scoring.mkdir()
    comparison = read(source/'live/comparison.json')
    comparison['task_ids'] = [28]
    comparison['runs'] = [r for r in comparison['runs'] if r['task_id'] == 28]
    comparison['inputs'] = {k:v for k,v in comparison['inputs'].items() if k.endswith('/28')}
    save(live/'comparison.json', comparison)
    shutil.copyfile(source/'live/run_config.json', live/'run_config.json')
    for item in comparison['inputs'].values():
        target = live/item['snapshot'];target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/'live'/item['snapshot'], target)
    for item in comparison['runs']:
        shutil.copytree(source/'live'/item['case_path'], live/item['case_path'],
                        ignore=shutil.ignore_patterns('runtime','workspace'))
    shutil.copyfile(source/selected/'protocol.json', scoring/'protocol.json')
    evaluation = read(source/selected/'evaluation.json')
    evaluation['cases'] = [c for c in evaluation['cases'] if c['task_id'] == 28]
    save(scoring/'evaluation.json', evaluation)
    for item in evaluation['cases']:
        shutil.copytree(source/selected/'cases'/item['case_id'], scoring/'cases'/item['case_id'])
    return live, scoring


def test_saved_scores_still_match_original_responses(saved_task28):
    rows, *_ = audit_batch(*saved_task28, repeat=1)
    assert len(rows) == 9
    assert all(r['scores']['task_fulfillment'] == 10 for r in rows)


def test_mutating_both_score_caches_cannot_override_raw_response(saved_task28):
    live, scoring = saved_task28
    evaluation = read(scoring/'evaluation.json');item = evaluation['cases'][0]
    path = scoring/'cases'/item['case_id']/'judge-1.json'
    receipt = read(path)
    assert receipt['scores']['task_fulfillment'] == 10
    original_response = receipt['raw_response']
    receipt['scores']['task_fulfillment'] = 1
    item['scores']['task_fulfillment'] = 1
    save(path, receipt);save(scoring/'evaluation.json', evaluation)
    assert read(path)['raw_response'] == original_response
    with pytest.raises(ValueError, match='original response text'):
        audit_batch(live, scoring, 1)


def sample_receipt():
    scores = {'task_fulfillment': 3, 'grounding': 8, 'planning_and_efficiency': 2,
        'task_fulfillment_reasoning': 'Several requirements were missed.',
        'grounding_reasoning': 'Most statements were supported.',
        'planning_efficiency_reasoning': 'Several calls were redundant.'}
    return {'scores': copy.deepcopy(scores), 'raw_response': json.dumps(scores)}


def test_brace_recovery_requires_explicit_supported_metadata():
    receipt = sample_receipt();receipt['raw_response'] = receipt['raw_response'][:-1]
    with pytest.raises(ValueError, match='without supported offline recovery'):
        verify_receipt_scores(receipt)
    receipt['offline_recovery'] = {'operation': 'invent replacement values',
        'raw_response_preserved': True, 'additional_model_requests': 0}
    with pytest.raises(ValueError, match='without supported offline recovery'):
        verify_receipt_scores(receipt)


def test_recorded_brace_recovery_preserves_raw_text_and_low_scores():
    receipt = sample_receipt();raw = receipt['raw_response'][:-1]
    receipt['raw_response'] = '```json\n'+raw+'\n```'
    before = receipt['raw_response']
    receipt['offline_recovery'] = {
        'operation': 'append exactly one missing final JSON object brace for parsing only',
        'raw_response_preserved': True, 'additional_model_requests': 0}
    assert verify_receipt_scores(receipt) == {
        'task_fulfillment': 3, 'grounding': 8, 'planning_and_efficiency': 2}
    assert receipt['raw_response'] == before


def test_fractional_cached_raw_scores_are_rejected():
    receipt = sample_receipt();receipt['scores']['task_fulfillment'] = 3.0
    with pytest.raises(ValueError, match='original response text'):
        verify_receipt_scores(receipt)


def test_stale_passed_flag_cannot_hide_changed_runtime_context(saved_task28):
    live, _ = saved_task28
    assert fresh_fairness_audit(ROOT, live)['observed_cases'] == 9
    save(live/'fairness_audit.json', {'passed': True})
    item = read(live/'comparison.json')['runs'][0]
    path = live/item['case_path']/'result/runtime_context.json'
    context = read(path);context['snapshot'] = 'wrong-snapshot';save(path, context)
    assert read(live/'fairness_audit.json')['passed'] is True
    with pytest.raises(ValueError, match='Fresh fairness audit failed'):
        fresh_fairness_audit(ROOT, live)


@pytest.fixture
def delivery_tree(tmp_path_factory):
    root = tmp_path_factory.mktemp('d')
    (root/'docs').mkdir()
    final = root/'member3/evidence/formal';final.mkdir(parents=True)
    for name in ('results.json','case-review.json'):
        shutil.copyfile(ROOT/'member3/evidence/formal'/name, final/name)
    cost = final/'cost-comparison';cost.mkdir()
    for name in ('benchmark.json','figure-provenance.json',
                 'update_cost_comparison.png','update_cost_comparison.svg'):
        shutil.copyfile(ROOT/'member3/evidence/formal/cost-comparison'/name, cost/name)
    for relative in ('member2/evidence/adaptation/knowledge',
        'member3_extension/workspace/member2/evidence/adaptation/knowledge',
        'member3_migration/workspace/member2/evidence/adaptation/knowledge'):
        shutil.copytree(ROOT/relative, root/relative)
    return root


def test_report_regeneration_keeps_cost_figure_and_30_repeat_table(delivery_tree, monkeypatch):
    monkeypatch.setattr(deliver, 'ROOT', delivery_tree)
    benchmark = delivery_tree/'member3/evidence/formal/cost-comparison/benchmark.json'
    before = benchmark.read_bytes()
    for _ in range(2):
        deliver.main()
        report = (delivery_tree/'docs/member3-report-section.md').read_text(encoding='utf-8')
        summary = (delivery_tree/'member3/evidence/formal/summary.md').read_text(encoding='utf-8')
        assert report.count('## 更新成本對比圖與重複量測') == 1
        assert '../member3/evidence/formal/cost-comparison/update_cost_comparison.png' in report
        assert '](cost-comparison/update_cost_comparison.png)' in summary
        for text in (report, summary):
            assert '30 次' in text and '0.8849' in text and '0.6130' in text
    assert benchmark.read_bytes() == before


def test_missing_required_cost_figure_fails_before_overwriting(delivery_tree, monkeypatch):
    monkeypatch.setattr(deliver, 'ROOT', delivery_tree)
    report = delivery_tree/'docs/member3-report-section.md'
    report.write_text('Keep the existing report', encoding='utf-8')
    (delivery_tree/'member3/evidence/formal/cost-comparison/update_cost_comparison.png').unlink()
    with pytest.raises(ValueError, match='Required cost evidence is missing'):
        deliver.main()
    assert report.read_text(encoding='utf-8') == 'Keep the existing report'
    assert not (delivery_tree/'member3/evidence/formal/completion.json').exists()


def test_stale_cost_figure_is_not_published_with_new_measurements(delivery_tree, monkeypatch):
    monkeypatch.setattr(deliver, 'ROOT', delivery_tree)
    benchmark = delivery_tree/'member3/evidence/formal/cost-comparison/benchmark.json'
    data = read(benchmark)
    data['summaries']['full_rewrite']['processing_wall_mean_seconds'] += 1
    save(benchmark, data)
    with pytest.raises(ValueError, match='Cost figures are stale'):
        deliver.main()
    assert not (delivery_tree/'docs/member3-report-section.md').exists()
