"""After all frozen task batches finish, repair technical scores and audit results."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import time
import json

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from member3_extension.repair_judges import repair
from member3_extension.merge_results import main as merge


def main():
    completion=ROOT/'member3/evidence/formal/completion.json'
    if completion.exists() and json.loads(completion.read_text(encoding='utf-8')).get('formal_design_complete'):
        print('Formal experiment already complete; no model requests made',flush=True)
        return
    bases=[ROOT/'outputs/member3-replication-v2',
           ROOT/'member3_extension/workspace/outputs/member3-expansion-v1',
           ROOT/'member3_migration/workspace/outputs/member3-migration-v1']
    deadline=time.monotonic()+7200
    while not all((p/'parallel-complete.json').exists() for p in bases):
        if time.monotonic()>deadline:raise TimeoutError('Task batches did not finish; no additional requests made by finalizer')
        time.sleep(2)
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(repair,bases))
    merge()
    print('Final raw-evidence audit and six-task aggregation finished',flush=True)


if __name__=='__main__':main()
