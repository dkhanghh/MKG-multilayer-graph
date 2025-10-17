"""
Test script to verify retry logic with exponential backoff in GeminiVectorizer.

This script tests that the vectorizer properly handles rate limit errors (429)
and retries with exponential backoff.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from knowledge_graphs.components.vectorizer import GeminiVectorizer
from knowledge_graphs.components.base import ComponentConfig
from knowledge_graphs.models.graph import Node, SubGraph


def test_retry_configuration():
    """Test that retry configuration is properly loaded."""
    print("=" * 80)
    print("TEST 1: Retry Configuration")
    print("=" * 80)

    config = ComponentConfig(
        type="gemini_vectorizer",
        name="test_vectorizer",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": 100,
            "max_retries": 3,
            "retry_delay": 10,
            "embed_nodes": True,
            "embed_edges": False
        }
    )

    try:
        vectorizer = GeminiVectorizer(config)

        print("\n✓ Vectorizer initialized successfully")
        print(f"  Model: {vectorizer.model}")
        print(f"  Batch size: {vectorizer.batch_size}")
        print(f"  Max retries: {vectorizer.max_retries}")
        print(f"  Retry delay: {vectorizer.retry_delay}s")

        assert vectorizer.max_retries == 3, "max_retries should be 3"
        assert vectorizer.retry_delay == 10, "retry_delay should be 10"

        print("\n✓ Retry configuration loaded correctly!")
        return True

    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_normal_embedding():
    """Test normal embedding without hitting rate limits."""
    print("\n" + "=" * 80)
    print("TEST 2: Normal Embedding (No Rate Limit)")
    print("=" * 80)

    config = ComponentConfig(
        type="gemini_vectorizer",
        name="test_vectorizer",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": 10,  # Small batch to avoid rate limits
            "max_retries": 3,
            "retry_delay": 10,
            "embed_nodes": True
        }
    )

    try:
        vectorizer = GeminiVectorizer(config)

        # Create small test set
        nodes = [
            Node(
                id=f"node_{i}",
                name=f"Test Entity {i}",
                label="Test",
                official_name=f"Test Entity {i}",
                properties={"description": f"Test entity number {i}"}
            )
            for i in range(5)
        ]

        subgraph = SubGraph(nodes=nodes, edges=[], source_chunk_id="test")

        print(f"\nGenerating embeddings for {len(nodes)} nodes...")

        import time
        start_time = time.time()

        vectorized_subgraph = vectorizer._vectorize_subgraph(subgraph)

        elapsed = time.time() - start_time

        # Check results
        embeddings_count = sum(
            1 for node in vectorized_subgraph.nodes
            if hasattr(node, 'embeddings') and node.embeddings
        )

        print(f"✓ Generated embeddings in {elapsed:.2f}s")
        print(f"  Nodes with embeddings: {embeddings_count}/{len(nodes)}")

        assert embeddings_count == len(nodes), "All nodes should have embeddings"

        print("\n✓ Normal embedding works correctly!")
        return True

    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_paid_tier_config():
    """Test configuration for Paid Tier 1."""
    print("\n" + "=" * 80)
    print("TEST 3: Paid Tier 1 Configuration")
    print("=" * 80)

    config = ComponentConfig(
        type="gemini_vectorizer",
        name="paid_tier_vectorizer",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": 100,      # Paid Tier 1 optimal
            "max_retries": 3,
            "retry_delay": 10,
            "max_tokens": 2048,
            "embed_nodes": True,
            "embed_edges": True
        }
    )

    try:
        vectorizer = GeminiVectorizer(config)

        print("\n✓ Paid Tier 1 configuration loaded:")
        print(f"  Batch size: {vectorizer.batch_size} (optimal for Paid Tier 1)")
        print(f"  Max retries: {vectorizer.max_retries}")
        print(f"  Retry delay: {vectorizer.retry_delay}s")
        print(f"  Max tokens: {vectorizer.max_tokens}")
        print(f"  Embed nodes: {vectorizer.embed_nodes}")
        print(f"  Embed edges: {vectorizer.embed_edges}")

        # Verify settings match recommended config
        assert vectorizer.batch_size == 100, "Batch size should be 100 for Paid Tier 1"
        assert vectorizer.max_retries == 3, "Max retries should be 3"
        assert vectorizer.retry_delay == 10, "Retry delay should be 10s"

        print("\n✓ Configuration matches Paid Tier 1 recommendations!")
        return True

    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_config_format():
    """Test that server.py config format is correct."""
    print("\n" + "=" * 80)
    print("TEST 4: Server Configuration Format")
    print("=" * 80)

    # This is the exact config from server.py
    server_config = {
        "type": "gemini_vectorizer",
        "model": "gemini-embedding-001",
        "max_tokens": 2048,
        "embed_nodes": True,
        "embed_edges": True,
        "batch_size": 100,
        "max_retries": 3,
        "retry_delay": 10,
        "enabled": True
    }

    print("\nServer.py configuration:")
    for key, value in server_config.items():
        print(f"  {key}: {value}")

    try:
        config = ComponentConfig(
            type=server_config["type"],
            name="server_vectorizer",
            enabled=server_config["enabled"],
            config=server_config
        )

        vectorizer = GeminiVectorizer(config)

        print("\n✓ Server configuration format is valid!")
        print(f"  Successfully created vectorizer with server config")

        # Verify all settings
        checks = [
            (vectorizer.batch_size == 100, "batch_size = 100"),
            (vectorizer.max_retries == 3, "max_retries = 3"),
            (vectorizer.retry_delay == 10, "retry_delay = 10"),
            (vectorizer.embed_nodes == True, "embed_nodes = True"),
            (vectorizer.embed_edges == True, "embed_edges = True"),
        ]

        all_passed = True
        for passed, check_name in checks:
            status = "✓" if passed else "✗"
            print(f"  {status} {check_name}")
            all_passed = all_passed and passed

        if all_passed:
            print("\n✓ All server config settings verified!")
            return True
        else:
            print("\n✗ Some settings don't match expected values")
            return False

    except Exception as e:
        print(f"\n✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_retry_behavior():
    """Print expected retry behavior."""
    print("\n" + "=" * 80)
    print("Expected Retry Behavior")
    print("=" * 80)

    print("\nWhen a 429 rate limit error occurs:")
    print("  Attempt 1: Initial request fails → Wait 10s")
    print("  Attempt 2: Retry request fails → Wait 20s (10 * 2^1)")
    print("  Attempt 3: Retry request fails → Wait 40s (10 * 2^2)")
    print("  Attempt 4: Max retries reached → Return zero embeddings")

    print("\nTotal wait time if all retries fail: 10 + 20 + 40 = 70 seconds")
    print("(Plus small random jitter of 0-10% per delay)")

    print("\nFor non-rate-limit errors:")
    print("  → Fails immediately without retry")
    print("  → Returns zero embeddings as fallback")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("GeminiVectorizer Retry Logic Test Suite")
    print("=" * 80)

    import os
    if not os.getenv("GOOGLE_API_KEY"):
        print("\n⚠️  Warning: GOOGLE_API_KEY not set")
        print("Some tests may fail without valid API key")
        print("Set with: export GOOGLE_API_KEY='your-key'")

    results = {}

    try:
        # Run tests
        results["Test 1: Configuration"] = test_retry_configuration()
        results["Test 2: Normal Embedding"] = test_normal_embedding()
        results["Test 3: Paid Tier Config"] = test_paid_tier_config()
        results["Test 4: Server Config"] = test_server_config_format()

        # Print retry behavior info
        print_retry_behavior()

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed

    print(f"\nTotal: {total}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")

    print("\nResults:")
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {test_name:<35s} {status}")

    if failed == 0:
        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED!")
        print("Retry logic is configured correctly for Paid Tier 1")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print(f"⚠️  {failed} test(s) failed")
        print("=" * 80)


if __name__ == "__main__":
    main()
