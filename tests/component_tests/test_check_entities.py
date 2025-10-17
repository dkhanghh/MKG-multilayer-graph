"""Check what entities exist in Neo4j"""
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
username = os.getenv("NEO4J_USERNAME", "neo4j")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(uri, auth=(username, password))

with driver.session(database=database) as session:
    # Check total entities
    result = session.run("MATCH (n) RETURN count(n) as total")
    total = result.single()["total"]
    print(f"Total nodes in graph: {total}")

    # Check entities with vectors
    result = session.run("""
        MATCH (n)
        WHERE n._name_vector IS NOT NULL OR n._desc_vector IS NOT NULL
        RETURN count(n) as total
    """)
    total_with_vectors = result.single()["total"]
    print(f"Nodes with vectors: {total_with_vectors}")

    # Find entities with "cycling" or "temperature" in name
    result = session.run("""
        MATCH (n)
        WHERE toLower(n.name) CONTAINS 'cycling' OR toLower(n.name) CONTAINS 'temperature'
        RETURN n.name as name, n._name_vector IS NOT NULL as has_name_vec, n._desc_vector IS NOT NULL as has_desc_vec
        LIMIT 10
    """)

    print("\nEntities matching 'cycling' or 'temperature':")
    for record in result:
        print(f"  - {record['name']} (name_vec: {record['has_name_vec']}, desc_vec: {record['has_desc_vec']})")

    # Check vector dimensions
    result = session.run("""
        MATCH (n)
        WHERE n._name_vector IS NOT NULL
        RETURN size(n._name_vector) as dim
        LIMIT 1
    """)
    record = result.single()
    if record:
        print(f"\nVector dimension: {record['dim']}")

driver.close()
