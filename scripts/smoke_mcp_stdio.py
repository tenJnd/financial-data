"""Smoke-test the MCP server over stdio as a real Hermes client would.

Run::

    PYTHONPATH=. python scripts/smoke_mcp_stdio.py
"""
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.hermes_tools.server"],
        env=None,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"server advertises {len(tools.tools)} tools:")
            for t in tools.tools:
                print(f"  - {t.name}")

            print("\ncall gurufocus_summary AWI:")
            result = await session.call_tool("gurufocus_summary", {"ticker": "AWI"})
            for c in result.content:
                if hasattr(c, "text"):
                    data = json.loads(c.text)
                    print(f"  metric count: {len(data.get('metrics', {}))}")
                    for k in ("moat_score", "price_to_gf_value", "price_to_graham_number"):
                        print(f"  {k}: {data['metrics'].get(k)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
