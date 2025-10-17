"""Check embedding model dimension"""
from sentence_transformers import SentenceTransformer
import os

model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
print(f"Loading embedding model: {model_name}")

model = SentenceTransformer(model_name)
test_text = "temperature cycling"
embedding = model.encode(test_text)

print(f"Text: '{test_text}'")
print(f"Embedding dimension: {len(embedding)}")
print(f"First 5 values: {embedding[:5]}")

# The Neo4j vectors are 768-dimensional
print(f"\nNeo4j vectors are 768-dimensional")
print(f"Model generates {len(embedding)}-dimensional vectors")

if len(embedding) != 768:
    print(f"\n⚠️  DIMENSION MISMATCH!")
    print(f"Need to use a model that generates 768-dimensional vectors")
    print(f"Or re-generate Neo4j vectors with the current model")
