"""
Test to find the actual rate limit threshold for Gemini API.

This script tests different batch sizes and request rates to determine
when the API returns 429 rate limit errors.

WARNING: This test will intentionally try to hit rate limits!
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from knowledge_graphs.components.vectorizer import GeminiVectorizer
from knowledge_graphs.components.base import ComponentConfig
from knowledge_graphs.models.graph import Node, SubGraph


def create_test_nodes(count: int) -> list:
    """Create test nodes for embedding."""
    return [
        Node(
            id=f"test_node_{i}",
            name=f"Test Entity {i}",
            label="TestEntity",
            official_name=f"Test Entity {i}",
            properties={
                "description": f"This is test entity number {i} for rate limit testing"
            }
        )
        for i in range(count)
    ]


def test_batch_size(batch_size: int, num_items: int, test_duration: int = 60):
    """
    Test a specific batch size to see if it hits rate limits.

    Args:
        batch_size: Size of each batch
        num_items: Total number of items to process
        test_duration: Max duration in seconds

    Returns:
        Dictionary with test results
    """
    print(f"\n{'='*80}")
    print(f"Testing batch_size={batch_size} with {num_items} items")
    print(f"{'='*80}")

    config = ComponentConfig(
        type="gemini_vectorizer",
        name="rate_limit_tester",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": batch_size,
            "max_retries": 1,  # Only retry once to detect rate limits faster
            "retry_delay": 5,
            "embed_nodes": True,
            "embed_edges": False
        }
    )

    try:
        vectorizer = GeminiVectorizer(config)
        nodes = create_test_nodes(num_items)
        subgraph = SubGraph(nodes=nodes, edges=[], source_chunk_id="rate_test")

        # Track metrics
        start_time = time.time()
        requests_made = 0
        rate_limit_hit = False
        rate_limit_time = None
        items_processed = 0

        print(f"\nProcessing {num_items} items...")
        print(f"Expected API requests: {num_items // batch_size + (1 if num_items % batch_size else 0)}")

        # Process with monitoring
        try:
            vectorized = vectorizer._vectorize_subgraph(subgraph)

            # Check if embeddings were generated
            items_processed = sum(
                1 for node in vectorized.nodes
                if hasattr(node, 'embeddings') and node.embeddings
            )

            elapsed = time.time() - start_time
            requests_made = (num_items + batch_size - 1) // batch_size  # Ceiling division

            print(f"✓ Completed in {elapsed:.2f}s")
            print(f"  Items processed: {items_processed}/{num_items}")
            print(f"  Estimated requests: {requests_made}")
            print(f"  Rate per minute: {(requests_made / elapsed) * 60:.1f} RPM")

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)

            if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                rate_limit_hit = True
                rate_limit_time = elapsed
                print(f"✗ Rate limit hit after {elapsed:.2f}s")
                print(f"  Error: {error_msg[:100]}")
            else:
                print(f"✗ Other error: {error_msg[:100]}")

        return {
            "batch_size": batch_size,
            "num_items": num_items,
            "requests_made": requests_made,
            "rate_limit_hit": rate_limit_hit,
            "rate_limit_time": rate_limit_time,
            "items_processed": items_processed,
            "elapsed_time": time.time() - start_time,
            "success": not rate_limit_hit and items_processed == num_items
        }

    except Exception as e:
        print(f"✗ Setup error: {e}")
        return {
            "batch_size": batch_size,
            "error": str(e),
            "success": False
        }


def test_progressive_load():
    """Test with progressively increasing load to find the breaking point."""
    print("\n" + "="*80)
    print("PROGRESSIVE LOAD TEST")
    print("Testing with increasing number of requests to find rate limit")
    print("="*80)

    results = []

    # Test scenarios - increasing load
    scenarios = [
        # (batch_size, num_items, description)
        (100, 500, "Conservative - 5 requests"),
        (100, 1000, "Moderate - 10 requests"),
        (100, 2000, "Normal - 20 requests"),
        (100, 5000, "Heavy - 50 requests"),
        (100, 10000, "Very Heavy - 100 requests"),
    ]

    for batch_size, num_items, description in scenarios:
        print(f"\n{description}")
        result = test_batch_size(batch_size, num_items)
        results.append(result)

        if result.get("rate_limit_hit"):
            print(f"\n⚠️  Rate limit found at {num_items} items!")
            break

        # Wait between tests to avoid accumulating rate limit
        print("\nWaiting 10 seconds before next test...")
        time.sleep(10)

    return results


def test_rapid_fire():
    """Test rapid consecutive requests to hit rate limits quickly."""
    print("\n" + "="*80)
    print("RAPID FIRE TEST")
    print("Making many small batches quickly to test RPM limits")
    print("="*80)

    config = ComponentConfig(
        type="gemini_vectorizer",
        name="rapid_fire_tester",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": 10,  # Small batches = more requests
            "max_retries": 0,  # No retries to see immediate failures
            "embed_nodes": True
        }
    )

    try:
        vectorizer = GeminiVectorizer(config)

        requests_made = 0
        rate_limit_hit = False
        start_time = time.time()

        print("\nMaking rapid requests until rate limit hit...")
        print("Press Ctrl+C to stop")

        # Keep making requests until rate limit
        for i in range(200):  # Max 200 attempts
            try:
                # Create small batch
                nodes = create_test_nodes(10)
                subgraph = SubGraph(nodes=nodes, edges=[], source_chunk_id=f"rapid_{i}")

                # Try to process
                vectorized = vectorizer._vectorize_subgraph(subgraph)
                requests_made += 1

                elapsed = time.time() - start_time
                rpm = (requests_made / elapsed) * 60

                if i % 10 == 0:
                    print(f"  Request {requests_made:3d} - {elapsed:5.1f}s elapsed - {rpm:6.1f} RPM")

            except Exception as e:
                elapsed = time.time() - start_time
                rpm = (requests_made / elapsed) * 60

                if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                    rate_limit_hit = True
                    print(f"\n✗ Rate limit hit!")
                    print(f"  Requests before limit: {requests_made}")
                    print(f"  Time elapsed: {elapsed:.2f}s")
                    print(f"  Rate: {rpm:.1f} RPM")
                    break

        if not rate_limit_hit:
            elapsed = time.time() - start_time
            rpm = (requests_made / elapsed) * 60
            print(f"\n✓ No rate limit hit after {requests_made} requests")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Rate: {rpm:.1f} RPM")

        return {
            "requests_made": requests_made,
            "rate_limit_hit": rate_limit_hit,
            "elapsed_time": time.time() - start_time,
            "rpm_achieved": (requests_made / (time.time() - start_time)) * 60
        }

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        rpm = (requests_made / elapsed) * 60
        print(f"\n\n⚠️  Test interrupted by user")
        print(f"  Requests made: {requests_made}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Rate: {rpm:.1f} RPM")
        return {
            "requests_made": requests_made,
            "interrupted": True
        }


def test_sustained_load():
    """Test sustained load over 60 seconds."""
    print("\n" + "="*80)
    print("SUSTAINED LOAD TEST (60 seconds)")
    print("Testing continuous processing over one minute")
    print("="*80)

    config = ComponentConfig(
        type="gemini_vectorizer",
        name="sustained_tester",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": 50,  # Medium batches
            "max_retries": 0,
            "embed_nodes": True
        }
    )

    try:
        vectorizer = GeminiVectorizer(config)

        requests_made = 0
        items_processed = 0
        rate_limit_hit = False
        start_time = time.time()
        test_duration = 60  # 60 seconds

        print(f"\nProcessing for {test_duration} seconds...")

        batch_count = 0
        while time.time() - start_time < test_duration:
            try:
                # Create batch
                nodes = create_test_nodes(50)
                subgraph = SubGraph(nodes=nodes, edges=[], source_chunk_id=f"sustained_{batch_count}")

                # Process
                vectorized = vectorizer._vectorize_subgraph(subgraph)
                requests_made += 1
                items_processed += 50
                batch_count += 1

                elapsed = time.time() - start_time
                rpm = (requests_made / elapsed) * 60

                if batch_count % 5 == 0:
                    print(f"  {elapsed:5.1f}s: {requests_made:3d} requests, {items_processed:5d} items, {rpm:6.1f} RPM")

            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    rate_limit_hit = True
                    elapsed = time.time() - start_time
                    print(f"\n✗ Rate limit hit at {elapsed:.1f}s")
                    print(f"  Requests made: {requests_made}")
                    print(f"  Items processed: {items_processed}")
                    break

        elapsed = time.time() - start_time
        rpm = (requests_made / elapsed) * 60

        print(f"\nTest complete:")
        print(f"  Duration: {elapsed:.2f}s")
        print(f"  Requests: {requests_made}")
        print(f"  Items: {items_processed}")
        print(f"  Average RPM: {rpm:.1f}")
        print(f"  Rate limit hit: {'Yes' if rate_limit_hit else 'No'}")

        return {
            "duration": elapsed,
            "requests_made": requests_made,
            "items_processed": items_processed,
            "rpm_achieved": rpm,
            "rate_limit_hit": rate_limit_hit
        }

    except Exception as e:
        print(f"✗ Error: {e}")
        return {"error": str(e)}


def analyze_results(results):
    """Analyze and summarize test results."""
    print("\n" + "="*80)
    print("RESULTS ANALYSIS")
    print("="*80)

    # Find where rate limits were hit
    rate_limit_results = [r for r in results if r.get("rate_limit_hit")]
    successful_results = [r for r in results if r.get("success")]

    if rate_limit_results:
        print("\n⚠️  Rate Limits Detected:")
        for r in rate_limit_results:
            batch_size = r.get("batch_size", "N/A")
            num_items = r.get("num_items", "N/A")
            requests = r.get("requests_made", "N/A")
            print(f"  • batch_size={batch_size}, items={num_items}, requests={requests}")
    else:
        print("\n✓ No rate limits hit in any test!")

    if successful_results:
        print("\n✓ Successful Configurations:")
        for r in successful_results:
            batch_size = r.get("batch_size", "N/A")
            num_items = r.get("num_items", "N/A")
            requests = r.get("requests_made", "N/A")
            elapsed = r.get("elapsed_time", 0)
            rpm = (requests / elapsed * 60) if elapsed > 0 else 0
            print(f"  • batch_size={batch_size}, items={num_items}, requests={requests}, RPM={rpm:.1f}")

    # Calculate safe threshold
    if successful_results and rate_limit_results:
        max_safe_requests = max(r.get("requests_made", 0) for r in successful_results)
        min_fail_requests = min(r.get("requests_made", 999999) for r in rate_limit_results)
        print(f"\n📊 Estimated Safe Threshold:")
        print(f"  • Maximum safe requests: {max_safe_requests}")
        print(f"  • Failed at: {min_fail_requests} requests")
        print(f"  • Recommended batch_size for 2,700 items: {2700 // max_safe_requests + 1}")


def main():
    """Run rate limit tests."""
    print("\n" + "="*80)
    print("Gemini API Rate Limit Threshold Test")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("\n❌ Error: GOOGLE_API_KEY not set")
        print("Set with: export GOOGLE_API_KEY='your-key'")
        return

    print("\n⚠️  WARNING: This test will intentionally try to hit rate limits!")
    print("This may temporarily exhaust your API quota.")

    # Ask for confirmation
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response != "yes":
        print("Test cancelled.")
        return

    all_results = []

    try:
        # Choose test type
        print("\nSelect test type:")
        print("1. Progressive Load Test (recommended)")
        print("2. Rapid Fire Test (aggressive)")
        print("3. Sustained Load Test (60 seconds)")
        print("4. All tests")

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "1":
            results = test_progressive_load()
            all_results.extend(results)
        elif choice == "2":
            result = test_rapid_fire()
            all_results.append(result)
        elif choice == "3":
            result = test_sustained_load()
            all_results.append(result)
        elif choice == "4":
            print("\nRunning all tests...")
            results = test_progressive_load()
            all_results.extend(results)
            time.sleep(30)  # Wait between test types
            result = test_rapid_fire()
            all_results.append(result)
            time.sleep(30)
            result = test_sustained_load()
            all_results.append(result)
        else:
            print("Invalid choice")
            return

        # Analyze results
        if all_results:
            analyze_results(all_results)

        # Save results
        results_file = "rate_limit_test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": all_results
            }, f, indent=2)

        print(f"\n✓ Results saved to: {results_file}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("Test completed")
    print("="*80)


if __name__ == "__main__":
    main()
