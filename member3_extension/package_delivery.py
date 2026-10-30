"""Package member-3 code, frozen inputs and raw evidence without credentials."""
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dotenv import dotenv_values


def main():
    destination=ROOT/'member3_delivery_20261030.zip'
    if destination.exists():raise FileExistsError('Delivery archive already exists')
    roots=['member3','member3_extension','member3_migration','outputs/member3-replication-v2']
    files=set()
    excluded={'node_modules','.venv','.tmp','.npm-cache','__pycache__','.pytest_cache','runtime','workers'}
    for relative in roots:
        for directory,names,entries in os.walk(ROOT/relative):
            names[:]=[n for n in names if n not in excluded]
            for name in entries:
                if name.startswith('.env') or name.endswith(('.pyc','.lock')):continue
                path=Path(directory)/name
                if path.is_file():files.add(path)
    for relative in ['docs/member3-report-section.md','docs/member3-offline-review.md',
                     'docs/member3-offline-fixes.md','README.md','package.json','package-lock.json',
                     'member1/requirements-lock.txt','member1/tasks_manifest.json']:
        files.add(ROOT/relative)
    # Current original knowledge packages identify the reused generation costs.
    for path in (ROOT/'member2/evidence/adaptation').rglob('*'):
        if path.is_file():files.add(path)
    for folder in ('member1','member2'):
        files.update((ROOT/folder).glob('*.py'))
    for path in (ROOT/'member1/snapshots').rglob('*'):
        if path.is_file():files.add(path)
    files.add(ROOT/'member1/windows_paths.mjs')
    key=dotenv_values(ROOT/'.env').get('ARK_API_KEY','')
    inventory=[]
    for path in sorted(files):
        raw=path.read_bytes()
        if key and key.encode() in raw:raise ValueError('Credential found in candidate artifact; archive not created')
        inventory.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for item in inventory:archive.write(ROOT/item['path'],item['path'])
        archive.writestr('DELIVERY_README.txt',
            'Member 3 delivery overlay for the existing PE6203 repository.\n'
            'Start with docs/member3-report-section.md and member3/evidence/formal/summary.md.\n'
            'Includes new raw trajectories, all judge attempts, frozen inputs and implementation.\n'
            'Install dependencies from package-lock/requirements-lock in the existing repository.\n'
            'No .env, API credentials, installed dependencies or transient runtime caches are included.\n')
        archive.writestr('DELIVERY_MANIFEST.json',json.dumps(inventory,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(destination) as archive:
        bad=archive.testzip()
        if bad:raise ValueError('Archive integrity check failed: '+bad)
    print(json.dumps({'archive':str(destination),'files':len(inventory),'bytes':destination.stat().st_size,
                      'credential_scan':'passed','zip_integrity':'passed'},ensure_ascii=False))


if __name__=='__main__':main()
