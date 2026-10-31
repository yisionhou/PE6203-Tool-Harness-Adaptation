"""Validate added services, freeze task scope, then run three fresh repetitions."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'member3_extension/workspace'


def call(*args):
    subprocess.run([sys.executable,'-X','utf8',*map(str,args)],cwd=WORK,check=True)


def main():
    probe = '''from pathlib import Path
import json
from member1.run_versions import run_one
root=Path('outputs/catalogs').resolve()
root.mkdir(parents=True,exist_ok=False)
rows=[]
for version in ('Early','Middle','Late'):
 for task in (3,24):
  row=run_one(version,task,root,True)
  rows.append(row)
  (root/'suite.json').write_text(json.dumps({'schema_version':1,'mode':'tools_only','versions':['Early','Middle','Late'],'task_ids':[3,24],'runs':rows},indent=2),encoding='utf-8')
  if row['status']!='tools_ready':raise RuntimeError('Expanded tool validation failed; no paid tasks requested')
'''
    call('-c',probe)
    call('member2/build.py','--catalog-root','outputs/catalogs','--output-dir','member2/evidence/adaptation',
         '--task-ids',3,24)
    call('member3/experiment.py','freeze','--output-dir','member3/studies/expansion-v1','--repetitions',3)
    call('member3/experiment.py','run','--study','member3/studies/expansion-v1',
         '--env-file',ROOT/'.env','--output-dir','outputs/member3-expansion-v1')


if __name__ == '__main__':main()
