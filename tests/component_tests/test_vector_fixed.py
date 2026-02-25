"""Test vector-based entity search with correct model"""
import os
os.environ["EMBEDDING_MODEL"] = "sentence-transformers/all-mpnet-base-v2"

from rag.retrievers import get_retriever
import time

print("Getting retriever with 768-dim model...")
start = time.time()
retriever = get_retriever()
print(f"Retriever ready in {time.time() - start:.2f}s\n")

print("Testing entity search with vector similarity:")
print("=" * 70)

# Test entities
entities = ["temperature cycling", "thermal shock", "JEDEC"]

for entity_name in entities:
    print(f"\nSearching for: '{entity_name}'")
    start = time.time()
    result = retriever.entity_graph_search(entity_name, depth=2)
    elapsed = time.time() - start

    print(f"Completed in {elapsed:.2f}s")
    if "not found" in result.lower():
        print(f"❌ {result}")
    else:
        # Extract first few lines
        lines = result.split('\n')[:5]
        print(f"✓ Found!")
        for line in lines:
            if line.strip():
                print(f"  {line}")

print("\n" + "=" * 70)
