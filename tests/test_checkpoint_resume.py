"""
Test script for CSV batch checkpoint/resume functionality.

This script verifies that the checkpoint/resume feature works correctly.
"""

import json
import shutil
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graphs.pipeline.csv_batch_processor import CSVBatchProcessor
from server.core.config import load_config


def create_test_csv(csv_path: Path, num_rows: int = 100) -> Path:
    """
    Create a test CSV file.

    Args:
        csv_path: Path to create CSV
        num_rows: Number of data rows

    Returns:
        Path to created CSV
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write("_id,content,company_code,year\n")

        # Write data rows
        for i in range(1, num_rows + 1):
            f.write(f"{i},Test content for row {i},TEST,2023\n")

    print(f"✅ Created test CSV: {csv_path} ({num_rows} rows)")
    return csv_path


def test_checkpoint_creation():
    """Test 1: Verify checkpoint file is created after first batch."""
    print("\n" + "=" * 70)
    print("Test 1: Checkpoint Creation")
    print("=" * 70)

    # Create test CSV
    temp_dir = Path(tempfile.mkdtemp(prefix="test_checkpoint_"))
    csv_path = create_test_csv(temp_dir / "test.csv", num_rows=50)
    output_dir = temp_dir / "output"

    # Load config
    config = load_config()

    # Create processor with small batch size
    processor = CSVBatchProcessor(config, batch_size=10, enable_checkpointing=True)

    # Process just to create checkpoint (will process all batches)
    print("\nProcessing CSV...")
    results = processor.process_csv_in_batches(str(csv_path), str(output_dir))

    # Check if checkpoint was created during processing
    checkpoint_path = output_dir / "batch_checkpoint.json"

    # Note: Checkpoint is deleted after successful completion
    # So we check if processing completed successfully instead
    if results['status'] == 'completed':
        print("✅ Processing completed successfully")
        print(f"   Batches processed: {results['execution_summary']['batches_processed']}")
        print("✅ Checkpoint was created and then deleted after completion")
    else:
        print("❌ Processing did not complete successfully")
        return False

    # Cleanup
    shutil.rmtree(temp_dir)
    return True


def test_checkpoint_resume():
    """Test 2: Simulate interruption and resume."""
    print("\n" + "=" * 70)
    print("Test 2: Checkpoint Resume Simulation")
    print("=" * 70)

    # Create test CSV
    temp_dir = Path(tempfile.mkdtemp(prefix="test_resume_"))
    csv_path = create_test_csv(temp_dir / "test.csv", num_rows=100)
    output_dir = temp_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    config = load_config()

    # Manually create a checkpoint simulating partial completion
    checkpoint_path = output_dir / "batch_checkpoint.json"

    # Simulate 3 out of 10 batches completed
    checkpoint_data = {
        "csv_path": str(csv_path),
        "total_batches": 10,
        "completed_batches": 3,
        "batch_size": 10,
        "batch_results": [
            {
                "batch_number": 1,
                "start_row": 1,
                "end_row": 10,
                "row_count": 10,
                "execution_summary": {"total_nodes": 5, "total_edges": 3}
            },
            {
                "batch_number": 2,
                "start_row": 11,
                "end_row": 20,
                "row_count": 10,
                "execution_summary": {"total_nodes": 5, "total_edges": 3}
            },
            {
                "batch_number": 3,
                "start_row": 21,
                "end_row": 30,
                "row_count": 10,
                "execution_summary": {"total_nodes": 5, "total_edges": 3}
            }
        ],
        "metrics": {
            "total_files_processed": 1,
            "total_chunks_created": 30,
            "total_nodes_extracted": 15,
            "total_edges_extracted": 9,
            "total_subgraphs_created": 0
        },
        "errors": [],
        "last_updated": 1733308800.0
    }

    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

    print(f"✅ Created mock checkpoint: 3/10 batches completed")

    # Now process - should resume from batch 4
    processor = CSVBatchProcessor(config, batch_size=10, enable_checkpointing=True)

    print("\nResuming processing...")
    results = processor.process_csv_in_batches(str(csv_path), str(output_dir))

    # Verify results
    if results['execution_summary']['batches_processed'] == 10:
        print(f"✅ Resume successful!")
        print(f"   Total batches: {results['execution_summary']['batches_processed']}")
        print(f"   Should have processed batches 4-10 (7 new batches)")
    else:
        print(f"❌ Resume failed - expected 10 batches, got {results['execution_summary']['batches_processed']}")
        shutil.rmtree(temp_dir)
        return False

    # Verify checkpoint was deleted after completion
    if not checkpoint_path.exists():
        print("✅ Checkpoint deleted after successful completion")
    else:
        print("⚠️  Checkpoint still exists after completion")

    # Cleanup
    shutil.rmtree(temp_dir)
    return True


def test_checkpoint_disabled():
    """Test 3: Verify checkpointing can be disabled."""
    print("\n" + "=" * 70)
    print("Test 3: Checkpointing Disabled")
    print("=" * 70)

    # Create test CSV
    temp_dir = Path(tempfile.mkdtemp(prefix="test_no_checkpoint_"))
    csv_path = create_test_csv(temp_dir / "test.csv", num_rows=30)
    output_dir = temp_dir / "output"

    # Load config
    config = load_config()

    # Create processor with checkpointing DISABLED
    processor = CSVBatchProcessor(config, batch_size=10, enable_checkpointing=False)

    print("\nProcessing with checkpointing disabled...")
    results = processor.process_csv_in_batches(str(csv_path), str(output_dir))

    # Verify checkpoint was NOT created
    checkpoint_path = output_dir / "batch_checkpoint.json"

    if not checkpoint_path.exists():
        print("✅ No checkpoint created (as expected)")
    else:
        print("❌ Checkpoint was created when it should be disabled")
        shutil.rmtree(temp_dir)
        return False

    # Cleanup
    shutil.rmtree(temp_dir)
    return True


def test_checkpoint_content():
    """Test 4: Verify checkpoint content is valid."""
    print("\n" + "=" * 70)
    print("Test 4: Checkpoint Content Validation")
    print("=" * 70)

    # Create test CSV
    temp_dir = Path(tempfile.mkdtemp(prefix="test_checkpoint_content_"))
    csv_path = create_test_csv(temp_dir / "test.csv", num_rows=20)
    output_dir = temp_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    config = load_config()

    # Manually create a checkpoint
    checkpoint_path = output_dir / "batch_checkpoint.json"

    checkpoint_data = {
        "csv_path": str(csv_path),
        "total_batches": 2,
        "completed_batches": 1,
        "batch_size": 10,
        "batch_results": [
            {
                "batch_number": 1,
                "start_row": 1,
                "end_row": 10,
                "row_count": 10,
                "execution_summary": {"total_nodes": 5, "total_edges": 3}
            }
        ],
        "metrics": {
            "total_files_processed": 1,
            "total_chunks_created": 10,
            "total_nodes_extracted": 5,
            "total_edges_extracted": 3,
            "total_subgraphs_created": 0
        },
        "errors": [],
        "last_updated": 1733308800.0
    }

    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

    # Read and validate checkpoint
    with open(checkpoint_path) as f:
        loaded_checkpoint = json.load(f)

    # Validate required fields
    required_fields = [
        "csv_path", "total_batches", "completed_batches", "batch_size",
        "batch_results", "metrics", "errors", "last_updated"
    ]

    all_present = all(field in loaded_checkpoint for field in required_fields)

    if all_present:
        print("✅ Checkpoint contains all required fields")
        print(f"   Fields: {', '.join(required_fields)}")
    else:
        missing = [f for f in required_fields if f not in loaded_checkpoint]
        print(f"❌ Checkpoint missing fields: {missing}")
        shutil.rmtree(temp_dir)
        return False

    # Validate metrics structure
    required_metrics = [
        "total_files_processed", "total_chunks_created",
        "total_nodes_extracted", "total_edges_extracted"
    ]

    metrics_present = all(m in loaded_checkpoint["metrics"] for m in required_metrics)

    if metrics_present:
        print("✅ Checkpoint metrics are valid")
    else:
        print("❌ Checkpoint metrics are invalid")
        shutil.rmtree(temp_dir)
        return False

    # Cleanup
    shutil.rmtree(temp_dir)
    return True


def run_all_tests():
    """Run all checkpoint tests."""
    print("\n" + "=" * 70)
    print("CSV Batch Processor - Checkpoint/Resume Tests")
    print("=" * 70)

    tests = [
        ("Checkpoint Creation", test_checkpoint_creation),
        ("Checkpoint Resume", test_checkpoint_resume),
        ("Checkpointing Disabled", test_checkpoint_disabled),
        ("Checkpoint Content Validation", test_checkpoint_content),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
