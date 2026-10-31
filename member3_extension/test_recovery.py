import json
from member3_extension.repair_judges import recover_scores


def example():
    return {'task_fulfillment':3,'grounding':8,'planning_and_efficiency':2,
        'task_fulfillment_reasoning':'Requirements were missed.',
        'grounding_reasoning':'Most statements were supported.',
        'planning_efficiency_reasoning':'Several calls were redundant.'}


def test_only_missing_final_brace_is_recovered_without_changing_low_scores():
    raw=json.dumps(example())[:-1]
    result=recover_scores('```json\n'+raw+'\n```')
    assert result==example()


def test_truncated_values_and_invalid_scores_are_not_inferred():
    raw=json.dumps(example())[:-12]
    assert recover_scores(raw) is None
    bad=example();bad['task_fulfillment']=100
    assert recover_scores(json.dumps(bad)[:-1]) is None


def test_empty_or_already_valid_responses_are_not_recovered():
    assert recover_scores('') is None
    assert recover_scores(None) is None
    assert recover_scores(json.dumps(example())) is None
