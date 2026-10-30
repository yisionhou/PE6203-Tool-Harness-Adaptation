"""Probe official clock snapshots without changing them or calling a model."""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from member1.stage2 import build_runtime_config
from member3.analyze import save, VERSIONS


async def check(output):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for version in VERSIONS:
        config, context = build_runtime_config(version, output/version, [156])
        service = config['mcpServers']['clock']
        params = StdioServerParameters(command=service['command'], args=service['args'])
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                for name, arguments in [('get_time_info', {'timezone': 'Asia/Tokyo'}),
                    ('get_current_time', {'timezone': 'Asia/Tokyo', 'format': 'locale'}),
                    ('get_current_time', {'timezone': 'Asia/Tokyo', 'format': 'timestamp'})]:
                    start = time.time()
                    raw = await session.call_tool(name, arguments)
                    end = time.time()
                    text = ''.join(c.text for c in raw.content if c.type == 'text')
                    value = json.loads(text)
                    try:
                        if name == 'get_time_info':
                            observed = datetime(*(value[k] for k in ('year', 'month', 'day', 'hour', 'minute', 'second')),
                                                tzinfo=ZoneInfo('Asia/Tokyo')).timestamp()
                        elif arguments['format'] == 'timestamp':
                            observed = float(value['time']) / 1000
                        else:
                            observed = datetime.strptime(value['time'], '%Y/%m/%d %H:%M:%S').replace(
                                tzinfo=ZoneInfo('Asia/Tokyo')).timestamp()
                        drift = observed - (start+end)/2
                        consistent = start-3 <= observed <= end+3
                        error = None
                    except (ValueError, TypeError, KeyError) as exc:
                        drift, consistent, error = None, False, str(exc)
                    records.append({'version': version, 'tool': name, 'arguments': arguments,
                        'raw_result': raw.model_dump(mode='json'), 'start_epoch': start, 'end_epoch': end,
                        'drift_seconds': drift, 'within_3_seconds': consistent, 'parse_error': error,
                        'service_sha256': context['services']['clock']['entry_sha256']})
    result = {'schema_version': 1, 'kind': 'live_service_probe_no_model', 'paid_requests': 0,
        'all_consistent': all(r['within_3_seconds'] for r in records), 'records': records,
        'policy': 'Official snapshots are unchanged. Service defects are not strategy failures.'}
    save(output/'clock-audit.json', result)
    print(json.dumps({'all_consistent': result['all_consistent'],
        'checks': len(records), 'paid_requests': 0}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    asyncio.run(check(parser.parse_args().output_dir))
