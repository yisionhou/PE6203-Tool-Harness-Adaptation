import itertools
import math
import pytest
from member3.analyze import aggregate, valid_scores, bounded, update_costs, save


def complete_rows(repetitions=1):
    return [{'repeat': r, 'strategy': s, 'version': v, 'task_id': 28,
             'scores': {'task_fulfillment': 10, 'planning_and_efficiency': 8, 'grounding': 10}}
            for r, s, v in itertools.product(range(1, repetitions+1),
                ('no_update', 'full_rewrite', 'selective_patch'), ('Early', 'Middle', 'Late'))]


def test_missing_score_is_retained_and_blocks_overall_metrics():
    rows = complete_rows()
    rows[0]['scores'] = None
    report = aggregate(rows, [28], 1)
    summary = report['strategies']['no_update']
    assert summary['metrics']['task_fulfillment']['mean'] is None
    assert summary['metrics']['task_fulfillment']['observed_mean'] == 10
    assert summary['scored_cases'] == 2 and summary['ecs_mean'] is None
    assert report['strategies']['full_rewrite']['ecs_mean'] == 10


def test_absent_repeat_does_not_become_a_zero_or_complete_study():
    report = aggregate(complete_rows(), [28], 3)
    assert len(report['absent_cases']) == 18
    assert report['strategies']['full_rewrite']['metrics']['task_fulfillment']['mean'] is None


def test_ecs_uses_population_sd_across_versions():
    rows = complete_rows()
    for row, score in zip(rows[:3], (10, 7, 4)):
        row['scores']['task_fulfillment'] = score
    result = aggregate(rows, [28], 1)
    assert result['strategies']['no_update']['ecs_mean'] == pytest.approx(7-math.sqrt(6))
    assert result['strategies']['no_update']['metrics']['task_fulfillment']['repeat_sample_sd'] is None


def test_repeat_variation_is_not_task_heterogeneity():
    rows = complete_rows(3)
    for row in rows:
        row['scores']['task_fulfillment'] = {1: 10, 2: 8, 3: 6}[row['repeat']]
    strategy = aggregate(rows, [28], 3)['strategies']['full_rewrite']
    metrics = strategy['metrics']['task_fulfillment']
    assert metrics['repeat_means'] == [10, 8, 6]
    assert metrics['mean'] == 8 and metrics['repeat_sample_sd'] == 2
    assert strategy['ecs_mean'] == 8 and strategy['ecs_repeat_sample_sd'] == 2


def test_duplicate_and_unexpected_conditions_are_rejected():
    rows = complete_rows()
    with pytest.raises(ValueError, match='Duplicate'):
        aggregate(rows + [rows[0]], [28], 1)
    with pytest.raises(ValueError, match='Unexpected'):
        aggregate(rows, [144], 1)


@pytest.mark.parametrize('score', [True, -1, 0, 0.9, 11, float('nan'), float('inf'), '10'])
def test_invalid_scores_cannot_enter_statistics(score):
    assert not valid_scores({'task_fulfillment': score, 'planning_and_efficiency': 10, 'grounding': 10})


def test_update_cost_is_charged_once_per_update_id(tmp_path):
    root = tmp_path/'updates'
    root.mkdir()
    record = {'update_id': 'shared', 'strategy': 'full_rewrite', 'task_id': 28,
              'update_cost': {'tokens': 0, 'seconds': 0.2}, 'regenerated_tools': ['x']}
    save(root/'a.json', record); save(root/'b.json', record)
    costs = update_costs(tmp_path)
    assert costs['full_rewrite']['seconds'] == 0.2
    assert costs['full_rewrite']['regenerated_tools'] == 1
    record['update_cost']['seconds'] = 0.3
    save(root/'b.json', record)
    with pytest.raises(ValueError, match='Inconsistent'):
        update_costs(tmp_path)


def test_evidence_paths_cannot_escape_batch(tmp_path):
    with pytest.raises(ValueError, match='escapes'):
        bounded(tmp_path, '../foreign.json')
