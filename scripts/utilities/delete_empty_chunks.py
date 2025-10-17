#!/usr/bin/env python3
"""
Script to identify and delete empty Chunk nodes from Neo4j.

Empty chunks are those with:
- No content or minimal content (e.g., just "Content:")
- Content that is empty string or whitespace only
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()


def delete_empty_chunks(dry_run=True):
    """
    Delete empty Chunk nodes from Neo4j.

    Args:
        dry_run: If True, only count and display empty chunks without deleting
    """
    # Connect to Neo4j
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "financebench")

    if not password:
        print("ERROR: NEO4J_PASSWORD environment variable not set")
        return

    driver = GraphDatabase.driver(uri, auth=(username, password))

    print("=" * 80)
    print("DELETE EMPTY CHUNKS FROM NEO4J")
    print("=" * 80)
    print(f"Database: {database}")
    print(f"Mode: {'DRY RUN (no deletion)' if dry_run else 'DELETION MODE'}")
    print("=" * 80)

    with driver.session(database=database) as session:

        # Step 1: Find and inspect empty chunks
        print("\n[1] Finding empty Chunk nodes...")
        print("-" * 80)

        inspect_query = """
        MATCH (c:Chunk)
        WHERE c.content IS NULL
           OR trim(c.content) = ''
           OR trim(c.content) = 'Content:'
           OR c.content =~ '(?i)^content:?\\s*$'
        OPTIONAL MATCH (c)-[r:SOURCE]->(e:Entity)
        RETURN c.id as chunk_id,
               c.content as content,
               c.chunk_index as chunk_index,
               c.source_file as source_file,
               c.page_number as page_number,
               count(e) as linked_entities
        ORDER BY c.source_file, c.chunk_index
        LIMIT 50
        """

        result = session.run(inspect_query)
        empty_chunks = list(result)

        if not empty_chunks:
            print("✓ No empty chunks found!")
            driver.close()
            return

        print(f"Found {len(empty_chunks)} empty chunks:")
        print()

        for i, chunk in enumerate(empty_chunks[:20], 1):  # Show first 20
            chunk_id = chunk['chunk_id']
            content = chunk['content']
            chunk_index = chunk['chunk_index']
            source_file = chunk['source_file']
            page_number = chunk['page_number']
            linked_entities = chunk['linked_entities']

            print(f"{i}. Chunk ID: {chunk_id}")
            print(f"   Index: {chunk_index}, Page: {page_number}")
            print(f"   Source: {source_file}")
            print(f"   Content: '{content}'")
            print(f"   Linked Entities: {linked_entities}")
            print()

        if len(empty_chunks) > 20:
            print(f"... and {len(empty_chunks) - 20} more")
            print()

        # Step 2: Count total empty chunks
        count_query = """
        MATCH (c:Chunk)
        WHERE c.content IS NULL
           OR trim(c.content) = ''
           OR trim(c.content) = 'Content:'
           OR c.content =~ '(?i)^content:?\\s*$'
        RETURN count(c) as total
        """

        result = session.run(count_query)
        total = result.single()['total']

        print(f"\n[2] Total empty chunks: {total}")
        print("-" * 80)

        if dry_run:
            print("\n⚠️  DRY RUN MODE - No chunks will be deleted")
            print(f"\nTo delete these {total} empty chunks, run:")
            print("  python delete_empty_chunks.py --delete")
            print()
        else:
            # Step 3: Delete empty chunks
            print(f"\n[3] Deleting {total} empty chunks...")
            print("-" * 80)

            # Get confirmation
            confirmation = input(f"\n⚠️  Are you sure you want to DELETE {total} empty chunks? (yes/no): ")

            if confirmation.lower() != 'yes':
                print("Deletion cancelled.")
                driver.close()
                return

            delete_query = """
            MATCH (c:Chunk)
            WHERE c.content IS NULL
               OR trim(c.content) = ''
               OR trim(c.content) = 'Content:'
               OR c.content =~ '(?i)^content:?\\s*$'
            DETACH DELETE c
            RETURN count(c) as deleted
            """

            result = session.run(delete_query)
            deleted_count = result.single()['deleted']

            print(f"\n✓ Successfully deleted {deleted_count} empty chunks")
            print()

            # Step 4: Verify deletion
            verify_query = """
            MATCH (c:Chunk)
            WHERE c.content IS NULL
               OR trim(c.content) = ''
               OR trim(c.content) = 'Content:'
            RETURN count(c) as remaining
            """

            result = session.run(verify_query)
            remaining = result.single()['remaining']

            if remaining == 0:
                print("✓ All empty chunks have been removed")
            else:
                print(f"⚠️  {remaining} empty chunks still remain")

    driver.close()

    print("\n" + "=" * 80)
    print("OPERATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    # Check for --delete flag
    dry_run = '--delete' not in sys.argv and '-d' not in sys.argv

    if dry_run:
        print("\n🔍 Running in DRY RUN mode (inspection only)")
        print("To actually delete chunks, run: python delete_empty_chunks.py --delete\n")

    try:
        delete_empty_chunks(dry_run=dry_run)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
