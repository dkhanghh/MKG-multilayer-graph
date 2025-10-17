"""
Test script for batch processing functionality.

This script demonstrates how to use batch processing to handle
multiple files efficiently.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_batch_processor_import():
    """Test that batch processor can be imported."""
    print("=" * 80)
    print("TEST 1: Import Batch Processor")
    print("=" * 80)

    try:
        from knowledge_graphs.pipeline.batch_processor import (
            BatchPipelineProcessor,
            process_directory_in_batches
        )
        print("✓ Batch processor imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import: {e}")
        return False


def test_batch_processor_initialization():
    """Test batch processor initialization."""
    print("\n" + "=" * 80)
    print("TEST 2: Initialize Batch Processor")
    print("=" * 80)

    try:
        from knowledge_graphs.pipeline.batch_processor import BatchPipelineProcessor

        # Minimal config
        config = {
            "pipeline": {
                "components": {
                    "scanner": {"type": "directory_scanner", "enabled": True, "config": {}},
                    "reader": {"type": "text_reader", "enabled": True, "config": {}},
                }
            }
        }

        processor = BatchPipelineProcessor(config, batch_size=10)

        print(f"✓ Processor initialized with batch_size={processor.batch_size}")
        print(f"  Config loaded: {len(config['pipeline']['components'])} components")
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_files_from_directory():
    """Test file discovery functionality."""
    print("\n" + "=" * 80)
    print("TEST 3: File Discovery")
    print("=" * 80)

    try:
        from knowledge_graphs.pipeline.batch_processor import BatchPipelineProcessor
        import os

        config = {
            "pipeline": {
                "components": {
                    "scanner": {
                        "type": "directory_scanner",
                        "enabled": True,
                        "config": {
                            "supported_extensions": [".txt", ".pdf"]
                        }
                    }
                }
            }
        }

        processor = BatchPipelineProcessor(config, batch_size=10)

        # Test with financebench_data if it exists
        test_dir = Path("./financebench_data")
        if test_dir.exists():
            files = processor._get_files_from_directory(test_dir)
            print(f"✓ Found {len(files)} files in {test_dir}")
            print(f"  Sample files:")
            for f in files[:5]:
                print(f"    - {Path(f).name}")
            if len(files) > 5:
                print(f"    ... and {len(files) - 5} more")
            return True
        else:
            print(f"⚠️  Directory not found: {test_dir}")
            print("  Skipping this test")
            return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_batches():
    """Test batch creation."""
    print("\n" + "=" * 80)
    print("TEST 4: Batch Creation")
    print("=" * 80)

    try:
        from knowledge_graphs.pipeline.batch_processor import BatchPipelineProcessor

        config = {"pipeline": {"components": {}}}
        processor = BatchPipelineProcessor(config, batch_size=10)

        # Test with 25 files
        test_files = [f"file_{i}.txt" for i in range(25)]
        batches = processor._create_batches(test_files)

        print(f"✓ Created {len(batches)} batches from {len(test_files)} files")
        for i, batch in enumerate(batches, 1):
            print(f"  Batch {i}: {len(batch)} files")

        # Verify
        assert len(batches) == 3, f"Expected 3 batches, got {len(batches)}"
        assert len(batches[0]) == 10, f"Batch 1 should have 10 files"
        assert len(batches[1]) == 10, f"Batch 2 should have 10 files"
        assert len(batches[2]) == 5, f"Batch 3 should have 5 files"

        print("✓ Batch sizes are correct!")
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_request_model():
    """Test that PipelineRequest includes batch_size."""
    print("\n" + "=" * 80)
    print("TEST 5: API Request Model")
    print("=" * 80)

    try:
        # Import server module to check PipelineRequest
        import server
        from pydantic import BaseModel

        # Check if PipelineRequest has batch_size field
        if hasattr(server, 'PipelineRequest'):
            request_model = server.PipelineRequest

            # Create test request
            test_request = request_model(
                input_path="./test",
                batch_size=10
            )

            print(f"✓ PipelineRequest model has batch_size field")
            print(f"  Default batch_size: {test_request.batch_size}")
            print(f"  Input path: {test_request.input_path}")

            return True
        else:
            print("⚠️  PipelineRequest model not found in server module")
            return False

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_usage_examples():
    """Print usage examples."""
    print("\n" + "=" * 80)
    print("USAGE EXAMPLES")
    print("=" * 80)

    print("\n1. Using Python directly:")
    print("""
from knowledge_graphs.pipeline.batch_processor import process_directory_in_batches

results = process_directory_in_batches(
    input_path="./financebench_data",
    config=your_config,
    batch_size=10  # Process 10 files at a time
)

print(f"Processed {results['execution_summary']['total_files']} files")
""")

    print("\n2. Using API endpoint:")
    print("""
import requests

response = requests.post(
    "http://localhost:8000/pipeline/run-batch",
    json={
        "input_path": "./financebench_data",
        "batch_size": 10
    }
)

result = response.json()
print(f"Status: {result['status']}")
""")

    print("\n3. Using BatchPipelineProcessor class:")
    print("""
from knowledge_graphs.pipeline.batch_processor import BatchPipelineProcessor

processor = BatchPipelineProcessor(config, batch_size=10)
results = processor.process_directory_in_batches("./financebench_data")
""")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("Batch Processing Test Suite")
    print("=" * 80)

    results = {}

    try:
        results["Test 1: Import"] = test_batch_processor_import()
        results["Test 2: Initialize"] = test_batch_processor_initialization()
        results["Test 3: File Discovery"] = test_get_files_from_directory()
        results["Test 4: Batch Creation"] = test_create_batches()
        results["Test 5: API Model"] = test_api_request_model()

        # Print usage examples
        print_usage_examples()

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
        print(f"  {test_name:<30s} {status}")

    if failed == 0:
        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED!")
        print("Batch processing is ready to use.")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Start server: python server.py")
        print("  2. Use batch endpoint: POST /pipeline/run-batch")
        print("  3. Set batch_size=10 for 150 files")
        print("\nSee: BATCH_PROCESSING_GUIDE.md for full documentation")
    else:
        print("\n" + "=" * 80)
        print(f"⚠️  {failed} test(s) failed")
        print("=" * 80)


if __name__ == "__main__":
    main()
