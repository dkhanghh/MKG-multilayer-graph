from langchain_mcp_adapters.tools import load_mcp_tools
import inspect

print(inspect.signature(load_mcp_tools))
print(inspect.getdoc(load_mcp_tools))
