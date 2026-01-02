from chatbot_graphs.tools.mcp import get_mcp_tools
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

print("Testing MCP Tool Loading...")
try:
    tools = get_mcp_tools()
    print(f"Successfully loaded {len(tools)} tools:")
    for tool in tools:
        print(f" - {tool.name}")
except Exception as e:
    print(f"Failed to load tools: {e}")
