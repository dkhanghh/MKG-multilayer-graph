#!/usr/bin/env python3
"""
Test runner script for LLMExtractor and GeminiVectorizer unit tests.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --verbose          # Run with verbose output
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_tests(test_args=None):
    """Run pytest with specified arguments."""
    if test_args is None:
        test_args = []

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Add test arguments
    cmd.extend(test_args)

    # Run the tests
    print(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=False, cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run unit tests for KAG-LangGraph components")

    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Run with verbose output"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Run specific test file"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Run specific test function"
    )

    args = parser.parse_args()

    # Build pytest arguments
    test_args = []

    if args.unit:
        test_args.extend(["-m", "unit"])

    if args.coverage:
        test_args.extend(["--cov=knowledge_graphs", "--cov-report=html", "--cov-report=term"])

    if args.verbose:
        test_args.append("-v")

    if args.file:
        test_args.append(args.file)

    if args.test:
        test_args.extend(["-k", args.test])

    # Default: run the extractor and vectorizer tests
    if not args.file and not args.test:
        test_args.append("tests/test_extractor_and_vectorizer.py")

    return run_tests(test_args)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)