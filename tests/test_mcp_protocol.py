"""Exercise the real MCP stdio protocol, not direct function calls."""
import asyncio
import json
import os
from pathlib import Path
import sys
import pytest

pytest.importorskip('mcp')
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_tools_and_review():
    async def check():
        env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
        params=StdioServerParameters(command=sys.executable,
            args=['-m','coresense.corexense_n.mcp_server'],env=env)
        async with stdio_client(params) as (reader,writer):
            async with ClientSession(reader,writer) as session:
                await session.initialize()
                tools=await session.list_tools()
                assert {t.name for t in tools.tools} == {'list_scenarios','review_scenario',
                    'explain_belief','review_episode','review_simulation_episode'}
                result=await session.call_tool('review_scenario',{'case':'slip'})
                assert not result.isError
                data=json.loads(result.content[0].text)
                assert data['report']['action']=='HOLD'
                assert data['report']['motor_command_sent'] is False
                invalid=await session.call_tool('review_scenario',{'case':'move_robot'})
                assert invalid.isError
    asyncio.run(asyncio.wait_for(check(),timeout=20))
