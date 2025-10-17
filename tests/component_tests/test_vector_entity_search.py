"""Quick test for vector-based entity search"""
from chatbot_graphs.rag_graph import get_retriever
import time

print("Getting retriever...")
start = time.time()
retriever = get_retriever()
print(f"Retriever ready in {time.time() - start:.2f}s\n")

print("Testing entity search with vector similarity:")
print("=" * 60)

# Test single entity
entity_name = "temperature cycling"
print(f"\nSearching for: '{entity_name}'")
start = time.time()
result = retriever.entity_graph_search(entity_name, depth=2)
elapsed = time.time() - start

print(f"Completed in {elapsed:.2f}s")
print(f"\nResult:\n{result}")
print("\n" + "=" * 60)
