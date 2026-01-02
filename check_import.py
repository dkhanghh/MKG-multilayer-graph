try:
    from langchain_mcp_adapters.sessions import SSEConnection
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")
