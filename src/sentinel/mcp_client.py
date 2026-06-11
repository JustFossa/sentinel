"""Minimal Model Context Protocol transport used in LIVE mode only.

Wraps the official `mcp` Python SDK so the rest of Sentinel can call a remote
MCP tool synchronously: `call_tool(server, name, args)`.

- Azure MCP runs as a local stdio server: `npx -y @azure/mcp@latest server start`
- GitHub MCP is the hosted Streamable-HTTP server at api.githubcopilot.com/mcp/

Never imported in mock mode, so the demo has no dependency on `mcp`.
"""

from __future__ import annotations

import asyncio
from typing import Any


async def _stdio_call(command: str, args: list[str], tool: str, arguments: dict) -> Any:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=command, args=args)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments=arguments)
            return _unwrap(result)


async def _http_call(url: str, headers: dict, tool: str, arguments: dict) -> Any:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments=arguments)
            return _unwrap(result)


def _unwrap(result: Any) -> Any:
    """Pull text/JSON content out of an MCP CallToolResult."""
    import json

    parts = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    payload = "\n".join(parts)
    try:
        return json.loads(payload)
    except Exception:
        return payload


def stdio_call(command: str, args: list[str], tool: str, arguments: dict) -> Any:
    return asyncio.run(_stdio_call(command, args, tool, arguments))


def http_call(url: str, headers: dict, tool: str, arguments: dict) -> Any:
    return asyncio.run(_http_call(url, headers, tool, arguments))
