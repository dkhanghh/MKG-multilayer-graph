"""
Example demonstrating checkpoint/resume functionality for CSV batch processing.

This example shows how the CSV batch processor automatically saves checkpoints
and can resume from where it left off if interrupted.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graphs.pipeline.csv_batch_processor import process_csv_in_batches
from server.core.config import load_config


def example_basic_checkpointing():
    """
    Basic example: Process CSV with automatic checkpointing.

    If the process is interrupted (Ctrl+C, crash, etc.), simply run this
    function again and it will resume from the last completed batch.
    """
    print("=" * 70)
    print("Example 1: Basic CSV Batch Processing with Checkpointing")
    print("=" * 70)

    # Load configuration
    config = load_config()

    # Process CSV in batches
    # Checkpointing is enabled by default
    results = process_csv_in_batches(
        csv_path=".data/data_vn30_first_100.csv",
        config=config,
        batch_size=50,  # Small batches for demonstration
        output_dir="./output/resume_example"
    )

    print(f"\n✅ Processing completed!")
    print(f"   Total batches: {results['execution_summary']['batches_processed']}")
    print(f"   Total rows: {results['execution_summary']['total_rows']}")
    print(f"   Total nodes: {results['execution_summary']['total_nodes']}")
    print(f"   Total edges: {results['execution_summary']['total_edges']}")
    print(f"   Time: {results['execution_summary']['total_execution_time']:.2f}s")

    return results


def example_manual_interrupt():
    """
    Example showing manual interrupt and resume.

    Run this once, then interrupt it (Ctrl+C), then run it again to see resume.
    """
    print("\n" + "=" * 70)
    print("Example 2: Interrupt and Resume Demo")
    print("=" * 70)
    print("TIP: Interrupt this with Ctrl+C after a few batches, then run again!")
    print()

    config = load_config()

    try:
        results = process_csv_in_batches(
            csv_path=".data/data_vn30_first_100.csv",
            config=config,
            batch_size=20,  # Very small batches for easy interruption
            output_dir="./output/interrupt_demo"
        )

        print(f"\n✅ All batches completed!")
        print(f"   Total batches: {results['execution_summary']['batches_processed']}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted!")
        print("   Progress has been saved to checkpoint.")
        print("   Run this script again to resume from where you left off.")
        return None

    return results


def example_check_checkpoint():
    """
    Example showing how to check if a checkpoint exists.
    """
    print("\n" + "=" * 70)
    print("Example 3: Check Checkpoint Status")
    print("=" * 70)

    output_dir = "./output/resume_example"
    checkpoint_file = Path(output_dir) / "batch_checkpoint.json"

    if checkpoint_file.exists():
        import json
        with open(checkpoint_file) as f:
            checkpoint = json.load(f)

        print(f"✅ Checkpoint found!")
        print(f"   Location: {checkpoint_file}")
        print(f"   CSV: {checkpoint['csv_path']}")
        print(f"   Total batches: {checkpoint['total_batches']}")
        print(f"   Completed batches: {checkpoint['completed_batches']}")
        print(f"   Progress: {checkpoint['completed_batches']}/{checkpoint['total_batches']} "
              f"({checkpoint['completed_batches']/checkpoint['total_batches']*100:.1f}%)")

        if checkpoint['errors']:
            print(f"   ⚠️  Errors: {len(checkpoint['errors'])}")
    else:
        print(f"❌ No checkpoint found at {checkpoint_file}")
        print(f"   Either processing hasn't started, or it completed successfully.")


def example_disable_checkpointing():
    """
    Example showing how to disable checkpointing if needed.
    """
    print("\n" + "=" * 70)
    print("Example 4: Processing WITHOUT Checkpointing")
    print("=" * 70)

    config = load_config()

    # Disable checkpointing
    results = process_csv_in_batches(
        csv_path=".data/data_vn30_first_100.csv",
        config=config,
        batch_size=100,
        output_dir="./output/no_checkpoint",
        enable_checkpointing=False  # Disable checkpointing
    )

    print(f"\n✅ Processing completed (no checkpoint saved)")
    print(f"   Total batches: {results['execution_summary']['batches_processed']}")


def example_multiple_csv_files():
    """
    Example showing how to process multiple CSV files with independent checkpoints.
    """
    print("\n" + "=" * 70)
    print("Example 5: Multiple CSV Files with Independent Checkpoints")
    print("=" * 70)

    config = load_config()

    csv_files = [
        (".data/data_vn30_first_100.csv", "./output/csv1"),
        # Add more CSV files here
        # (".data/another_file.csv", "./output/csv2"),
    ]

    for csv_path, output_dir in csv_files:
        if not Path(csv_path).exists():
            print(f"⚠️  Skipping {csv_path} (not found)")
            continue

        print(f"\nProcessing {csv_path} → {output_dir}")

        results = process_csv_in_batches(
            csv_path=csv_path,
            config=config,
            batch_size=50,
            output_dir=output_dir  # Each file gets its own checkpoint
        )

        print(f"   ✅ Completed: {results['execution_summary']['batches_processed']} batches")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("CSV Batch Processing - Checkpoint/Resume Examples")
    print("=" * 70)
    print()
    print("This script demonstrates the checkpoint/resume functionality")
    print("for processing large CSV files in batches.")
    print()

    # Example 1: Basic usage
    example_basic_checkpointing()

    # Example 2: Check checkpoint status
    example_check_checkpoint()

    # Uncomment to try other examples:
    # example_manual_interrupt()
    # example_disable_checkpointing()
    # example_multiple_csv_files()


if __name__ == "__main__":
    main()
