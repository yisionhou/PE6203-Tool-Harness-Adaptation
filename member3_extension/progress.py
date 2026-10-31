"""Print compact progress without model content or credentials."""
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for label,folder,expected in [
    ('original',ROOT/'outputs/member3-replication-v2',81),
    ('expanded',ROOT/'member3_extension/workspace/outputs/member3-expansion-v1',54),
    ('migration',ROOT/'member3_migration/workspace/outputs/member3-migration-v1',27)]:
    runs,judges=Counter(),Counter()
    for path in folder.glob('repeat-*/live/comparison.json'):
        selection=path.parent.parent/'live-selection.json'
        if selection.exists():path=path.parent.parent/json.loads(selection.read_text(encoding='utf-8'))['selected']/'comparison.json'
        record=json.loads(path.read_text(encoding='utf-8'))
        runs.update(x['status'] for x in record['runs'])
    for path in folder.glob('repeat-*/scoring/evaluation.json'):
        selection=path.parent.parent/'judge-selection.json'
        if selection.exists():path=path.parent.parent/json.loads(selection.read_text(encoding='utf-8'))['selected']/'evaluation.json'
        record=json.loads(path.read_text(encoding='utf-8'))
        judges.update(x.get('judge_status','not_run') for x in record['cases'])
    print(json.dumps({'cohort':label,'planned_tasks':expected,'finished_tasks':sum(runs.values()),
        'run_states':dict(runs),'judge_states':dict(judges)},ensure_ascii=False))
