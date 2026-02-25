"""
Script to drop rows from the beginning of a CSV file up to and including a specific ID.

This script removes all rows from the start of the CSV up to and including the row
with the specified _id value, keeping only the rows after it.
"""

import csv
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def drop_rows_until_id(
    input_csv: str,
    output_csv: str,
    target_id: str,
    encoding: str = "utf-8"
) -> dict:
    """
    Drop all rows from beginning up to and including the row with target_id.

    Args:
        input_csv: Path to input CSV file
        output_csv: Path to output CSV file
        target_id: The _id value to drop up to (inclusive)
        encoding: File encoding (default: utf-8)

    Returns:
        Dictionary with statistics about the operation
    """
    input_path = Path(input_csv)
    output_path = Path(output_csv)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_csv}")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"📂 Reading: {input_csv}")
    print(f"🎯 Target ID: {target_id}")
    print(f"📝 Output: {output_csv}")
    print()

    # Statistics
    total_rows = 0
    dropped_rows = 0
    kept_rows = 0
    found_target = False

    # Read input CSV and write filtered output
    with open(input_path, 'r', encoding=encoding) as infile, \
         open(output_path, 'w', encoding=encoding, newline='') as outfile:

        reader = csv.DictReader(infile)
        headers = reader.fieldnames

        if not headers or '_id' not in headers:
            raise ValueError("CSV must have headers with '_id' column")

        writer = csv.DictWriter(outfile, fieldnames=headers)
        writer.writeheader()

        # Process rows
        for row in reader:
            total_rows += 1

            # Check if this is the target row
            if row['_id'] == target_id:
                found_target = True
                dropped_rows += 1
                print(f"✅ Found target row at row {total_rows + 1} (including header)")
                print(f"   ID: {target_id}")
                print(f"   Company: {row.get('company_name', 'N/A')}")
                print(f"   Year: {row.get('year', 'N/A')}")
                print()
                continue  # Drop this row

            # If target not found yet, drop the row
            if not found_target:
                dropped_rows += 1
            else:
                # Target found and passed, keep this row
                writer.writerow(row)
                kept_rows += 1

            # Progress update every 100 rows
            if total_rows % 100 == 0:
                print(f"   Processed {total_rows} rows... (dropped: {dropped_rows}, kept: {kept_rows})", end='\r')

    print()  # New line after progress

    # Final statistics
    stats = {
        "input_file": str(input_path),
        "output_file": str(output_path),
        "target_id": target_id,
        "total_rows": total_rows,
        "dropped_rows": dropped_rows,
        "kept_rows": kept_rows,
        "target_found": found_target
    }

    return stats


def print_statistics(stats: dict):
    """Print operation statistics."""
    print("=" * 70)
    print("Operation Summary")
    print("=" * 70)
    print(f"Input file:       {stats['input_file']}")
    print(f"Output file:      {stats['output_file']}")
    print(f"Target ID:        {stats['target_id']}")
    print()
    print(f"Total rows:       {stats['total_rows']:,} (excluding header)")
    print(f"Dropped rows:     {stats['dropped_rows']:,}")
    print(f"Kept rows:        {stats['kept_rows']:,}")
    print()

    if stats['target_found']:
        print(f"✅ Target ID found and dropped")
        print(f"   Dropped percentage: {stats['dropped_rows']/stats['total_rows']*100:.1f}%")
        print(f"   Kept percentage: {stats['kept_rows']/stats['total_rows']*100:.1f}%")
    else:
        print(f"❌ Target ID NOT found in file")
        print(f"   No rows were dropped")

    print("=" * 70)


def main():
    """Main function to drop rows up to specific ID."""

    # Configuration
    INPUT_CSV = ".data/vn30/data_vn30_2024.csv"
    OUTPUT_CSV = ".data/vn30/data_vn30_2024_filtered.csv"
    TARGET_ID = "HVA_2024_00021174477696216825ctcp_u_t_hva13082024_000000bo_co_ti_chnh_bn_nin_2024_page_18.json.txt_1"

    print()
    print("=" * 70)
    print("Drop Rows Until Specific ID")
    print("=" * 70)
    print()

    try:
        # Execute the drop operation
        stats = drop_rows_until_id(
            input_csv=INPUT_CSV,
            output_csv=OUTPUT_CSV,
            target_id=TARGET_ID
        )

        # Print statistics
        print_statistics(stats)

        # Success
        print()
        print("✅ Operation completed successfully!")
        print(f"📁 New file created: {OUTPUT_CSV}")
        print()

        return 0

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        return 1
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
