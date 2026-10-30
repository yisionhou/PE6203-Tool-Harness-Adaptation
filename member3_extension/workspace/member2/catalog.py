"""Strict, task-independent tool observations and field-level change detection."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re
from jsonschema import Draft202012Validator

NAME = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
FIELDS = {'name', 'source_name', 'source_server', 'description', 'inputSchema', 'outputSchema', 'annotations'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def identity(tool):
    return tool['source_server'] + '::' + tool['source_name']


def _local_refs_only(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ('$ref', '$dynamicRef') and (not isinstance(child, str) or not child.startswith('#')):
                raise ValueError('Only local schema references are supported for offline validation')
            _local_refs_only(child)
    elif isinstance(value, list):
        for child in value:
            _local_refs_only(child)


def validate_catalog(tools):
    if not isinstance(tools, list) or not tools:
        raise ValueError('Catalog must be a nonempty list of tool definitions')
    ids, names = set(), set()
    for tool in tools:
        if not isinstance(tool, dict) or set(tool) - FIELDS:
            raise ValueError('Catalog accepts tool definition fields only, not task/answer/trajectory data')
        for field in ('name', 'source_name'):
            if not isinstance(tool.get(field), str) or not NAME.fullmatch(tool[field]):
                raise ValueError(f'Invalid tool {field}')
        if not isinstance(tool.get('source_server'), str) or not tool['source_server'] or '::' in tool['source_server']:
            raise ValueError('Invalid source_server')
        if not isinstance(tool.get('description'), str):
            raise ValueError('Tool description is required')
        if identity(tool) in ids or tool['name'] in names:
            raise ValueError('Duplicate tool identity or exposed name')
        ids.add(identity(tool)); names.add(tool['name'])
        for field in ('inputSchema', 'outputSchema'):
            if field == 'outputSchema' and field not in tool:
                continue
            schema = tool.get(field)
            if not isinstance(schema, dict) or (field == 'inputSchema' and schema.get('type') != 'object'):
                raise ValueError(f'Invalid {field}')
            _local_refs_only(schema)
            try:
                Draft202012Validator.check_schema(schema)
            except Exception as exc:
                raise ValueError(f"Invalid {field}: {type(exc).__name__}") from exc
    canonical(tools)  # Reject non-finite/non-JSON values before saving evidence.
    return copy.deepcopy(sorted(tools, key=identity))


def read_catalog(path):
    # Only this explicitly named tools file is opened. No neighboring results.
    raw = Path(path).read_bytes()
    value = json.loads(raw.decode('utf-8-sig'))
    return validate_catalog(value), hashlib.sha256(raw).hexdigest(), raw


def _pointer(part):
    return str(part).replace('~', '~0').replace('/', '~1')


def changed_paths(before, after, prefix=''):
    if type(before) is not type(after):
        return [prefix or '/']
    if isinstance(before, dict):
        paths = []
        for key in sorted(before.keys() | after.keys()):
            path = prefix + '/' + _pointer(key)
            if key not in before or key not in after:
                paths.append(path)
            else:
                paths.extend(changed_paths(before[key], after[key], path))
        return paths
    # Array order is conservatively treated as observable (examples/enums/defaults).
    return [] if before == after else [prefix or '/']


def diff_catalogs(before, after):
    old = {identity(t): t for t in validate_catalog(before)}
    new = {identity(t): t for t in validate_catalog(after)}
    changed = {}
    for key in sorted(old.keys() & new.keys()):
        paths = changed_paths(old[key], new[key])
        if paths:
            kinds = set()
            for path in paths:
                if path == '/description' or path.startswith('/inputSchema/') and path.endswith('/description'):
                    kinds.add('description')
                elif path.startswith('/inputSchema'):
                    kinds.add('parameter')
                elif path.startswith('/outputSchema'):
                    kinds.add('output')
                elif path == '/name':
                    kinds.add('routing')
                else:
                    kinds.add('metadata')
            changed[key] = {'paths': paths, 'kinds': sorted(kinds)}
    return {'added': sorted(new.keys() - old.keys()), 'removed': sorted(old.keys() - new.keys()),
            'changed': changed, 'unchanged': sorted((old.keys() & new.keys()) - changed.keys())}
