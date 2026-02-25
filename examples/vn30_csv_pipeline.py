"""
VN30 CSV Pipeline Example

This script demonstrates how to process VN30 financial reports from a CSV file
and build a knowledge graph using the KAG-LangGraph pipeline.
"""

import os
import sys
import logging
from pathlib import Path

# Add the package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graphs.pipeline import PipelineWorkflow
from knowledge_graphs.pipeline.config import load_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Run VN30 CSV pipeline with full dataset.

    Processes all rows from the VN30 financial reports CSV and builds
    a knowledge graph.
    """
    print("=" * 70)
    print("🚀 VN30 Financial Reports Knowledge Graph Pipeline")
    print("=" * 70)

    # Get paths
    config_path = Path(__file__).parent / "config_vn30_csv.yaml"
    csv_path = Path(__file__).parent.parent / ".data" / "data_vn30_first_100.csv"

    # Verify files exist
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        return

    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return

    print(f"\n📋 Configuration: {config_path}")
    print(f"📄 CSV Data: {csv_path}")

    # Check for API key
    if "OPENAI_API_KEY" not in os.environ:
        print("\n⚠️  Warning: OPENAI_API_KEY not found in environment")
        print("   The extractor component requires an OpenAI API key")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            return

    try:
        # Load configuration
        print("\n🔧 Loading configuration...")
        workflow = PipelineWorkflow(config_path=str(config_path))

        # Run pipeline
        print(f"\n🔄 Processing CSV file...")
        print(f"   This may take 30-60 minutes depending on the dataset size")
        print(f"   and LLM extraction speed...\n")

        results = workflow.run_pipeline(str(csv_path))

        # Display results
        print("\n" + "=" * 70)
        print("✅ Pipeline Completed Successfully!")
        print("=" * 70)

        if "execution_summary" in results:
            summary = results["execution_summary"]
            print(f"\n📊 Execution Summary:")
            print(f"   - Total chunks processed: {summary.get('total_chunks', 0)}")
            print(f"   - Total nodes extracted: {summary.get('total_nodes', 0)}")
            print(f"   - Total edges extracted: {summary.get('total_edges', 0)}")

            if "component_times" in summary:
                print(f"\n⏱️  Component Execution Times:")
                for component, time in summary["component_times"].items():
                    print(f"   - {component}: {time:.2f}s")

        if "output_path" in results:
            print(f"\n📁 Output saved to: {results['output_path']}")
            print(f"   Check for nodes.csv and edges.csv files")

        print("\n" + "=" * 70)

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1

    return 0


def run_with_filtering(company_code=None, year=None):
    """
    Run pipeline with filtering to process specific subset of data.

    Args:
        company_code: Filter to specific company code (e.g., "VPB")
        year: Filter to specific year (e.g., "2023")
    """
    print("=" * 70)
    print("🚀 VN30 CSV Pipeline - Filtered Processing")
    print("=" * 70)

    # Get paths
    config_path = Path(__file__).parent / "config_vn30_csv.yaml"
    csv_path = Path(__file__).parent.parent / ".data" / "data_vn30_first_100.csv"

    if not config_path.exists() or not csv_path.exists():
        print("❌ Required files not found")
        return

    try:
        # Load and modify configuration
        print("\n🔧 Loading configuration with filters...")
        config = load_config(str(config_path))

        # Add filter conditions
        filter_conditions = {}
        if company_code:
            filter_conditions["company_code"] = company_code
            print(f"   Filtering by company: {company_code}")
        if year:
            filter_conditions["year"] = year
            print(f"   Filtering by year: {year}")

        if filter_conditions:
            config["pipeline"]["components"]["reader"]["config"]["filter_conditions"] = filter_conditions

        # Create workflow with modified config
        workflow = PipelineWorkflow(config=config)

        # Run pipeline
        print(f"\n🔄 Processing filtered CSV data...")
        results = workflow.run_pipeline(str(csv_path))

        # Display results
        print("\n✅ Pipeline Completed!")
        if "execution_summary" in results:
            summary = results["execution_summary"]
            print(f"   Chunks: {summary.get('total_chunks', 0)}")
            print(f"   Nodes: {summary.get('total_nodes', 0)}")
            print(f"   Edges: {summary.get('total_edges', 0)}")

        if "output_path" in results:
            print(f"\n📁 Output: {results['output_path']}")

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        print(f"❌ Error: {e}")


def run_sample(num_rows=10):
    """
    Process only first N rows for quick testing.

    This is useful for testing the pipeline setup without processing
    the entire dataset.

    Args:
        num_rows: Number of rows to process (default: 10)
    """
    print("=" * 70)
    print(f"🚀 VN30 CSV Pipeline - Sample Mode ({num_rows} rows)")
    print("=" * 70)

    # Get paths
    config_path = Path(__file__).parent / "config_vn30_csv.yaml"
    csv_path = Path(__file__).parent.parent / ".data" / "data_vn30_first_100.csv"

    if not config_path.exists() or not csv_path.exists():
        print("❌ Required files not found")
        return

    # Create temporary sample CSV
    import csv
    temp_csv_path = Path(__file__).parent / "temp_sample.csv"

    try:
        print(f"\n📝 Creating sample CSV with first {num_rows} rows...")

        with open(csv_path, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            header = next(reader)

            with open(temp_csv_path, 'w', encoding='utf-8', newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(header)

                for i, row in enumerate(reader):
                    if i >= num_rows:
                        break
                    writer.writerow(row)

        print(f"✓ Sample CSV created: {temp_csv_path}")

        # Run pipeline on sample
        print("\n🔧 Loading configuration...")
        workflow = PipelineWorkflow(config_path=str(config_path))

        print(f"\n🔄 Processing sample data...")
        results = workflow.run_pipeline(str(temp_csv_path))

        # Display results
        print("\n✅ Sample Pipeline Completed!")
        if "execution_summary" in results:
            summary = results["execution_summary"]
            print(f"   Chunks: {summary.get('total_chunks', 0)}")
            print(f"   Nodes: {summary.get('total_nodes', 0)}")
            print(f"   Edges: {summary.get('total_edges', 0)}")

        if "output_path" in results:
            print(f"\n📁 Output: {results['output_path']}")

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        print(f"❌ Error: {e}")

    finally:
        # Clean up temp file
        if temp_csv_path.exists():
            temp_csv_path.unlink()
            print(f"\n🧹 Cleaned up temporary file")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="VN30 Financial Reports Knowledge Graph Pipeline"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "filter", "sample"],
        default="full",
        help="Processing mode (default: full)"
    )
    parser.add_argument(
        "--company",
        type=str,
        help="Filter by company code (e.g., VPB)"
    )
    parser.add_argument(
        "--year",
        type=str,
        help="Filter by year (e.g., 2023)"
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=10,
        help="Number of rows for sample mode (default: 10)"
    )

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs("./output", exist_ok=True)

    # Run appropriate mode
    if args.mode == "full":
        exit_code = main()
        sys.exit(exit_code if exit_code else 0)
    elif args.mode == "filter":
        run_with_filtering(company_code=args.company, year=args.year)
    elif args.mode == "sample":
        run_sample(num_rows=args.rows)
