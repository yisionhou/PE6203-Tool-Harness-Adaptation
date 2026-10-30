"""Three actual adaptation policies over one explicit knowledge representation."""
from __future__ import annotations
import copy
import time
import uuid
from member2.catalog import diff_catalogs, fingerprint, identity, validate_catalog
from member2.knowledge_base import (CARD, INVENTORY, INVENTORY_ID, affected_rules, card_id,
    instructions, render_card, render_inventory, seed_knowledge, validate_knowledge)

METHOD_VERSION = 'dependency-aware-v1'
STRATEGIES = ('no_update', 'full_rewrite', 'selective_patch')


class ReviewRequired(ValueError):
    """There is affected knowledge for which no valid rewrite recipe is available."""
    def __init__(self, blocks):
        self.blocks = sorted(blocks)
        super().__init__('Manual review required for rules without a supported recipe: ' + ', '.join(self.blocks))


def adapt(base, target_tools, strategy, target_version):
    if strategy not in STRATEGIES or target_version not in ('Early', 'Middle', 'Late'):
        raise ValueError('Unknown strategy or target version')
    started = time.perf_counter()
    validate_knowledge(base)
    before_hash = fingerprint(base)
    old_tools = {identity(t): t for t in base['tools']}
    old_blocks = {b['id']: b for b in base['blocks']}
    if strategy == 'no_update':
        # The no-update policy does not inspect the target catalog.
        result = copy.deepcopy(base)
        record = {'update_id': 'no-update-' + before_hash, 'strategy': strategy,
            'base_version': base['version'], 'target_version': target_version,
            'base_sha256': before_hash, 'target_catalog_sha256': None, 'changes': None,
            'affected_blocks': [], 'regenerated_tools': [], 'regenerated_blocks': [],
            'removed_blocks': [], 'changed_blocks': [], 'changed_tool_records': [],
            'preserved_tool_sha256': {k: fingerprint(v) for k, v in old_tools.items()},
            'preserved_block_sha256': {k: fingerprint(v) for k, v in old_blocks.items()},
            'output_sha256': before_hash, 'update_cost': {'tokens': 0, 'seconds': 0.0},
            'harness_overhead_seconds': time.perf_counter() - started}
    else:
        target = validate_catalog(target_tools)
        new_tools = {identity(t): t for t in target}
        changes = diff_catalogs(base['tools'], target)
        changed_ids = set(changes['changed']) | set(changes['removed'])
        affected = affected_rules(base, changed_ids, bool(changes['added'] or changes['removed']))
        if strategy == 'full_rewrite':
            unsupported = {k for k, b in old_blocks.items() if b.get('recipe') not in (CARD, INVENTORY)}
            if unsupported: raise ReviewRequired(unsupported)
            result = seed_knowledge(target, base['task_id'], target_version, base['global_instructions'])
            regenerated_tools = set(new_tools)
            regenerated = {b['id'] for b in result['blocks']}
            preserved_tools, preserved_blocks = {}, {}
        else:
            unsupported = {k for k in affected if old_blocks[k].get('recipe') not in (CARD, INVENTORY)}
            if unsupported: raise ReviewRequired(unsupported)
            merged_tools = {k: copy.deepcopy(old_tools[k] if k in changes['unchanged'] else new_tools[k])
                            for k in sorted(new_tools)}
            blocks = copy.deepcopy(old_blocks)
            for key in changes['removed']:
                blocks.pop(card_id(key))
            regenerated_tools = set(changes['added']) | set(changes['changed'])
            regenerated = set()
            for key in sorted(regenerated_tools):
                block = render_card(merged_tools[key])
                blocks[block['id']] = block; regenerated.add(block['id'])
            if INVENTORY_ID in affected or changes['added'] or changes['removed']:
                blocks[INVENTORY_ID] = render_inventory(list(merged_tools.values()))
                regenerated.add(INVENTORY_ID)
            result = {'schema_version': 1, 'task_id': base['task_id'], 'version': target_version,
                'tools': list(merged_tools.values()), 'global_instructions': base['global_instructions'],
                'blocks': [blocks[k] for k in sorted(blocks)]}
            preserved_tools = {k: fingerprint(old_tools[k]) for k in changes['unchanged']}
            preserved_blocks = {k: fingerprint(b) for k, b in old_blocks.items()
                                if k not in affected and k in blocks}
            for key, digest in preserved_tools.items():
                if fingerprint(merged_tools[key]) != digest: raise ValueError('Unrelated tool knowledge was changed')
            for key, digest in preserved_blocks.items():
                if fingerprint(blocks[key]) != digest: raise ValueError('Unrelated rule was changed')
        validate_knowledge(result)
        output_blocks = {b['id']: b for b in result['blocks']}
        changed_blocks = {k for k in old_blocks.keys() | output_blocks.keys()
                          if old_blocks.get(k) != output_blocks.get(k)}
        allowed = affected | {card_id(k) for k in changes['added']}
        if strategy == 'selective_patch' and not changed_blocks <= allowed:
            raise ValueError('A selective patch changed a block outside its dependency closure')
        record = {'update_id': str(uuid.uuid4()), 'strategy': strategy,
            'base_version': base['version'], 'target_version': target_version, 'base_sha256': before_hash,
            'target_catalog_sha256': fingerprint(target), 'changes': changes,
            'affected_blocks': sorted(affected), 'regenerated_tools': sorted(regenerated_tools),
            'regenerated_blocks': sorted(regenerated), 'removed_blocks': sorted(old_blocks.keys() - output_blocks.keys()),
            'changed_blocks': sorted(changed_blocks),
            'changed_tool_records': sorted(set(changes['added']) | set(changes['removed']) | set(changes['changed'])),
            'preserved_tool_sha256': preserved_tools, 'preserved_block_sha256': preserved_blocks,
            'output_sha256': fingerprint(result),
            'update_cost': {'tokens': 0, 'seconds': time.perf_counter() - started}}
    record.update(schema_version=1, task_id=base['task_id'], method_version=METHOD_VERSION,
        backend='deterministic_templates', measurement_scope='update algorithm including detection, rendering and validation; excludes disk IO, compatibility export/serialization, initial shared seeding, task inference and scoring',
        no_update_cost_policy='No knowledge update; zero update cost, orchestration validation/copy time recorded separately')
    if fingerprint(base) != before_hash:
        raise ValueError('Adapter mutated its source knowledge')
    return result, record


def packet(kb, strategy, record):
    validate_knowledge(kb)
    if record['strategy'] != strategy or record['task_id'] != kb['task_id']:
        raise ValueError('Update record does not match knowledge')
    return {'schema_version': 1, 'task_id': kb['task_id'], 'strategy': strategy,
        'source_version': kb['version'], 'tools': copy.deepcopy(kb['tools']),
        'instructions': instructions(kb), 'update_cost': copy.deepcopy(record['update_cost']),
        'knowledge_blocks': copy.deepcopy(kb['blocks']), 'knowledge_global_instructions': kb['global_instructions'],
        'adaptation': {'method_version': METHOD_VERSION, 'backend': 'deterministic_templates',
            'update_id': record['update_id'], 'base_version': record['base_version'],
            'base_sha256': record['base_sha256'], 'knowledge_sha256': fingerprint(kb),
            'target_catalog_sha256': record['target_catalog_sha256']}}
