"""
Test script for Scanner component with financebench_data directory.

This script demonstrates how to use the DirectoryScanner to scan
files in the financebench_data directory.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from knowledge_graphs.components.scanner import DirectoryScanner
from knowledge_graphs.components.base import ComponentConfig
from knowledge_graphs.models.pipeline_state import PipelineState, PipelineStateManager


def test_basic_scan():
    """Test basic directory scanning."""
    print("=" * 80)
    print("TEST 1: Basic Directory Scan")
    print("=" * 80)

    # Configuration for the scanner
    config = ComponentConfig(
        type="directory_scanner",
        name="financebench_scanner",
        enabled=True,
        config={
            "recursive": False,  # Don't scan subdirectories
            "file_patterns": ["*.txt"],  # Only .txt files
            "supported_extensions": [".txt"],
            "max_files": None  # No limit
        }
    )

    # Create scanner instance
    scanner = DirectoryScanner(config)

    # Create initial pipeline state
    financebench_path = str(project_root / "financebench_data")
    initial_state = PipelineStateManager.create_initial_state(
        pipeline_id="test_scanner_001",
        input_path=financebench_path,
        config={}
    )

    # Run scanner
    print(f"\nScanning directory: {financebench_path}")
    print(f"Configuration: {config.config}")
    print("\nExecuting scanner...")

    result_state = scanner.process(initial_state)

    # Display results
    file_paths = result_state.get("file_paths", [])
    print(f"\n✓ Scan completed successfully!")
    print(f"Total files found: {len(file_paths)}")

    # Show first 10 files
    print("\nFirst 10 files:")
    for i, file_path in enumerate(file_paths[:10], 1):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        print(f"  {i:3d}. {filename:50s} ({file_size:,} bytes)")

    if len(file_paths) > 10:
        print(f"  ... and {len(file_paths) - 10} more files")

    return result_state


def test_with_limit():
    """Test scanning with max_files limit."""
    print("\n" + "=" * 80)
    print("TEST 2: Directory Scan with File Limit")
    print("=" * 80)

    config = ComponentConfig(
        type="directory_scanner",
        name="limited_scanner",
        enabled=True,
        config={
            "recursive": False,
            "file_patterns": ["*.txt"],
            "supported_extensions": [".txt"],
            "max_files": 5  # Limit to 5 files
        }
    )

    scanner = DirectoryScanner(config)

    financebench_path = str(project_root / "financebench_data")
    initial_state = PipelineStateManager.create_initial_state(
        pipeline_id="test_scanner_002",
        input_path=financebench_path,
        config={}
    )

    print(f"\nScanning directory with max_files=5")
    result_state = scanner.process(initial_state)

    file_paths = result_state.get("file_paths", [])
    print(f"✓ Found {len(file_paths)} files (limited to 5)")

    print("\nFiles found:")
    for i, file_path in enumerate(file_paths, 1):
        print(f"  {i}. {os.path.basename(file_path)}")

    return result_state


def test_with_pattern():
    """Test scanning with specific filename pattern."""
    print("\n" + "=" * 80)
    print("TEST 3: Directory Scan with Pattern Matching")
    print("=" * 80)

    config = ComponentConfig(
        type="directory_scanner",
        name="pattern_scanner",
        enabled=True,
        config={
            "recursive": False,
            "file_patterns": ["financebench_id_00*.txt"],  # Only files starting with 00
            "supported_extensions": [".txt"],
            "max_files": None
        }
    )

    scanner = DirectoryScanner(config)

    financebench_path = str(project_root / "financebench_data")
    initial_state = PipelineStateManager.create_initial_state(
        pipeline_id="test_scanner_003",
        input_path=financebench_path,
        config={}
    )

    print(f"\nScanning for files matching pattern: financebench_id_00*.txt")
    result_state = scanner.process(initial_state)

    file_paths = result_state.get("file_paths", [])
    print(f"✓ Found {len(file_paths)} matching files")

    print("\nMatching files:")
    for i, file_path in enumerate(file_paths[:15], 1):
        print(f"  {i:3d}. {os.path.basename(file_path)}")

    if len(file_paths) > 15:
        print(f"  ... and {len(file_paths) - 15} more files")

    return result_state


def test_file_statistics():
    """Display statistics about scanned files."""
    print("\n" + "=" * 80)
    print("TEST 4: File Statistics Analysis")
    print("=" * 80)

    config = ComponentConfig(
        type="directory_scanner",
        name="stats_scanner",
        enabled=True,
        config={
            "recursive": False,
            "file_patterns": ["*.txt"],
            "supported_extensions": [".txt"],
            "max_files": None
        }
    )

    scanner = DirectoryScanner(config)

    financebench_path = str(project_root / "financebench_data")
    initial_state = PipelineStateManager.create_initial_state(
        pipeline_id="test_scanner_004",
        input_path=financebench_path,
        config={}
    )

    result_state = scanner.process(initial_state)
    file_paths = result_state.get("file_paths", [])

    # Calculate statistics
    total_files = len(file_paths)
    total_size = sum(os.path.getsize(fp) for fp in file_paths)
    avg_size = total_size / total_files if total_files > 0 else 0
    min_size = min(os.path.getsize(fp) for fp in file_paths) if file_paths else 0
    max_size = max(os.path.getsize(fp) for fp in file_paths) if file_paths else 0

    # Find smallest and largest files
    smallest_file = min(file_paths, key=lambda f: os.path.getsize(f)) if file_paths else None
    largest_file = max(file_paths, key=lambda f: os.path.getsize(f)) if file_paths else None

    print("\nFile Statistics:")
    print(f"  Total files:        {total_files}")
    print(f"  Total size:         {total_size:,} bytes ({total_size / 1024:.2f} KB)")
    print(f"  Average file size:  {avg_size:.2f} bytes")
    print(f"  Minimum file size:  {min_size} bytes")
    print(f"  Maximum file size:  {max_size} bytes")

    if smallest_file:
        print(f"\n  Smallest file: {os.path.basename(smallest_file)} ({os.path.getsize(smallest_file)} bytes)")
    if largest_file:
        print(f"  Largest file:  {os.path.basename(largest_file)} ({os.path.getsize(largest_file)} bytes)")

    return result_state


def main():
    """Run all scanner tests."""
    print("\n" + "=" * 80)
    print("FinanceBench Scanner Test Suite")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if directory exists
    financebench_path = Path(__file__).parent / "financebench_data"
    if not financebench_path.exists():
        print(f"\n❌ Error: Directory not found: {financebench_path}")
        return

    print(f"Target directory: {financebench_path}")
    print(f"Directory exists: ✓")

    try:
        # Run tests
        test_basic_scan()
        test_with_limit()
        test_with_pattern()
        test_file_statistics()

        print("\n" + "=" * 80)
        print("✓ All tests completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
