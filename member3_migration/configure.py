"""Isolated, pinned official task 90 deletion/migration cohort."""
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'member3_migration/workspace'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    DEST.mkdir(parents=True,exist_ok=False)
    for folder in ('member1','member2','member3'):
        (DEST/folder).mkdir()
        for file in (ROOT/folder).glob('*.py'):shutil.copy2(file,DEST/folder/file.name)
    shutil.copytree(ROOT/'member1/snapshots',DEST/'member1/snapshots')
    shutil.copytree(ROOT/'src/custom',DEST/'src/custom')
    shutil.copytree(ROOT/'anotation_path/txt',DEST/'anotation_path/txt')
    for path in ('member1/tasks_manifest.json','member1/windows_paths.mjs','member1/requirements-lock.txt','package.json','package-lock.json'):
        shutil.copy2(ROOT/path,DEST/path)
    manifest=json.loads((DEST/'member1/tasks_manifest.json').read_text(encoding='utf-8'))
    extras={'ygocdb-mcp-server':{'alias':'cards','package':'ygocdb-mcp-server','entry':'dist/index.js','kind':'node'},
            '@jinzcdev/leetcode-mcp-server':{'alias':'leetcode','package':'@jinzcdev/leetcode-mcp-server','entry':'build/index.js','kind':'node'}}
    manifest['services'].update(extras)
    for index,value in enumerate(manifest['versions'].values()):value['port']=3251+index*2
    manifest['tasks'].append({'id':90,'summary_zh':'卡片资料、图片与当日 LeetCode 题目',
        'services':list(extras),'change_types':['TOOL','DESC'],
        'notes':'Official task unchanged; Late deletes get_daily_challenge and migrates daily lookup to get_problem(daily=true). Public read-only services; availability probed before model calls.'})
    manifest['selection_rule']='Official selected task 90 chosen before its first outcome because its referenced daily challenge route is deleted in layer 2; no score/reference-answer based task selection.'
    save(DEST/'member1/tasks_manifest.json',manifest)
    provenance=json.loads((DEST/'member1/snapshots/provenance.json').read_text(encoding='utf-8'))
    fetched=json.loads((ROOT/'member3_migration/snapshots/provenance.json').read_text(encoding='utf-8'))
    for record in fetched['files']:
        rel=Path('member1/snapshots').joinpath(*Path(record['local_path']).parts[2:])
        target=DEST/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/record['local_path'],target)
        provenance['files'].append({**record,'local_path':rel.as_posix()})
    save(DEST/'member1/snapshots/provenance.json',provenance)
    stage=DEST/'member1/stage2.py'
    text=stage.read_text(encoding='utf-8')
    needle='config.update(command=node, args=[str(executable)])'
    replacement="config.update(command=node, args=[str(executable)] + (['--site', 'global'] if server == '@jinzcdev/leetcode-mcp-server' else []))"
    if needle not in text:raise ValueError('Unexpected stage2 source')
    stage.write_text(text.replace(needle,replacement),encoding='utf-8')
    package=json.loads((DEST/'package.json').read_text(encoding='utf-8'))
    for service in extras.values():
        meta=json.loads((ROOT/'member3_migration/snapshots/original'/service['alias']/'package.json').read_text(encoding='utf-8'))
        package['dependencies'][service['package']]=meta['version']
    save(DEST/'package.json',package)
    target=DEST/'member2/evidence/pre_handoff/judge-config-v2.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'member2/evidence/pre_handoff/judge-config-v2.json',target)
    experiment=DEST/'member3/experiment.py'
    text=experiment.read_text(encoding='utf-8').replace('fresh_repetitions_of_existing_official_subset','official_task_90_deleted_daily_route')
    text=text.replace('Replication only; expanded migration and retention coverage remain pending.','Official task 90: get_daily_challenge deleted, get_problem(daily=true) migration; original question unchanged.')
    experiment.write_text(text,encoding='utf-8')
    print('Configured official task 90; ports 3251/3253/3255',flush=True)


if __name__=='__main__':main()
