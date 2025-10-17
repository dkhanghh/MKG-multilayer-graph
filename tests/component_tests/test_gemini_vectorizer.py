"""
Integration test for GeminiVectorizer component.

This test verifies that the Gemini vectorizer works correctly with real API calls
and can generate embeddings for financial entities and relationships.

Prerequisites:
    - Set GOOGLE_API_KEY environment variable
    - Install google-genai: pip install google-genai
"""

import os
import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_prerequisites():
    """Check if all prerequisites are met."""
    print("=" * 80)
    print("Checking Prerequisites")
    print("=" * 80)

    issues = []

    # Check Google API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        issues.append("❌ GOOGLE_API_KEY environment variable not set")
    else:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"✓ GOOGLE_API_KEY: {masked_key}")

    # Check google-genai library
    try:
        from google import genai
        print("✓ google-genai library is installed")
    except ImportError:
        issues.append("❌ google-genai not installed. Run: pip install google-genai")

    # Check project imports
    try:
        from knowledge_graphs.components.vectorizer import GeminiVectorizer
        from knowledge_graphs.components.base import ComponentConfig
        from knowledge_graphs.models.graph import SubGraph, Node, Edge
        from knowledge_graphs.models.pipeline_state import PipelineState, PipelineStateManager
        print("✓ Project imports successful")
    except ImportError as e:
        issues.append(f"❌ Failed to import project modules: {e}")

    if issues:
        print("\n" + "=" * 80)
        print("Issues Found:")
        for issue in issues:
            print(f"  {issue}")
        print("\nPlease fix these issues before running the test.")
        print("=" * 80)
        return False

    print("\n✓ All prerequisites met!")
    return True


def test_basic_embedding_generation():
    """Test 1: Basic embedding generation with simple texts."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Embedding Generation")
    print("=" * 80)

    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)

    # Test texts
    test_texts = [
        "Apple Inc. is a technology company.",
        "Microsoft Corporation produces software.",
        "Revenue increased by 15% in Q4 2022."
    ]

    print(f"\nGenerating embeddings for {len(test_texts)} texts...")
    print("Texts:")
    for i, text in enumerate(test_texts, 1):
        print(f"  {i}. {text}")

    try:
        start_time = time.time()

        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=test_texts,
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY"
            )
        )

        elapsed = time.time() - start_time

        embeddings = [emb.values for emb in result.embeddings]

        print(f"\n✓ Successfully generated embeddings in {elapsed:.2f}s")
        print(f"  Number of embeddings: {len(embeddings)}")
        print(f"  Embedding dimension: {len(embeddings[0])}")
        print(f"  Average time per text: {(elapsed/len(test_texts)*1000):.2f}ms")

        # Show sample values
        print(f"\n  Sample embedding values (first 10 dimensions):")
        print(f"    Text 1: {embeddings[0][:10]}")

        return True

    except Exception as e:
        print(f"\n✗ Failed to generate embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gemini_vectorizer_initialization():
    """Test 2: GeminiVectorizer initialization."""
    print("\n" + "=" * 80)
    print("TEST 2: GeminiVectorizer Initialization")
    print("=" * 80)

    from knowledge_graphs.components.vectorizer import GeminiVectorizer
    from knowledge_graphs.components.base import ComponentConfig

    config = ComponentConfig(
        type="gemini_vectorizer",
        name="test_vectorizer",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": 100,
            "max_tokens": 2048,
            "embed_nodes": True,
            "embed_edges": True,
            "node_text_template": "{name} is a {type}. {description}",
            "edge_text_template": "{source} {relation} {target}"
        }
    )

    print("\nConfiguration:")
    print(f"  Model: {config.config['model']}")
    print(f"  Batch size: {config.config['batch_size']}")
    print(f"  Embed nodes: {config.config['embed_nodes']}")
    print(f"  Embed edges: {config.config['embed_edges']}")

    try:
        vectorizer = GeminiVectorizer(config)

        print("\n✓ GeminiVectorizer initialized successfully")
        print(f"  Component type: {vectorizer.component_type}")
        print(f"  Model: {vectorizer.model}")
        print(f"  Batch size: {vectorizer.batch_size}")
        print(f"  Max tokens: {vectorizer.max_tokens}")

        return vectorizer

    except Exception as e:
        print(f"\n✗ Failed to initialize vectorizer: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_node_embedding():
    """Test 3: Generate embeddings for nodes."""
    print("\n" + "=" * 80)
    print("TEST 3: Node Embedding Generation")
    print("=" * 80)

    from knowledge_graphs.components.vectorizer import GeminiVectorizer
    from knowledge_graphs.components.base import ComponentConfig
    from knowledge_graphs.models.graph import Node, SubGraph

    # Create config
    config = ComponentConfig(
        type="gemini_vectorizer",
        name="test_vectorizer",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": 50,
            "embed_nodes": True,
            "embed_edges": False
        }
    )

    # Create sample financial nodes
    nodes = [
        Node(
            id="apple_inc",
            name="Apple Inc.",
            label="Company",
            official_name="Apple Inc.",
            properties={
                "description": "Technology company that manufactures consumer electronics",
                "sector": "Technology"
            }
        ),
        Node(
            id="revenue_q4_2022",
            name="Q4 2022 Revenue",
            label="Financial_Metric",
            official_name="Revenue Quarter 4 2022",
            properties={
                "description": "Total revenue for the fourth quarter of 2022",
                "value": "5.2 billion USD"
            }
        ),
        Node(
            id="tim_cook",
            name="Tim Cook",
            label="Person",
            official_name="Timothy Cook",
            properties={
                "description": "Chief Executive Officer",
                "role": "CEO"
            }
        )
    ]

    print(f"\nCreated {len(nodes)} sample nodes:")
    for node in nodes:
        print(f"  • {node.name} ({node.label})")

    # Create subgraph
    subgraph = SubGraph(
        nodes=nodes,
        edges=[],
        source_chunk_id="test_chunk"
    )

    try:
        vectorizer = GeminiVectorizer(config)

        print("\nGenerating node embeddings...")
        start_time = time.time()

        vectorized_subgraph = vectorizer._vectorize_subgraph(subgraph)

        elapsed = time.time() - start_time

        print(f"✓ Node embeddings generated in {elapsed:.2f}s")
        print(f"  Average per node: {(elapsed/len(nodes)*1000):.2f}ms")

        # Check embeddings
        print("\nNode embedding details:")
        for node in vectorized_subgraph.nodes:
            has_emb = hasattr(node, 'embeddings') and node.embeddings is not None
            emb_dim = len(node.embeddings) if has_emb else 0
            print(f"  • {node.name:30s} - Embedding: {'Yes' if has_emb else 'No':3s} (dim={emb_dim})")

            if has_emb and emb_dim > 0:
                # Show first 5 values
                print(f"    Sample values: {node.embeddings[:5]}")

        return True

    except Exception as e:
        print(f"\n✗ Failed to generate node embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_embedding():
    """Test 4: Generate embeddings for edges."""
    print("\n" + "=" * 80)
    print("TEST 4: Edge Embedding Generation")
    print("=" * 80)

    from knowledge_graphs.components.vectorizer import GeminiVectorizer
    from knowledge_graphs.components.base import ComponentConfig
    from knowledge_graphs.models.graph import Node, Edge, SubGraph

    # Create config with edge embedding enabled
    config = ComponentConfig(
        type="gemini_vectorizer",
        name="test_vectorizer",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": 50,
            "embed_nodes": True,
            "embed_edges": True  # Enable edge embeddings
        }
    )

    # Create nodes
    nodes = [
        Node(id="apple", name="Apple Inc.", label="Company", official_name="Apple Inc."),
        Node(id="tim_cook", name="Tim Cook", label="Person", official_name="Timothy Cook"),
        Node(id="revenue", name="Q4 Revenue", label="Financial_Metric", official_name="Revenue Q4 2022")
    ]

    # Create edges
    edges = [
        Edge(
            id="edge_1",
            source_id="tim_cook",
            target_id="apple",
            relation_type="is_ceo_of",
            confidence=0.95,
            properties={"description": "CEO relationship"}
        ),
        Edge(
            id="edge_2",
            source_id="apple",
            target_id="revenue",
            relation_type="has_metric",
            confidence=0.90,
            properties={"description": "Financial metric relationship"}
        )
    ]

    print(f"\nCreated {len(nodes)} nodes and {len(edges)} edges:")
    print("Edges:")
    for edge in edges:
        print(f"  • {edge.source_id} --[{edge.relation_type}]--> {edge.target_id}")

    # Create subgraph
    subgraph = SubGraph(
        nodes=nodes,
        edges=edges,
        source_chunk_id="test_chunk"
    )

    try:
        vectorizer = GeminiVectorizer(config)

        print("\nGenerating embeddings for nodes and edges...")
        start_time = time.time()

        vectorized_subgraph = vectorizer._vectorize_subgraph(subgraph)

        elapsed = time.time() - start_time

        print(f"✓ Embeddings generated in {elapsed:.2f}s")

        # Check node embeddings
        nodes_with_emb = sum(1 for n in vectorized_subgraph.nodes
                            if hasattr(n, 'embeddings') and n.embeddings)
        print(f"\n  Nodes with embeddings: {nodes_with_emb}/{len(vectorized_subgraph.nodes)}")

        # Check edge embeddings
        edges_with_emb = sum(1 for e in vectorized_subgraph.edges
                            if e.properties and 'embeddings' in e.properties)
        print(f"  Edges with embeddings: {edges_with_emb}/{len(vectorized_subgraph.edges)}")

        # Show edge embedding details
        if edges_with_emb > 0:
            print("\nEdge embedding details:")
            for edge in vectorized_subgraph.edges:
                if edge.properties and 'embeddings' in edge.properties:
                    emb = edge.properties['embeddings']
                    print(f"  • {edge.relation_type:20s} - dim={len(emb)}")
                    print(f"    Sample values: {emb[:5]}")

        return True

    except Exception as e:
        print(f"\n✗ Failed to generate edge embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pipeline_integration():
    """Test 5: Full pipeline integration."""
    print("\n" + "=" * 80)
    print("TEST 5: Pipeline Integration")
    print("=" * 80)

    from knowledge_graphs.components.vectorizer import GeminiVectorizer
    from knowledge_graphs.components.base import ComponentConfig
    from knowledge_graphs.models.graph import Node, Edge, SubGraph
    from knowledge_graphs.models.pipeline_state import PipelineState, PipelineStateManager

    # Create config
    config = ComponentConfig(
        type="gemini_vectorizer",
        name="pipeline_vectorizer",
        enabled=True,
        config={
            "model": "gemini-embedding-001",
            "batch_size": 100,
            "embed_nodes": True,
            "embed_edges": True
        }
    )

    # Create multiple subgraphs (simulating extraction results)
    subgraphs = []

    # Subgraph 1: Company information
    sg1 = SubGraph(
        nodes=[
            Node(id="company_1", name="Apple Inc.", label="Company",
                 official_name="Apple Inc.",
                 properties={"description": "Technology company"}),
            Node(id="metric_1", name="Total Assets", label="Financial_Metric",
                 official_name="Total Assets 2022",
                 properties={"description": "Total assets as of Dec 31, 2022", "value": "352.8B"})
        ],
        edges=[
            Edge(id="e1", source_id="company_1", target_id="metric_1",
                 relation_type="has_metric", confidence=0.9)
        ],
        source_chunk_id="chunk_1"
    )

    # Subgraph 2: Financial performance
    sg2 = SubGraph(
        nodes=[
            Node(id="company_1", name="Apple Inc.", label="Company",
                 official_name="Apple Inc."),
            Node(id="metric_2", name="Revenue Q4 2022", label="Financial_Metric",
                 official_name="Revenue Quarter 4 2022",
                 properties={"description": "Revenue for Q4 2022", "value": "90.1B"})
        ],
        edges=[
            Edge(id="e2", source_id="company_1", target_id="metric_2",
                 relation_type="reported", confidence=0.95)
        ],
        source_chunk_id="chunk_2"
    )

    subgraphs = [sg1, sg2]

    print(f"\nCreated {len(subgraphs)} subgraphs:")
    for i, sg in enumerate(subgraphs, 1):
        print(f"  Subgraph {i}: {len(sg.nodes)} nodes, {len(sg.edges)} edges")

    # Create pipeline state
    pipeline_state = PipelineStateManager.create_initial_state(
        pipeline_id="test_pipeline",
        input_path="test_data.txt",
        config={}
    )
    pipeline_state["subgraphs"] = subgraphs

    try:
        vectorizer = GeminiVectorizer(config)

        print("\nProcessing pipeline state...")
        start_time = time.time()

        updated_state = vectorizer.process(pipeline_state)

        elapsed = time.time() - start_time

        print(f"✓ Pipeline processed in {elapsed:.2f}s")

        # Check results
        vectorized_subgraphs = updated_state.get("vectorized_subgraphs", [])
        print(f"\nResults:")
        print(f"  Vectorized subgraphs: {len(vectorized_subgraphs)}")

        total_nodes_vectorized = 0
        total_edges_vectorized = 0

        for i, sg in enumerate(vectorized_subgraphs, 1):
            nodes_with_emb = sum(1 for n in sg.nodes if hasattr(n, 'embeddings') and n.embeddings)
            edges_with_emb = sum(1 for e in sg.edges if e.properties and 'embeddings' in e.properties)

            total_nodes_vectorized += nodes_with_emb
            total_edges_vectorized += edges_with_emb

            print(f"  Subgraph {i}: {nodes_with_emb}/{len(sg.nodes)} nodes, {edges_with_emb}/{len(sg.edges)} edges vectorized")

        print(f"\nTotal vectorized:")
        print(f"  Nodes: {total_nodes_vectorized}")
        print(f"  Edges: {total_edges_vectorized}")

        return True

    except Exception as e:
        print(f"\n✗ Failed pipeline integration: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_processing():
    """Test 6: Batch processing efficiency."""
    print("\n" + "=" * 80)
    print("TEST 6: Batch Processing Efficiency")
    print("=" * 80)

    from knowledge_graphs.components.vectorizer import GeminiVectorizer
    from knowledge_graphs.components.base import ComponentConfig
    from knowledge_graphs.models.graph import Node, SubGraph

    # Test different batch sizes
    batch_sizes = [10, 50, 100]
    num_nodes = 50

    print(f"\nTesting with {num_nodes} nodes at different batch sizes...")

    results = {}

    for batch_size in batch_sizes:
        config = ComponentConfig(
            type="gemini_vectorizer",
            name="batch_test",
            enabled=True,
            config={
                "model": "gemini-embedding-001",
                "batch_size": batch_size,
                "embed_nodes": True,
                "embed_edges": False
            }
        )

        # Create nodes
        nodes = [
            Node(
                id=f"node_{i}",
                name=f"Entity {i}",
                label="Test",
                official_name=f"Test Entity {i}",
                properties={"description": f"Test entity number {i}"}
            )
            for i in range(num_nodes)
        ]

        subgraph = SubGraph(nodes=nodes, edges=[], source_chunk_id="test")

        try:
            vectorizer = GeminiVectorizer(config)

            start_time = time.time()
            vectorized_subgraph = vectorizer._vectorize_subgraph(subgraph)
            elapsed = time.time() - start_time

            results[batch_size] = {
                'time': elapsed,
                'avg_per_node': (elapsed / num_nodes) * 1000,
                'success': True
            }

            print(f"\n  Batch size {batch_size:3d}:")
            print(f"    Total time: {elapsed:.2f}s")
            print(f"    Per node: {results[batch_size]['avg_per_node']:.2f}ms")

        except Exception as e:
            print(f"\n  Batch size {batch_size:3d}: ✗ Failed - {e}")
            results[batch_size] = {'success': False, 'error': str(e)}

    # Show comparison
    print("\n" + "-" * 80)
    print("Batch Size Comparison:")
    print("-" * 80)
    print(f"{'Batch Size':<15} {'Total Time':<15} {'Time/Node':<15}")
    print("-" * 80)
    for batch_size in batch_sizes:
        if results[batch_size]['success']:
            print(f"{batch_size:<15} {results[batch_size]['time']:.2f}s{'':<9} {results[batch_size]['avg_per_node']:.2f}ms")

    return True


def print_summary(test_results):
    """Print test summary."""
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    failed_tests = total_tests - passed_tests

    print(f"\nTotal tests: {total_tests}")
    print(f"Passed: {passed_tests} ✓")
    print(f"Failed: {failed_tests} ✗")

    print("\nDetailed Results:")
    for test_name, result in test_results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {test_name:<40s} {status}")

    if failed_tests == 0:
        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED! GeminiVectorizer is working correctly.")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print(f"⚠️  {failed_tests} test(s) failed. Please review the errors above.")
        print("=" * 80)


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("GeminiVectorizer Integration Test Suite")
    print("=" * 80)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Check prerequisites
    if not check_prerequisites():
        return

    # Run tests
    test_results = {}

    try:
        test_results["Test 1: Basic Embedding"] = test_basic_embedding_generation()
        test_results["Test 2: Vectorizer Init"] = test_gemini_vectorizer_initialization() is not None
        test_results["Test 3: Node Embedding"] = test_node_embedding()
        test_results["Test 4: Edge Embedding"] = test_edge_embedding()
        test_results["Test 5: Pipeline Integration"] = test_pipeline_integration()
        test_results["Test 6: Batch Processing"] = test_batch_processing()

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

    # Print summary
    print_summary(test_results)

    print(f"\nCompleted at: {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
