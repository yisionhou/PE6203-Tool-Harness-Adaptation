"""Configure a separate expanded runner without editing a running frozen study."""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'member3_extension/workspace'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    manifest = json.loads((DEST/'member1/tasks_manifest.json').read_text(encoding='utf-8'))
    extras = {
        'mcp-sequentialthinking-tools': {'alias':'thinktools','package':'mcp-sequentialthinking-tools','entry':'dist/index.js','kind':'node'},
        '@modelcontextprotocol/server-filesystem': {'alias':'fs_official','package':'@modelcontextprotocol/server-filesystem','entry':'dist/index.js','kind':'node'},
        'server-sequential-thinking': {'alias':'thinking','package':'@modelcontextprotocol/server-sequential-thinking','entry':'dist/index.js','kind':'node'},
    }
    manifest['services'].update(extras)
    for i, value in enumerate(manifest['versions'].values()): value['port'] = 3151 + i*2
    new_tasks = [
        {'id':3,'summary_zh':'比较日志并写入新报告','services':['mcp-filesystem-server','time-mcp','mcp-sequentialthinking-tools'],
         'change_types':['DESC','PARAM'],'notes':'Official task unchanged; additional local report-writing coverage.'},
        {'id':24,'summary_zh':'读取昨日日志并创建跟进待办','services':['@modelcontextprotocol/server-filesystem','server-sequential-thinking','mcp-tasks'],
         'change_types':['TOOL','DESC'],'notes':'Late official snapshot deletes deprecated read_file, retaining this task\'s read_text_file. This is a retention control, not forced migration. server-sequential-thinking alias follows upstream custom/utils/test_utils.py.'},
    ]
    manifest['tasks'] = [x for x in manifest['tasks'] if x['id'] not in (3,24)] + new_tasks
    manifest['selection_rule'] = 'Expanded before any outcomes for task 3 or 24: local official tasks with additional writing and retention coverage. Original task questions/labels remain unchanged.'
    save(DEST/'member1/tasks_manifest.json',manifest)
    provenance = json.loads((DEST/'member1/snapshots/provenance.json').read_text(encoding='utf-8'))
    fetched = json.loads((ROOT/'member3_extension/snapshots/provenance.json').read_text(encoding='utf-8'))
    for record in fetched['files']:
        parts = Path(record['local_path']).parts
        rel = Path('member1/snapshots').joinpath(*parts[2:])
        target = DEST/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/record['local_path'],target)
        rec = {**record, 'local_path':rel.as_posix()}
        if rec['server'] == '@modelcontextprotocol/server-sequential-thinking': rec['server'] = 'server-sequential-thinking'
        provenance['files'].append(rec)
    save(DEST/'member1/snapshots/provenance.json',provenance)
    # The official filesystem service accepts allowed directories on argv.
    # Use the per-case workspace instead of the upstream config's broad '/'.
    stage = DEST/'member1/stage2.py'
    text = stage.read_text(encoding='utf-8')
    needle = "config.update(command=node, args=[str(executable)])"
    replacement = "config.update(command=node, args=[str(executable)] + ([str(workspace)] if server == '@modelcontextprotocol/server-filesystem' else []))"
    if needle not in text: raise ValueError('Unexpected stage2 source')
    stage.write_text(text.replace(needle,replacement),encoding='utf-8')
    judge = DEST/'member2/evidence/pre_handoff/judge-config-v2.json'
    judge.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'member2/evidence/pre_handoff/judge-config-v2.json',judge)
    package = json.loads((DEST/'package.json').read_text(encoding='utf-8'))
    for server, service in extras.items():
        metadata = json.loads((ROOT/'member3_extension/snapshots/original'/service['alias']/'package.json').read_text(encoding='utf-8'))
        package['dependencies'][service['package']] = metadata['version']
    save(DEST/'package.json',package)
    print('Configured tasks 3 and 24, isolated ports 3151/3153/3155; original study unchanged')


if __name__ == '__main__': main()
