#!/usr/bin/env python3
"""
Inspect Neo4j database schema to understand the actual structure.

This script will analyze:
- Node labels and their properties
- Relationship types and their properties
- Which nodes/relationships have embeddings
- Sample data structure
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv(override=True)


def inspect_schema():
    """Inspect the Neo4j database schema."""

    # Connect to Neo4j
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not password:
        print("ERROR: NEO4J_PASSWORD environment variable not set")
        return

    driver = GraphDatabase.driver(uri, auth=(username, password))

    print("=" * 80)
    print("NEO4J DATABASE SCHEMA INSPECTION")
    print("=" * 80)
    print(f"Database: {database}")
    print(f"URI: {uri}")
    print("=" * 80)

    with driver.session(database=database) as session:

        # 1. Get all node labels
        print("\n[1] NODE LABELS")
        print("-" * 80)
        result = session.run("CALL db.labels()")
        labels = [record[0] for record in result]
        print(f"Found {len(labels)} node labels:")
        for label in labels:
            print(f"  • {label}")

        # 2. Get properties for each label
        print("\n[2] NODE PROPERTIES BY LABEL")
        print("-" * 80)
        for label in labels:
            # Get sample node to inspect properties
            result = session.run(f"MATCH (n:{label}) RETURN n LIMIT 1")
            record = result.single()

            if record:
                node = record["n"]
                props = dict(node.items())

                print(f"\n  Label: {label}")
                print(f"  Properties ({len(props)}):")

                for key, value in props.items():
                    value_type = type(value).__name__

                    # Check if it's an embedding (list of numbers)
                    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], (int, float)):
                        value_info = f"list[{len(value)} floats] (EMBEDDING)"
                    elif isinstance(value, str) and len(value) > 50:
                        value_info = f"string ({len(value)} chars)"
                    else:
                        value_info = f"{value_type}: {str(value)[:50]}"

                    print(f"    - {key}: {value_info}")

                # Count total nodes with this label
                count_result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                count = count_result.single()["count"]
                print(f"  Total nodes: {count}")

        # 3. Get all relationship types
        print("\n\n[3] RELATIONSHIP TYPES")
        print("-" * 80)
        result = session.run("CALL db.relationshipTypes()")
        rel_types = [record[0] for record in result]
        print(f"Found {len(rel_types)} relationship types:")
        for rel_type in rel_types:
            print(f"  • {rel_type}")

        # 4. Get properties for each relationship type
        print("\n[4] RELATIONSHIP PROPERTIES BY TYPE")
        print("-" * 80)
        for rel_type in rel_types:
            # Get sample relationship
            result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN r LIMIT 1")
            record = result.single()

            if record:
                rel = record["r"]
                props = dict(rel.items())

                print(f"\n  Type: {rel_type}")

                if props:
                    print(f"  Properties ({len(props)}):")
                    for key, value in props.items():
                        value_type = type(value).__name__

                        # Check if it's an embedding
                        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], (int, float)):
                            value_info = f"list[{len(value)} floats] (EMBEDDING)"
                        elif isinstance(value, str) and len(value) > 50:
                            value_info = f"string ({len(value)} chars)"
                        else:
                            value_info = f"{value_type}: {str(value)[:50]}"

                        print(f"    - {key}: {value_info}")
                else:
                    print("  Properties: None")

                # Count total relationships
                count_result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                count = count_result.single()["count"]
                print(f"  Total relationships: {count}")

        # 5. Analyze nodes with embeddings
        print("\n\n[5] NODES WITH EMBEDDINGS")
        print("-" * 80)
        for label in labels:
            result = session.run(f"""
                MATCH (n:{label})
                WHERE n.embeddings IS NOT NULL
                RETURN count(n) as count, size(n.embeddings) as dim
                LIMIT 1
            """)
            record = result.single()

            if record and record["count"] > 0:
                print(f"  • {label}: {record['count']} nodes with {record['dim']}-dimensional embeddings")

        # 6. Analyze relationships with embeddings
        print("\n[6] RELATIONSHIPS WITH EMBEDDINGS")
        print("-" * 80)
        for rel_type in rel_types:
            result = session.run(f"""
                MATCH ()-[r:{rel_type}]->()
                WHERE r.embeddings IS NOT NULL
                RETURN count(r) as count, size(r.embeddings) as dim
                LIMIT 1
            """)
            record = result.single()

            if record and record["count"] > 0:
                print(f"  • {rel_type}: {record['count']} relationships with {record['dim']}-dimensional embeddings")

        # 7. Analyze Chunk nodes specifically
        print("\n\n[7] CHUNK NODE ANALYSIS")
        print("-" * 80)
        if "Chunk" in labels:
            # Get sample chunk
            result = session.run("""
                MATCH (c:Chunk)
                OPTIONAL MATCH (c)-[r]->(target)
                RETURN c, type(r) as rel_type, labels(target) as target_labels
                LIMIT 1
            """)
            record = result.single()

            if record:
                chunk = record["c"]
                rel_type = record["rel_type"]
                target_labels = record["target_labels"]

                print("  Sample Chunk node:")
                print(f"    Properties: {list(chunk.keys())}")
                if rel_type:
                    print(f"    Connected via: {rel_type} -> {target_labels}")

                # Get total chunks
                count_result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
                count = count_result.single()["count"]
                print(f"  Total Chunks: {count}")
        else:
            print("  No Chunk label found")

        # 8. Analyze Entity nodes specifically
        print("\n[8] ENTITY NODE ANALYSIS")
        print("-" * 80)
        if "Entity" in labels:
            result = session.run("""
                MATCH (e:Entity)
                RETURN
                    count(e) as total,
                    count(e.official_name) as has_official_name,
                    count(e.taxonomy_name) as has_taxonomy_name,
                    count(e.embeddings) as has_embeddings,
                    count(e.description) as has_description
            """)
            record = result.single()

            if record:
                print(f"  Total Entity nodes: {record['total']}")
                print(f"  With official_name: {record['has_official_name']} ({record['has_official_name']/record['total']*100:.1f}%)")
                print(f"  With taxonomy_name: {record['has_taxonomy_name']} ({record['has_taxonomy_name']/record['total']*100:.1f}%)")
                print(f"  With embeddings: {record['has_embeddings']} ({record['has_embeddings']/record['total']*100:.1f}%)")
                print(f"  With description: {record['has_description']} ({record['has_description']/record['total']*100:.1f}%)")
        else:
            print("  No Entity label found")

        # 9. Sample graph structure
        print("\n\n[9] SAMPLE GRAPH STRUCTURE")
        print("-" * 80)
        result = session.run("""
            MATCH (e:Entity)-[r]->(target)
            RETURN e.name as entity_name,
                   type(r) as relationship,
                   labels(target) as target_labels,
                   target.name as target_name
            LIMIT 5
        """)

        print("  Sample connections:")
        for record in result:
            print(f"    {record['entity_name']} -[{record['relationship']}]-> {record['target_labels']} ({record['target_name']})")

    driver.close()

    print("\n" + "=" * 80)
    print("SCHEMA INSPECTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    try:
        inspect_schema()
    except Exception as e:
        print(f"\n❌ Error inspecting schema: {e}")
        import traceback
        traceback.print_exc()
