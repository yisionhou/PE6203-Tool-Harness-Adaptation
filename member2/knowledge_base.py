"""Tool cards, explicit dependencies, schema-shaped examples and validation."""
from __future__ import annotations
import copy
import json
from jsonschema import Draft202012Validator
from member2.catalog import identity, validate_catalog

CARD = 'tool_card_v1'
INVENTORY = 'tool_inventory_v1'
INVENTORY_ID = 'rule:inventory'
GLOBAL_RULES = ('Use the supplied tool knowledge. Example arguments illustrate JSON shape only; '
                'replace placeholders with values from the user task before execution. '
                'Do not treat examples as task answers. Inspect tool errors before continuing.')


def tool_node(key): return 'tool:' + key


def card_id(key): return 'rule:' + key


def _candidate(schema, root, label='value', depth=0):
    if depth > 12 or not isinstance(schema, dict):
        raise ValueError('Schema example is too complex')
    if '$ref' in schema:
        reference = schema['$ref']
        if not reference.startswith('#/'):
            raise ValueError('Unsupported example reference')
        resolved = root
        for part in reference[2:].split('/'):
            resolved = resolved[part.replace('~1', '/').replace('~0', '~')]
        return _candidate(resolved, root, label, depth + 1)
    for key in ('const', 'default'):
        if key in schema: return copy.deepcopy(schema[key])
    if schema.get('enum'): return copy.deepcopy(schema['enum'][0])
    for key in ('anyOf', 'oneOf', 'allOf'):
        if schema.get(key): return _candidate(schema[key][0], root, label, depth + 1)
    kind = schema.get('type')
    if isinstance(kind, list): kind = next((t for t in kind if t != 'null'), 'null')
    if kind == 'object' or 'properties' in schema:
        return {key: _candidate(schema.get('properties', {}).get(key, {}), root, key, depth + 1)
                for key in schema.get('required', [])}
    if kind == 'array':
        count = schema.get('minItems', 0)
        if count > 8: raise ValueError('Large schema example omitted')
        return [_candidate(schema.get('items', {}), root, label, depth + 1) for _ in range(count)]
    if kind == 'string':
        text = '<' + label + '>'
        text = text[:schema.get('maxLength', len(text))]
        return text + 'x' * max(0, schema.get('minLength', 0) - len(text))
    if kind in ('number', 'integer'):
        value = max(0, schema.get('minimum', 0), schema.get('exclusiveMinimum', -1) + 1)
        value = min(value, schema.get('maximum', value), schema.get('exclusiveMaximum', value + 1) - 1)
        return int(value) if kind == 'integer' else value
    if kind == 'boolean': return True
    return None


def schema_example(tool):
    try:
        arguments = _candidate(tool['inputSchema'], tool['inputSchema'])
        Draft202012Validator(tool['inputSchema']).validate(arguments)
        return {'tool': tool['name'], 'arguments': arguments, 'kind': 'shape_only',
                'requires_task_values': True}, None
    except Exception as exc:
        # A missing example is explicit; never publish an invalid call as valid.
        return None, type(exc).__name__ + ': cannot construct a validated schema-shaped example'


def render_card(tool):
    key = identity(tool)
    example, reason = schema_example(tool)
    schema = tool['inputSchema']
    lines = [f'Tool {tool["name"]}: {tool["description"]}',
             'Required arguments: ' + ', '.join(schema.get('required', [])) + '.',
             'Parameter contract: ' + json.dumps(schema, ensure_ascii=False, sort_keys=True)]
    if 'outputSchema' in tool:
        lines.append('Declared output contract: ' + json.dumps(tool['outputSchema'], ensure_ascii=False, sort_keys=True))
    if example:
        lines.append('Shape example (substitute task values): ' + json.dumps(example, ensure_ascii=False, sort_keys=True))
    else:
        lines.append('No validated shape example available; use the parameter contract.')
    return {'id': card_id(key), 'recipe': CARD, 'tool_id': key, 'depends_on': [tool_node(key)],
            'text': '\n'.join(lines), 'example': example, 'example_unavailable_reason': reason}


def render_inventory(tools):
    return {'id': INVENTORY_ID, 'recipe': INVENTORY,
            'depends_on': [card_id(identity(t)) for t in tools],
            'text': 'Available routes: ' + ', '.join(t['name'] for t in tools) +
                    '. Use only these supplied routes and their declared argument names.'}


def seed_knowledge(tools, task_id, version='Early', global_instructions=GLOBAL_RULES):
    tools = validate_catalog(tools)
    kb = {'schema_version': 1, 'task_id': task_id, 'version': version, 'tools': tools,
          'global_instructions': global_instructions,
          'blocks': [render_card(t) for t in tools] + [render_inventory(tools)]}
    validate_knowledge(kb)
    return kb


def dependency_graph(kb):
    tools = {tool_node(identity(t)) for t in kb['tools']}
    blocks = {}
    for block in kb['blocks']:
        key = block.get('id')
        if not isinstance(key, str) or not key.startswith('rule:') or key in blocks:
            raise ValueError('Rule IDs must be unique and use the rule: prefix')
        if not isinstance(block.get('text'), str):
            raise ValueError('Every rule needs text')
        deps = block.get('depends_on')
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps) or len(deps) != len(set(deps)):
            raise ValueError('Every rule needs unique explicit dependencies')
        blocks[key] = block
    all_nodes = tools | blocks.keys()
    reverse = {node: set() for node in all_nodes}
    visiting, visited = set(), set()
    def visit(node):
        if node in visiting: raise ValueError('Dependency cycle detected')
        if node in visited: return
        visiting.add(node)
        for dep in blocks.get(node, {}).get('depends_on', []):
            if dep not in all_nodes: raise ValueError('Dangling dependency: ' + dep)
            reverse[dep].add(node)
            visit(dep)
        visiting.remove(node); visited.add(node)
    for node in sorted(all_nodes): visit(node)
    return blocks, reverse


def affected_rules(kb, changed_ids, inventory_changed=False):
    blocks, reverse = dependency_graph(kb)
    pending = [tool_node(key) for key in changed_ids]
    if inventory_changed: pending.append(INVENTORY_ID)
    reached = set(pending)
    while pending:
        node = pending.pop()
        for child in reverse.get(node, ()):
            if child not in reached:
                reached.add(child); pending.append(child)
    return set(blocks) & reached


def validate_knowledge(kb):
    allowed = {'schema_version', 'task_id', 'version', 'tools', 'global_instructions', 'blocks'}
    if set(kb) != allowed:
        raise ValueError('Unknown or missing knowledge fields; put tool-specific knowledge into declared rule blocks')
    if type(kb.get('schema_version')) is not int or kb['schema_version'] != 1 or type(kb.get('task_id')) is not int:
        raise ValueError('Invalid knowledge base identity')
    if kb.get('version') not in ('Early', 'Middle', 'Late') or not isinstance(kb.get('global_instructions'), str):
        raise ValueError('Invalid knowledge base version or global instructions')
    if kb['global_instructions'] != GLOBAL_RULES:
        raise ValueError('Custom instructions must be scoped rule blocks with explicit dependencies')
    tools = validate_catalog(kb['tools'])
    by_id = {identity(t): t for t in tools}
    blocks, _ = dependency_graph(kb)
    expected = {card_id(key) for key in by_id}
    if not expected <= blocks.keys() or INVENTORY_ID not in blocks:
        raise ValueError('Tool cards and inventory are required')
    for block in blocks.values():
        if block.get('recipe') == CARD:
            key = block.get('tool_id')
            if key not in by_id or block['id'] != card_id(key) or block['depends_on'] != [tool_node(key)]:
                raise ValueError('Tool card identity/dependencies are inconsistent')
            example = block.get('example')
            if example is not None:
                if example.get('tool') != by_id[key]['name']:
                    raise ValueError('Example references a stale tool route')
                Draft202012Validator(by_id[key]['inputSchema']).validate(example['arguments'])
        elif block.get('recipe') == INVENTORY:
            if block['id'] != INVENTORY_ID or set(block['depends_on']) != expected:
                raise ValueError('Inventory must depend on every tool card')
    if blocks[INVENTORY_ID].get('recipe') != INVENTORY:
        raise ValueError('Inventory needs a supported generation recipe')
    return kb


def instructions(kb):
    validate_knowledge(kb)
    return '\n\n'.join([kb['global_instructions']] + [b['text'] for b in sorted(kb['blocks'], key=lambda b: b['id'])])
