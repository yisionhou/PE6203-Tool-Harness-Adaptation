"""Run the local test suite with real HTTP disabled and usable keys removed."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
os.chdir(ROOT)
for name in ('ARK_API_KEY', 'JUDGE_API_KEY', 'OPENAI_API_KEY'):
    os.environ[name] = ''
os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:9'
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,::1'
temp = ROOT/'.tmp'
temp.mkdir(exist_ok=True)
os.environ['TEMP'] = os.environ['TMP'] = str(temp)

from member3.restore_evidence import restore
restore()

import httpx
import pytest

blocked = []


def deny(*args, **kwargs):
    blocked.append('real HTTP attempted')
    raise AssertionError('Real HTTP is disabled for offline validation')


async def deny_async(*args, **kwargs):
    return deny(*args, **kwargs)


httpx.Client.send = deny
httpx.AsyncClient.send = deny_async


class Counts:
    def pytest_terminal_summary(self, terminalreporter):
        self.values = {key: len(items) for key, items in terminalreporter.stats.items()
                       if key in ('passed', 'failed', 'error', 'skipped')}


counts = Counts()
code = pytest.main(['-q', 'member1/tests', 'member2/tests', 'member3/tests',
                   'member3_extension/test_recovery.py', '--basetemp', '.tmp/offline-tests',
                   '-o', 'faulthandler_timeout=30'], plugins=[counts])
report = {'pytest_exit_code': int(code), 'test_counts': counts.values,
          'real_http_attempts': len(blocked), 'model_api_requests': 0}
(temp/'publication-validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
raise SystemExit(code)
