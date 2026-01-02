"""
MCP Tool Loader leveraging langchain-mcp-adapters.
"""
import asyncio
from typing import List, Any
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.sessions import SSEConnection
from server.core.config import MCP_SETTINGS

async def get_mcp_tools_async() -> List[BaseTool]:
    """
    Asynchronously load MCP tools from configured servers.
    """
    all_tools = []
    
    servers = MCP_SETTINGS.get("servers", {})
    for server_name, config in servers.items():
        url = config.get("url")
        transport = config.get("transport")
        enabled_tools = config.get("enabled_tools", [])
        
        if not url:
            print(f"[MCP] Skipping server {server_name}: No URL provided")
            continue
            
        if transport != "sse":
            print(f"[MCP] Skipping server {server_name}: Only SSE transport is supported currently")
            continue
            
        print(f"[MCP] Connecting to server: {server_name} at {url}")
        
        try:
            # Create connection object
            connection = SSEConnection(url=url, transport="sse")
            
            # load_mcp_tools manages the connection via the connection object
            # session is required positional argument, pass None when using connection
            tools = await load_mcp_tools(None, connection=connection)
            
            # Filter tools if enabled_tools is specified
            if enabled_tools:
                filtered_tools = [t for t in tools if t.name in enabled_tools]
                print(f"[MCP] Loaded {len(filtered_tools)} tools from {server_name} (filtered from {len(tools)})")
                all_tools.extend(filtered_tools)
            else:
                print(f"[MCP] Loaded {len(tools)} tools from {server_name}")
                all_tools.extend(tools)
                
        except Exception as e:
            print(f"[MCP] Failed to load tools from {server_name}: {e}")
            
    print(f"[MCP DEBUG] get_mcp_tools_async returning all_tools with size: {len(all_tools)}")
    return all_tools
import nest_asyncio

_CACHED_TOOLS = None

def get_mcp_tools() -> List[BaseTool]:
    """
    Synchronous wrapper to get MCP tools.
    Uses nest_asyncio to allow running the async loader even if an event loop is already running.
    Implements caching to avoid reconnecting on every request.
    """
    global _CACHED_TOOLS
    
    # Return cached tools if available
    if _CACHED_TOOLS is not None:
        return _CACHED_TOOLS
        
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Apply nest_asyncio to allow re-entrant loop
        nest_asyncio.apply(loop)
        
        result = loop.run_until_complete(get_mcp_tools_async())
        print(f"[MCP DEBUG] Wrapper got result with size: {len(result) if result else 'None'}")
        
        # Cache the result if successful (even if empty list, to avoid retry loops if config is bad)
        if result is not None:
             _CACHED_TOOLS = result
             
        return result

    except Exception as e:
        print(f"[MCP] Error loading tools: {e}")
        return []
