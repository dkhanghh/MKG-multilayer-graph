"""
Simple standalone test for Scanner component with financebench_data directory.

This script tests the DirectoryScanner without importing the full pipeline.
"""

import os
import sys
import glob
from pathlib import Path
from datetime import datetime
from typing import List, Set


class SimpleDirectoryScanner:
    """Simplified scanner for testing purposes."""

    def __init__(self,
                 recursive: bool = True,
                 file_patterns: List[str] = None,
                 supported_extensions: List[str] = None,
                 max_files: int = None):
        self.recursive = recursive
        self.file_patterns = file_patterns or ["*"]
        self.supported_extensions = supported_extensions or [".pdf", ".txt", ".docx", ".md"]
        self.max_files = max_files

    def scan(self, directory: str) -> List[str]:
        """Scan directory for files."""
        if not os.path.exists(directory):
            raise ValueError(f"Directory does not exist: {directory}")

        if not os.path.isdir(directory):
            raise ValueError(f"Not a directory: {directory}")

        discovered_files = self._discover_files(directory)
        return discovered_files

    def _discover_files(self, directory: str) -> List[str]:
        """Discover files matching criteria."""
        discovered_files: Set[str] = set()
        root_path = Path(directory)

        for pattern in self.file_patterns:
            if self.recursive:
                search_pattern = root_path / "**" / pattern
                matches = glob.glob(str(search_pattern), recursive=True)
            else:
                search_pattern = root_path / pattern
                matches = glob.glob(str(search_pattern))

            for match in matches:
                if self._should_include_file(match):
                    discovered_files.add(match)

                    if self.max_files and len(discovered_files) >= self.max_files:
                        return sorted(list(discovered_files))

        return sorted(list(discovered_files))

    def _should_include_file(self, file_path: str) -> bool:
        """Check if file should be included."""
        if not os.path.isfile(file_path):
            return False

        file_path_obj = Path(file_path)

        # Check supported extensions
        if self.supported_extensions:
            extension = file_path_obj.suffix.lower()
            if extension not in [ext.lower() for ext in self.supported_extensions]:
                return False

        # Check if file is readable
        try:
            with open(file_path, 'rb') as f:
                f.read(1)
            return True
        except (PermissionError, OSError):
            return False


def print_separator(title: str = ""):
    """Print a separator line."""
    print("\n" + "=" * 80)
    if title:
        print(title)
        print("=" * 80)


def test_basic_scan():
    """Test basic directory scanning."""
    print_separator("TEST 1: Basic Directory Scan")

    financebench_path = "./financebench_data"

    scanner = SimpleDirectoryScanner(
        recursive=False,
        file_patterns=["*.txt"],
        supported_extensions=[".txt"],
        max_files=None
    )

    print(f"\nScanning directory: {financebench_path}")
    print(f"Recursive: {scanner.recursive}")
    print(f"Patterns: {scanner.file_patterns}")
    print(f"Extensions: {scanner.supported_extensions}")

    file_paths = scanner.scan(financebench_path)

    print(f"\n✓ Scan completed successfully!")
    print(f"Total files found: {len(file_paths)}")

    print("\nFirst 10 files:")
    for i, file_path in enumerate(file_paths[:10], 1):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        print(f"  {i:3d}. {filename:50s} ({file_size:,} bytes)")

    if len(file_paths) > 10:
        print(f"  ... and {len(file_paths) - 10} more files")

    return file_paths


def test_with_limit():
    """Test scanning with max_files limit."""
    print_separator("TEST 2: Directory Scan with File Limit")

    financebench_path = "./financebench_data"

    scanner = SimpleDirectoryScanner(
        recursive=False,
        file_patterns=["*.txt"],
        supported_extensions=[".txt"],
        max_files=5
    )

    print(f"\nScanning directory with max_files=5")
    file_paths = scanner.scan(financebench_path)

    print(f"✓ Found {len(file_paths)} files (limited to 5)")

    print("\nFiles found:")
    for i, file_path in enumerate(file_paths, 1):
        print(f"  {i}. {os.path.basename(file_path)}")

    return file_paths


def test_with_pattern():
    """Test scanning with specific filename pattern."""
    print_separator("TEST 3: Directory Scan with Pattern Matching")

    financebench_path = "./financebench_data"

    scanner = SimpleDirectoryScanner(
        recursive=False,
        file_patterns=["financebench_id_00*.txt"],
        supported_extensions=[".txt"],
        max_files=None
    )

    print(f"\nScanning for files matching pattern: financebench_id_00*.txt")
    file_paths = scanner.scan(financebench_path)

    print(f"✓ Found {len(file_paths)} matching files")

    print("\nMatching files (first 15):")
    for i, file_path in enumerate(file_paths[:15], 1):
        print(f"  {i:3d}. {os.path.basename(file_path)}")

    if len(file_paths) > 15:
        print(f"  ... and {len(file_paths) - 15} more files")

    return file_paths


def test_file_statistics():
    """Display statistics about scanned files."""
    print_separator("TEST 4: File Statistics Analysis")

    financebench_path = "./financebench_data"

    scanner = SimpleDirectoryScanner(
        recursive=False,
        file_patterns=["*.txt"],
        supported_extensions=[".txt"],
        max_files=None
    )

    file_paths = scanner.scan(financebench_path)

    # Calculate statistics
    total_files = len(file_paths)

    if total_files == 0:
        print("No files found!")
        return []

    total_size = sum(os.path.getsize(fp) for fp in file_paths)
    avg_size = total_size / total_files
    min_size = min(os.path.getsize(fp) for fp in file_paths)
    max_size = max(os.path.getsize(fp) for fp in file_paths)

    smallest_file = min(file_paths, key=lambda f: os.path.getsize(f))
    largest_file = max(file_paths, key=lambda f: os.path.getsize(f))

    print("\nFile Statistics:")
    print(f"  Total files:        {total_files}")
    print(f"  Total size:         {total_size:,} bytes ({total_size / 1024:.2f} KB)")
    print(f"  Average file size:  {avg_size:.2f} bytes")
    print(f"  Minimum file size:  {min_size} bytes")
    print(f"  Maximum file size:  {max_size} bytes")

    print(f"\n  Smallest file: {os.path.basename(smallest_file)} ({os.path.getsize(smallest_file)} bytes)")
    print(f"  Largest file:  {os.path.basename(largest_file)} ({os.path.getsize(largest_file)} bytes)")

    # Show sample content from smallest file
    print(f"\n  Sample content from smallest file ({os.path.basename(smallest_file)}):")
    try:
        with open(smallest_file, 'r', encoding='utf-8') as f:
            content = f.read(200)
            print(f"    {content[:200]}...")
    except Exception as e:
        print(f"    Error reading file: {e}")

    return file_paths


def test_multiple_patterns():
    """Test scanning with multiple patterns."""
    print_separator("TEST 5: Multiple Pattern Matching")

    financebench_path = "./financebench_data"

    scanner = SimpleDirectoryScanner(
        recursive=False,
        file_patterns=["financebench_id_001*.txt", "financebench_id_002*.txt"],
        supported_extensions=[".txt"],
        max_files=None
    )

    print(f"\nScanning for files matching multiple patterns:")
    print(f"  - financebench_id_001*.txt")
    print(f"  - financebench_id_002*.txt")

    file_paths = scanner.scan(financebench_path)

    print(f"\n✓ Found {len(file_paths)} matching files")

    print("\nMatching files:")
    for i, file_path in enumerate(file_paths[:20], 1):
        print(f"  {i:3d}. {os.path.basename(file_path)}")

    if len(file_paths) > 20:
        print(f"  ... and {len(file_paths) - 20} more files")

    return file_paths


def main():
    """Run all scanner tests."""
    print("\n" + "=" * 80)
    print("FinanceBench Scanner Test Suite (Simplified)")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if directory exists
    financebench_path = "./financebench_data"
    if not os.path.exists(financebench_path):
        print(f"\n❌ Error: Directory not found: {financebench_path}")
        print(f"Current working directory: {os.getcwd()}")
        return

    print(f"\nTarget directory: {os.path.abspath(financebench_path)}")
    print(f"Directory exists: ✓")

    try:
        # Run tests
        test_basic_scan()
        test_with_limit()
        test_with_pattern()
        test_file_statistics()
        test_multiple_patterns()

        print("\n" + "=" * 80)
        print("✓ All tests completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
