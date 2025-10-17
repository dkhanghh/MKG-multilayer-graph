"""Test with lower threshold to see what similarities we get"""
import os
os.environ["EMBEDDING_MODEL"] = "sentence-transformers/all-mpnet-base-v2"

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Setup
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
username = os.getenv("NEO4J_USERNAME", "neo4j")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "neo4j")

model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
print("Model loaded, dimension:", len(model.encode("test")))

# Generate embedding
query_text = "temperature cycling"
query_vector = model.encode(query_text).tolist()
print(f"\nSearching for: '{query_text}'")

driver = GraphDatabase.driver(uri, auth=(username, password))

with driver.session(database=database) as session:
    # Simplified query - just get top 3 with any similarity
    cypher = """
    MATCH (n)
    WHERE n._name_vector IS NOT NULL
    WITH n,
         reduce(dot = 0.0, i IN range(0, size(n._name_vector)-1) |
              dot + n._name_vector[i] * $query_vector[i]) /
              (sqrt(reduce(sum = 0.0, x IN n._name_vector | sum + x * x)) *
               sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) as similarity
    WHERE similarity > 0
    RETURN n.name as name, similarity
    ORDER BY similarity DESC
    LIMIT 5
    """

    result = session.run(cypher, query_vector=query_vector)

    print("\nTop 5 matches:")
    for record in result:
        print(f"  {record['similarity']:.4f} - {record['name']}")

driver.close()
