"""MCP Tool Loader leveraging langchain-mcp-adapters."""
import asyncio
import logging
from typing import List

import nest_asyncio
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.sessions import SSEConnection

from server.core.config import MCP_SETTINGS

logger = logging.getLogger(__name__)

_CACHED_TOOLS: List[BaseTool] | None = None


async def get_mcp_tools_async() -> List[BaseTool]:
    """Asynchronously load MCP tools from configured servers."""
    all_tools: List[BaseTool] = []

    servers = MCP_SETTINGS.get("servers", {})
    for server_name, config in servers.items():
        url = config.get("url")
        transport = config.get("transport")
        enabled_tools = config.get("enabled_tools", [])

        if not url:
            logger.debug("Skipping MCP server %s: no URL", server_name)
            continue
        if transport != "sse":
            logger.debug("Skipping MCP server %s: unsupported transport %s", server_name, transport)
            continue

        logger.info("Connecting to MCP server: %s at %s", server_name, url)

        try:
            connection = SSEConnection(url=url, transport="sse")
            tools = await load_mcp_tools(None, connection=connection)

            if enabled_tools:
                tools = [t for t in tools if t.name in enabled_tools]

            logger.info("Loaded %d tools from %s", len(tools), server_name)
            all_tools.extend(tools)
        except Exception as exc:
            logger.error("Failed to load tools from %s: %s", server_name, exc)

    return all_tools


def get_mcp_tools() -> List[BaseTool]:
    """Synchronous wrapper to get MCP tools.

    Uses ``nest_asyncio`` to allow running the async loader even if an
    event loop is already running. Results are cached after first load.
    """
    global _CACHED_TOOLS

    if _CACHED_TOOLS is not None:
        return _CACHED_TOOLS

    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        nest_asyncio.apply(loop)
        result = loop.run_until_complete(get_mcp_tools_async())

        if result is not None:
            _CACHED_TOOLS = result

        return result

    except Exception as exc:
        logger.error("Error loading MCP tools: %s", exc)
        return []
