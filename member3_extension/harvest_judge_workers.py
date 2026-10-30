"""Offline consolidation of saved worker receipts; never calls a model."""
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from member3.analyze import read,save


def harvest():
    bases=[ROOT/'outputs/member3-replication-v2',ROOT/'member3_extension/workspace/outputs/member3-expansion-v1',
           ROOT/'member3_migration/workspace/outputs/member3-migration-v1']
    count=0
    for base in bases:
        for folder in base.glob('repeat-*'):
            selection=folder/'judge-selection.json'
            if not selection.exists():continue
            target=folder/read(selection)['selected']
            master=read(target/'evaluation.json');changed=False
            for item in master['cases']:
                worker=target/'workers'/item['case_id']
                file=worker/'cases'/item['case_id']/'judge-1.json'
                evaluation=worker/'evaluation.json'
                if not file.exists() or not evaluation.exists():continue
                try:
                    receipt=read(file);result=read(evaluation)['cases'][0]
                except (ValueError,OSError):continue
                if result.get('judge_status')=='not_run':continue
                if receipt['protocol_sha256']!=master['protocol_sha256'] or receipt['prompt_sha256']!=item['prompts'][0]['sha256']:
                    raise ValueError('Worker evidence mismatch')
                dest=target/'cases'/item['case_id']/'judge-1.json'
                if not dest.exists():shutil.copyfile(file,dest)
                elif read(dest)!=receipt:raise ValueError('Existing receipt differs; refusing overwrite')
                if item.get('judge_status')=='not_run':
                    item.update(result);changed=True;count+=1
            if changed:save(target/'evaluation.json',master)
    print('Offline worker receipts consolidated:',count,flush=True)
    return count


if __name__=='__main__':harvest()
