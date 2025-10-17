#!/usr/bin/env python3
"""
Test script for hybrid search with Reciprocal Rank Fusion.

This script demonstrates the new hybrid search functionality that combines:
1. Vector similarity search (semantic matching)
2. Text-based keyword search (lexical matching)
3. Entity graph search (structural matching)

Results are fused using Reciprocal Rank Fusion (RRF) for optimal ranking.
"""

import os
from dotenv import load_dotenv
from chatbot_graphs.rag_graph import get_retriever

# Load environment variables
load_dotenv()

def test_hybrid_search():
    """Test the hybrid search functionality."""

    print("=" * 80)
    print("HYBRID SEARCH TEST WITH RECIPROCAL RANK FUSION")
    print("=" * 80)

    # Initialize retriever
    print("\n[1/3] Initializing Neo4j retriever...")
    retriever = get_retriever()
    print("✓ Retriever initialized successfully")

    # Test queries
    test_queries = [
        "What are the requirements for temperature cycling tests?",
        "Tell me about thermal shock testing procedures",
        "How do reliability tests work?"
    ]

    print(f"\n[2/3] Running hybrid search on {len(test_queries)} test queries...")
    print("-" * 80)

    for i, query in enumerate(test_queries, 1):
        print(f"\n\n{'='*80}")
        print(f"TEST QUERY {i}/{len(test_queries)}")
        print(f"{'='*80}")
        print(f"Query: {query}\n")

        # Run hybrid search
        result = retriever.hybrid_search(
            query=query,
            limit=3,  # Get top 3 results
            enable_vector=True,
            enable_text=True,
            enable_entity=True
        )

        print("\n" + "-" * 80)
        print("HYBRID SEARCH RESULTS:")
        print("-" * 80)
        print(result)
        print("-" * 80)

    print(f"\n\n[3/3] Testing individual strategies...")
    print("-" * 80)

    test_query = test_queries[0]
    print(f"\nQuery: {test_query}\n")

    # Test vector search only
    print("\n[Vector Search Only]")
    vector_result = retriever.hybrid_search(
        query=test_query,
        limit=3,
        enable_vector=True,
        enable_text=False,
        enable_entity=False
    )
    print(f"Results: {len(vector_result.split('**')) - 1} entities found")

    # Test text search only
    print("\n[Text Search Only]")
    text_result = retriever.hybrid_search(
        query=test_query,
        limit=3,
        enable_vector=False,
        enable_text=True,
        enable_entity=False
    )
    print(f"Results: {len(text_result.split('**')) - 1} entities found")

    # Test entity search only
    print("\n[Entity Search Only]")
    entity_result = retriever.hybrid_search(
        query=test_query,
        limit=3,
        enable_vector=False,
        enable_text=False,
        enable_entity=True
    )
    print(f"Results: {len(entity_result.split('**')) - 1} entities found")

    # Close connection
    retriever.close()

    print("\n\n" + "=" * 80)
    print("✓ HYBRID SEARCH TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nKey Benefits of Hybrid Search:")
    print("  • Combines semantic, lexical, and structural matching")
    print("  • RRF fusion creates optimal ranking across strategies")
    print("  • Better recall (finds more relevant results)")
    print("  • Better precision (ranks most relevant results first)")
    print("  • Includes RRF scores and source information for transparency")
    print("\nFor DeepEval evaluation, this should improve:")
    print("  ✓ Contextual Precision (better ranking)")
    print("  ✓ Contextual Recall (finds more relevant contexts)")
    print("  ✓ Contextual Relevancy (better overall relevance)")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_hybrid_search()
    except Exception as e:
        print(f"\n❌ Error during hybrid search test: {e}")
        import traceback
        traceback.print_exc()
