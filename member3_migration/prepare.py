"""Validate official task 90 catalogs and public API availability before inference."""
import asyncio
from datetime import timedelta
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'member3_migration/workspace'
sys.path[:0]=[str(WORK),str(WORK/'src')]
from member1.run_versions import run_one
from member1.stage2 import build_runtime_config
from member2.build import build
from member3.experiment import freeze


async def services(output):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    records=[]
    for version in ('Early','Middle','Late'):
        config,_=build_runtime_config(version,output/f'probe-{version}',[90])
        for alias in ('cards','leetcode'):
            service=config['mcpServers'][alias]
            params=StdioServerParameters(command=service['command'],args=service['args'])
            async with stdio_client(params) as (reader,writer):
                async with ClientSession(reader,writer) as session:
                    await session.initialize()
                    tool='search_cards' if alias=='cards' else 'get_problem' if version=='Late' else 'get_daily_challenge'
                    arguments={'query':'青眼白龙'} if alias=='cards' else {'daily':True} if version=='Late' else {}
                    try:
                        result=await session.call_tool(tool,arguments,read_timeout_seconds=timedelta(seconds=40))
                        raw=result.model_dump(mode='json')
                        texts=''.join(x.text for x in result.content if x.type=='text')
                        ok=not result.isError and 'error' not in texts.lower() and len(texts)>20
                        records.append({'version':version,'service':alias,'tool':tool,'arguments':arguments,
                                        'ok':ok,'result':raw})
                    except Exception as exc:
                        records.append({'version':version,'service':alias,'tool':tool,'ok':False,'error':str(exc)})
                    print('Public service probe',version,alias,records[-1]['ok'],flush=True)
    (output/'public-service-probes.json').write_text(json.dumps({'paid_requests':0,'records':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return all(x['ok'] for x in records)


def main():
    catalogs=WORK/'outputs/catalogs'
    catalogs.mkdir(parents=True,exist_ok=False)
    for version in ('Early','Middle','Late'):
        result=run_one(version,90,catalogs,True)
        if result['status']!='tools_ready':raise RuntimeError('Task 90 catalog validation failed')
    # Prove the intended migration from actual tool discovery, before model calls.
    early=json.loads((catalogs/'Early-task-90/result/tools.json').read_text(encoding='utf-8'))
    late=json.loads((catalogs/'Late-task-90/result/tools.json').read_text(encoding='utf-8'))
    assert any(t['source_name']=='get_daily_challenge' for t in early)
    assert not any(t['source_name']=='get_daily_challenge' for t in late)
    assert any(t['source_name']=='get_problem' for t in late)
    if not asyncio.run(services(catalogs)):
        raise RuntimeError('Public APIs not consistently available; no paid task-90 runs requested')
    build(catalogs,WORK/'member2/evidence/adaptation',[90])
    freeze(WORK/'member3/studies/migration-v1',3)
    (WORK/'outputs/prepared.json').write_text(json.dumps({'status':'ready','task_id':90,'conditions':27,'paid_requests':0}),encoding='utf-8')
    print('Official task 90 ready: deleted route confirmed, public services probed',flush=True)


if __name__=='__main__':main()
