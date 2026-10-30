import copy
import hashlib
import json
from pathlib import Path
import pytest
from member2.catalog import diff_catalogs, fingerprint, identity, read_catalog, validate_catalog
from member2.knowledge_base import (CARD, INVENTORY_ID, affected_rules, card_id, instructions,
    seed_knowledge, tool_node, validate_knowledge)
from member2.adapt import ReviewRequired, adapt, packet
from member2.build import build

ROOT = Path(__file__).resolve().parents[2]


def tool(name='lookup', server='@guanxiong/mcp-server-time', alias='clock'):
    return {'name': alias+'__'+name, 'source_server': server, 'source_name': name,
            'description': 'Lookup by city.', 'inputSchema': {'type': 'object',
                'properties': {'city': {'type': 'string'}}, 'required': ['city'], 'additionalProperties': False}}


def pair():
    return [tool(), tool('calculate', 'calculator', 'calculator')]


def blocks(kb): return {b['id']: b for b in kb['blocks']}


def test_no_update_ignores_target_and_preserves_entire_knowledge():
    base = seed_knowledge(pair(), 156)
    result, record = adapt(base, None, 'no_update', 'Late')
    assert result == base and record['update_cost'] == {'tokens': 0, 'seconds': 0.0}
    assert record['target_catalog_sha256'] is None and record['regenerated_blocks'] == []


def test_object_key_order_is_not_a_change():
    old = tool(); reordered = dict(reversed(list(old.items())))
    assert diff_catalogs([old], [reordered])['changed'] == {}


def test_same_tool_name_on_different_servers_has_separate_identity():
    old = [tool('convert_time','time','time_py'), tool('convert_time','time-mcp','time_mcp')]
    target = copy.deepcopy(old); target[0]['description'] = 'Only this server changed.'
    change = diff_catalogs(old, target)
    assert list(change['changed']) == ['time::convert_time']
    assert change['unchanged'] == ['time-mcp::convert_time']


@pytest.mark.parametrize('field,kind', [('description','description'),('inputSchema','parameter'),
    ('outputSchema','output'),('name','routing')])
def test_change_categories_and_field_paths(field, kind):
    old=tool(); new=copy.deepcopy(old)
    replacements={'description':'Updated guidance','inputSchema':{'type':'object'},
        'outputSchema':{'type':'object','properties':{'result':{'type':'number'}}},'name':'clock__replacement'}
    new[field]=replacements[field]
    change=diff_catalogs([old],[new])['changed'][identity(old)]
    assert kind in change['kinds'] and all(p.startswith('/'+field) for p in change['paths'])


def test_parameter_description_propagates_to_usage_card():
    old=pair(); new=copy.deepcopy(old)
    new[0]['inputSchema']['properties']['city']['description']='Use an IANA timezone name.'
    base=seed_knowledge(old,156)
    result,record=adapt(base,new,'selective_patch','Middle')
    assert record['changes']['changed'][identity(old[0])]['kinds']==['description']
    assert 'IANA' in blocks(result)[card_id(identity(old[0]))]['text']
    assert blocks(result)[card_id(identity(old[1]))] == blocks(base)[card_id(identity(old[1]))]


def test_parameter_rename_updates_examples_and_preserves_unrelated_rule_text():
    old=pair(); base=seed_knowledge(old,156)
    unrelated=card_id(identity(old[1])); blocks(base)[unrelated]['text']+='\nPreserved expert note: keep exact expression order.'
    original=fingerprint(base)
    target=copy.deepcopy(old)
    target[0]['inputSchema']={'type':'object','properties':{'location':{'type':'string'},'unit':{'enum':['celsius']}},
        'required':['location','unit'],'additionalProperties':False}
    result,record=adapt(base,target,'selective_patch','Late')
    card=blocks(result)[card_id(identity(old[0]))]
    assert set(card['example']['arguments'])=={'location','unit'}
    assert '"city"' not in card['text']
    assert blocks(result)[unrelated]['text'].encode()==blocks(base)[unrelated]['text'].encode()
    assert unrelated not in record['regenerated_blocks']
    assert INVENTORY_ID in record['affected_blocks']
    assert fingerprint(base)==original
    assert record['update_cost']['seconds']>0 and record['update_cost']['tokens']==0


def test_full_rewrite_regenerates_every_card_and_rule_even_if_tools_are_unchanged():
    base=seed_knowledge(pair(),156)
    blocks(base)[card_id(identity(pair()[1]))]['text']+='\nCustom extra wording.'
    rebuilt,full=adapt(base,pair(),'full_rewrite','Early')
    retained,patch=adapt(base,pair(),'selective_patch','Early')
    assert len(full['regenerated_tools'])==2 and len(full['regenerated_blocks'])==3
    assert patch['regenerated_blocks']==[]
    assert 'Custom extra wording.' in instructions(retained)
    assert 'Custom extra wording.' not in instructions(rebuilt)


def test_add_remove_and_rename_clean_all_generated_route_references():
    old=pair(); target=[copy.deepcopy(old[1]),tool('fetch')]
    base=seed_knowledge(old,156)
    result,record=adapt(base,target,'selective_patch','Late')
    assert record['changes']['removed']==[identity(old[0])]
    assert record['changes']['added']==[identity(target[1])]
    assert 'clock__lookup' not in instructions(result)
    assert 'clock__fetch' in instructions(result)
    assert card_id(identity(old[0])) not in blocks(result)
    validate_knowledge(result)


def test_affected_opaque_rule_requires_review_instead_of_silent_under_update():
    base=seed_knowledge(pair(),156)
    base['blocks'].append({'id':'rule:expert','recipe':None,'depends_on':[card_id(identity(pair()[0]))],
                          'text':'Expert workflow uses the old city argument.'})
    target=pair(); target[0]['description']='Changed meaning'
    with pytest.raises(ReviewRequired) as exc:
        adapt(base,target,'selective_patch','Late')
    assert exc.value.blocks==['rule:expert']


def test_unrelated_opaque_rule_is_preserved_but_full_rewrite_requires_a_recipe():
    base=seed_knowledge(pair(),156)
    opaque={'id':'rule:expert','recipe':None,'depends_on':[tool_node(identity(pair()[1]))],
            'text':'Stable calculator-specific policy.'}
    base['blocks'].append(opaque)
    target=pair(); target[0]['description']='A new clock rule.'
    result,_=adapt(base,target,'selective_patch','Middle')
    assert blocks(result)['rule:expert']==opaque
    with pytest.raises(ReviewRequired): adapt(base,target,'full_rewrite','Middle')


def test_dependency_closure_reaches_rules_through_inventory():
    base=seed_knowledge(pair(),156)
    base['blocks'].extend([
        {'id':'rule:a','recipe':None,'depends_on':[INVENTORY_ID],'text':'A'},
        {'id':'rule:b','recipe':None,'depends_on':['rule:a'],'text':'B'}])
    assert {'rule:a','rule:b'} <= affected_rules(base,{identity(pair()[0])})


@pytest.mark.parametrize('problem',['cycle','dangling','unscoped','unknown_field'])
def test_invalid_or_hidden_knowledge_is_rejected(problem):
    base=seed_knowledge(pair(),156)
    if problem=='cycle':
        base['blocks'].extend([{'id':'rule:a','depends_on':['rule:b'],'text':'A'},
                               {'id':'rule:b','depends_on':['rule:a'],'text':'B'}])
    elif problem=='dangling': base['blocks'][0]['depends_on']=['tool:missing']
    elif problem=='unscoped': base['global_instructions']='Use the old route.'
    else: base['hidden_tool_rules']='Untracked knowledge'
    with pytest.raises(ValueError): validate_knowledge(base)


def test_examples_that_cannot_satisfy_schema_are_explicitly_omitted():
    value=tool(); value['inputSchema']['properties']['city']={'type':'string','pattern':'^[0-9]{3}$'}
    base=seed_knowledge([value],156)
    card=blocks(base)[card_id(identity(value))]
    assert card['example'] is None and card['example_unavailable_reason']
    assert 'No validated shape example' in card['text']


@pytest.mark.parametrize('change',['answer','bad_schema','remote_ref','duplicate'])
def test_catalog_rejects_task_data_invalid_schema_and_external_dependencies(change):
    values=[tool()]
    if change=='answer': values[0]['answer']='Do not ingest'
    elif change=='bad_schema': values[0]['inputSchema']['type']='nonsense'
    elif change=='remote_ref': values[0]['inputSchema']['properties']['city']={'$ref':'https://example.com/schema'}
    else: values.append(copy.deepcopy(values[0]))
    with pytest.raises(ValueError): validate_catalog(values)


def test_build_real_catalogs_exports_27_conditions_and_byte_identical_no_update(tmp_path):
    from member1.run_comparison import prepare
    from member1.knowledge import load_knowledge
    output=tmp_path/'build'
    plan,report=build(ROOT/'member1/evidence/stage2/validation',output)
    _,_,inputs=prepare(plan)
    assert report['status']=='completed' and len(inputs)==27
    assert report['paid_model_requests']==0
    assert len(report['updates'])==27
    for task in (28,144,156):
        baseline=(output/f'initial_packets/{task}.json').read_bytes()
        for version in ('Early','Middle','Late'):
            assert inputs['no_update',version,task]['raw_bytes']==baseline
            for strategy in ('full_rewrite','selective_patch'):
                loaded=load_knowledge(output/f'knowledge/{strategy}/{version}/{task}.json',task)
                assert not loaded['packet'].get('test_fixture')
                assert loaded['packet']['adaptation']['backend']=='deterministic_templates'
                assert loaded['packet']['update_cost']['tokens']==0
    # Unchanged real task provides a retention control; nothing is regenerated.
    unchanged=json.loads((output/'updates/selective_patch/Middle/28.json').read_text())
    assert unchanged['regenerated_blocks']==[] and unchanged['regenerated_tools']==[]
    late=json.loads((output/'updates/selective_patch/Late/156.json').read_text())
    assert any('convert_timezone' in k for k in late['changes']['added'])
    for source in report['sources'].values():
        assert hashlib.sha256((output/source['frozen_path']).read_bytes()).hexdigest()==source['sha256']
    with pytest.raises(FileExistsError): build(ROOT/'member1/evidence/stage2/validation',output)


def test_invalid_observation_preflight_creates_no_partial_output(tmp_path):
    from shutil import copytree
    source=tmp_path/'catalogs'
    for version in ('Early','Middle','Late'):
        dst=source/f'{version}-task-156/result'; dst.mkdir(parents=True)
        original=ROOT/f'member1/evidence/stage2/validation/{version}-task-156/result/tools.json'
        (dst/'tools.json').write_bytes(original.read_bytes())
    (source/'Late-task-156/result/tools.json').write_text('{"answer":"not a catalog"}')
    output=tmp_path/'output'
    with pytest.raises(ValueError): build(source,output,[156])
    assert not output.exists()



def test_portable_tool_integration_is_auditable_but_not_scorable_as_model_results(tmp_path):
    from member1.run_comparison import audit_comparison
    from member1.read_results import read_results
    from member1.scoring_bridge import prepare_evaluation
    source=ROOT/'member2/evidence/tool_integration'
    assert audit_comparison(source)['passed']
    rows=list(read_results(source))
    assert len(rows)==27 and all(r['status']=='knowledge_ready' for r in rows)
    assert all(r['summary']['mode']=='tools_only' for r in rows)
    config=json.loads((ROOT/'member1/judge_config.example.json').read_text())
    evaluation=prepare_evaluation(source,tmp_path/'scoring',config)
    assert len(evaluation['cases'])==27
    assert all(c['status']=='unscorable' for c in evaluation['cases'])
