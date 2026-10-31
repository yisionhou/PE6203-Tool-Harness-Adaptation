"""Create explicitly labelled interface fixtures, not member 2's adaptation method."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from member1.protocol import DEFAULTS


def build(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    versions = ('Early', 'Middle', 'Late')
    catalogs = {v: json.loads((ROOT / f'member1/evidence/stage2/validation/{v}-task-156/result/tools.json')
        .read_text(encoding='utf-8')) for v in versions}
    dirs = {'no_update': {}, 'full_rewrite': {}, 'selective_patch': {}}
    for version in versions:
        for strategy in dirs:
            directory = 'no_update' if strategy == 'no_update' else f'{strategy}/{version}'
            dirs[strategy][version] = directory
            target = output / directory / '156.json'
            if target.exists():
                continue
            tools = copy.deepcopy(catalogs['Early'] if strategy == 'no_update' else catalogs[version])
            recipe = 'Frozen saved Early catalog.'
            if strategy == 'full_rewrite':
                recipe = 'Fixture: import the entire saved target-version catalog, no LLM rewrite.'
            elif strategy == 'selective_patch':
                old = {(t['source_server'], t['source_name']): t for t in catalogs['Early']}
                tools = [copy.deepcopy(old.get((t['source_server'], t['source_name']), t))
                    if old.get((t['source_server'], t['source_name'])) == t else copy.deepcopy(t) for t in tools]
                recipe = 'Fixture: replace changed catalog entries and retain identical Early entries; no learned adaptation.'
            packet = {'schema_version': 1, 'task_id': 156, 'strategy': strategy,
                'source_version': 'Early' if strategy == 'no_update' else version,
                'test_fixture': True, 'fixture_recipe': recipe, 'instructions': '',
                'update_cost': None, 'tools': tools}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    plan = {'schema_version': 1, 'purpose': 'interface_smoke', 'task_ids': [156],
        'versions': list(versions), 'run_config': DEFAULTS, 'knowledge_dirs': dirs}
    (output / 'comparison.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    return output / 'comparison.json'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    print(build(parser.parse_args().output_dir))
