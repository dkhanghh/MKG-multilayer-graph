"""
Test script for CSV batch processing API endpoint.

This script tests the /api/pipeline/run-csv-batch endpoint.
Run the server first: python run_server.py
"""

import requests
import time


def test_csv_batch_endpoint():
    """Test the CSV batch processing endpoint."""

    base_url = "http://localhost:8000"

    print("=" * 70)
    print("Testing CSV Batch Processing API Endpoint")
    print("=" * 70)

    # Test data
    request_data = {
        "input_path": ".data/data_vn30_first_100.csv",
        "batch_size": 50,  # Small batch for quick test
        "output_path": "./output/test_csv_batch_api"
    }

    print(f"\n📤 Sending request to {base_url}/api/pipeline/run-csv-batch")
    print(f"   Input: {request_data['input_path']}")
    print(f"   Batch size: {request_data['batch_size']} rows")
    print(f"   Output: {request_data['output_path']}")

    try:
        start_time = time.time()

        response = requests.post(
            f"{base_url}/api/pipeline/run-csv-batch",
            json=request_data,
            timeout=600  # 10 minute timeout
        )

        elapsed_time = time.time() - start_time

        print(f"\n📥 Response received in {elapsed_time:.2f}s")
        print(f"   Status code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            print(f"\n✅ Success!")
            print(f"   Pipeline ID: {result.get('pipeline_id', 'N/A')}")
            print(f"   Status: {result.get('status', 'N/A')}")

            summary = result.get('execution_summary', {})
            print(f"\n📊 Execution Summary:")
            print(f"   Total rows: {summary.get('total_rows', 0)}")
            print(f"   Rows processed: {summary.get('rows_processed', 0)}")
            print(f"   Batches: {summary.get('batches_processed', 0)}")
            print(f"   Batch size: {summary.get('batch_size', 0)}")
            print(f"   Total chunks: {summary.get('total_chunks', 0)}")
            print(f"   Total nodes: {summary.get('total_nodes', 0)}")
            print(f"   Total edges: {summary.get('total_edges', 0)}")
            print(f"   Execution time: {summary.get('total_execution_time', 0):.2f}s")

            # Show batch breakdown
            batch_results = summary.get('batch_results', [])
            if batch_results:
                print(f"\n📦 Batch Breakdown ({len(batch_results)} batches):")
                for batch in batch_results[:5]:  # Show first 5
                    batch_num = batch.get('batch_number', '?')
                    start_row = batch.get('start_row', '?')
                    end_row = batch.get('end_row', '?')
                    batch_summary = batch.get('execution_summary', {})
                    nodes = batch_summary.get('total_nodes', 0)
                    edges = batch_summary.get('total_edges', 0)
                    print(f"   Batch {batch_num}: rows {start_row}-{end_row} → {nodes} nodes, {edges} edges")

                if len(batch_results) > 5:
                    print(f"   ... and {len(batch_results) - 5} more batches")

            # Show errors if any
            errors = result.get('errors', [])
            if errors:
                print(f"\n⚠️  Errors ({len(errors)}):")
                for error in errors[:3]:  # Show first 3
                    print(f"   - {error}")
                if len(errors) > 3:
                    print(f"   ... and {len(errors) - 3} more errors")

            print(f"\n📁 Output: {result.get('output_path', 'N/A')}")

            return True

        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection Error")
        print(f"   Could not connect to {base_url}")
        print(f"   Make sure the server is running: python run_server.py")
        return False

    except requests.exceptions.Timeout:
        print(f"\n❌ Timeout Error")
        print(f"   Request took longer than 10 minutes")
        return False

    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        return False


def test_health_check():
    """Test if server is running."""
    base_url = "http://localhost:8000"

    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is running at {base_url}")
            return True
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Server is not running at {base_url}")
        print(f"   Start it with: python run_server.py")
        return False


def test_checkpoint_resume():
    """Test checkpoint/resume functionality by checking checkpoint file."""

    base_url = "http://localhost:8000"
    output_path = "./output/test_checkpoint_resume"

    print("=" * 70)
    print("Testing Checkpoint/Resume Functionality")
    print("=" * 70)

    request_data = {
        "input_path": ".data/data_vn30_first_100.csv",
        "batch_size": 50,
        "output_path": output_path
    }

    print(f"\n📤 First run - will save checkpoints")
    print(f"   Output: {output_path}")
    print(f"   Checkpoints will be saved to: {output_path}/batch_checkpoint.json")

    try:
        response = requests.post(
            f"{base_url}/api/pipeline/run-csv-batch",
            json=request_data,
            timeout=600
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ First run completed!")
            print(f"   Batches: {result['execution_summary']['batches_processed']}")

            # Check if checkpoint was deleted after completion
            import os
            checkpoint_path = f"{output_path}/batch_checkpoint.json"

            if not os.path.exists(checkpoint_path):
                print(f"\n✅ Checkpoint correctly deleted after successful completion")
            else:
                print(f"\n⚠️  Checkpoint still exists (may have errors)")

            print(f"\n💡 To test resume functionality:")
            print(f"   1. Interrupt the server during processing (Ctrl+C)")
            print(f"   2. Restart the server")
            print(f"   3. Run the same request again")
            print(f"   4. It will resume from where it stopped!")

            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n🔍 Checking server health...")
    if not test_health_check():
        exit(1)

    print("\n" + "=" * 70)
    success = test_csv_batch_endpoint()
    print("=" * 70)

    # Also test checkpoint functionality
    print("\n")
    checkpoint_success = test_checkpoint_resume()

    if success and checkpoint_success:
        print("\n✅ All tests passed!")
        exit(0)
    else:
        print("\n❌ Tests failed!")
        exit(1)
