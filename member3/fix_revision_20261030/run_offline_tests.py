"""Review-only runner: disable real HTTP and remove usable API credentials."""
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
os.chdir(ROOT);sys.path[:0]=[str(ROOT),str(ROOT/'src')]
for name in ('ARK_API_KEY','JUDGE_API_KEY','OPENAI_API_KEY'):
    os.environ[name]=''
os.environ['HTTP_PROXY']='http://127.0.0.1:9'
os.environ['HTTPS_PROXY']='http://127.0.0.1:9'
os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
os.environ['TEMP']=str(ROOT/'.tmp');os.environ['TMP']=str(ROOT/'.tmp')
import httpx
blocked=[]
def deny(*args,**kwargs):
    blocked.append('real HTTP attempted')
    raise AssertionError('HTTP disabled for offline code review')
async def deny_async(*args,**kwargs):return deny(*args,**kwargs)
httpx.Client.send=deny;httpx.AsyncClient.send=deny_async
import pytest
class Counts:
    def pytest_terminal_summary(self, terminalreporter):
        self.counts={k:len(v) for k,v in terminalreporter.stats.items() if k in ('passed','failed','error','skipped')}
counts=Counts()
code=pytest.main(['-q','member1/tests','member2/tests','member3/tests',
                 'member3_extension/test_recovery.py','--basetemp','.tmp/fix-full-suite'],plugins=[counts])
report={'pytest_exit_code':int(code),'real_http_requests_allowed':0,
        'blocked_real_http_attempts':len(blocked),'usable_key_environment_removed':True,'test_counts':counts.counts,'model_api_requests':0}
(ROOT/'member3/fix_revision_20261030/tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
raise SystemExit(code)
