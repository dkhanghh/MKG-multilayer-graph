# VN30 Financial Reports CSV Pipeline

This document explains how to use the new CSV reader component to process VN30 financial reports and build a knowledge graph.

## Overview

The CSV reader component allows you to feed data from `.data/data_vn30_first_100.csv` (or any CSV file) into the knowledge graph pipeline. Each row in the CSV becomes a chunk that flows through the pipeline for entity extraction and graph building.

## Quick Start

### 1. Set up your OpenAI API key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 2. Run the pipeline

#### Option A: Sample Mode (Recommended for testing)

Process first 10 rows to test the setup:

```bash
cd examples
python vn30_csv_pipeline.py --mode sample --rows 10
```

#### Option B: Full Dataset

Process all 1,896 rows (takes ~30-60 minutes):

```bash
cd examples
python vn30_csv_pipeline.py --mode full
```

#### Option C: Filtered Mode

Process only specific companies or years:

```bash
# Filter by company
python vn30_csv_pipeline.py --mode filter --company VPB

# Filter by year
python vn30_csv_pipeline.py --mode filter --year 2023

# Filter by both
python vn30_csv_pipeline.py --mode filter --company VPB --year 2023
```

## Output

The pipeline generates two CSV files in `./output/vn30_knowledge_graph/`:

- `nodes.csv` - Extracted entities (companies, metrics, time periods, etc.)
- `edges.csv` - Relationships between entities

## Configuration

The pipeline configuration is in [config_vn30_csv.yaml](config_vn30_csv.yaml). Key settings:

### CSV Reader Configuration

```yaml
reader:
  type: "csv_reader"
  config:
    encoding: "utf-8"
    content_column: "content"  # Column containing main text
    id_column: "_id"           # Column for unique IDs
    metadata_columns:          # Columns to extract as metadata
      - "company_code"
      - "company_name"
      - "year"
      - "quarter"
    embedding_column: "content_vector"
    use_existing_embeddings: true  # Use pre-computed embeddings
    skip_empty_content: true       # Skip rows with empty content
```

### Entity Types Extracted

The LLM extractor is configured to identify:

- **Company** - Organization names
- **Financial_Metric** - Financial values and metrics
- **Time_Period** - Dates, quarters, years
- **Report_Section** - Document sections
- **Currency_Amount** - Monetary values

### Relationship Types

- **reports** - Company reports metric
- **has_metric** - Entity has financial metric
- **in_period** - Event in time period
- **part_of** - Section part of document
- **measures** - Metric measures concept

## Features

### Pre-computed Embeddings

The CSV contains embeddings in PostgreSQL array format (`{0.058,0.047,...}`). The reader automatically:

1. Parses the PostgreSQL array format
2. Converts to Python list of floats
3. Stores in `Chunk.embeddings` field
4. Skips the vectorizer component (already have embeddings)

### Metadata Preservation

All CSV columns specified in `metadata_columns` are preserved in the chunk's `processing_metadata`:

```python
{
  "source_type": "csv",
  "source_file": "/path/to/csv",
  "csv_row_index": 0,
  "company_code": "VPB",
  "company_name": "Ngân hàng Thương mại Cổ phần Việt Nam Thịnh Vượng",
  "year": "2023",
  "quarter": "3",
  "language": "vi",
  "is_tabular_data": True
}
```

### Filtering

You can filter data at read time by adding `filter_conditions` to the config:

```yaml
reader:
  config:
    filter_conditions:
      company_code: "VPB"
      year: "2023"
```

This processes only rows matching all filter conditions.

### Vietnamese Text Support

The reader uses UTF-8 encoding by default and correctly handles Vietnamese text from the financial reports.

## File Structure

```
examples/
├── config_vn30_csv.yaml        # Pipeline configuration
├── vn30_csv_pipeline.py        # Main script
└── VN30_CSV_PIPELINE_README.md # This file

knowledge_graphs/components/
├── csv_reader.py               # CSV reader implementation
└── __init__.py                 # Component registration

tests/
└── test_csv_reader.py          # Unit tests (all passing)
```

## Architecture

The pipeline follows this flow:

```
CSV File → Scanner → CSV Reader → Splitter → Extractor → Vectorizer → Writer
                     [NEW]         [SKIP]    [LLM]      [SKIP]      [CSV]
```

- **Scanner**: Locates the CSV file
- **CSV Reader**: Parses CSV and creates chunks (1 per row)
- **Splitter**: Disabled (rows already appropriately sized)
- **Extractor**: LLM-based entity and relationship extraction
- **Vectorizer**: Disabled (using existing embeddings)
- **Writer**: Outputs nodes.csv and edges.csv

## Performance

- **CSV Reading**: ~5 seconds for 1,896 rows
- **LLM Extraction**: ~30-60 minutes for full dataset (depends on batch size and API limits)
- **Total**: 30-60 minutes for complete pipeline

**Optimization Tips:**

1. Start with sample mode (`--rows 10`) to test setup
2. Use filtering to process specific subsets
3. Increase `batch_size` in extractor config for faster processing
4. Consider using a faster model like `gpt-3.5-turbo` instead of `gpt-4`

## Testing

Run unit tests:

```bash
python -m pytest tests/test_csv_reader.py -v
```

All 10 tests should pass:

- ✅ Basic CSV reading
- ✅ Metadata extraction
- ✅ Embedding parsing (PostgreSQL format)
- ✅ Row filtering
- ✅ Empty content skipping
- ✅ UTF-8 encoding (Vietnamese)
- ✅ Boolean conversion
- ✅ Embeddings integration
- ✅ Embeddings disabled mode
- ✅ Error handling

## Troubleshooting

### No API key error

```
Error: OPENAI_API_KEY not found
```

**Solution**: Export your API key:
```bash
export OPENAI_API_KEY="your-key"
```

### Content column not found

```
ValueError: Content column 'content' not found in CSV
```

**Solution**: Check that your CSV has a `content` column, or update `content_column` in config.

### Empty output

If you get 0 chunks:

1. Check that CSV has non-empty content in the `content` column
2. Verify filter conditions aren't too restrictive
3. Check `skip_empty_content` setting

### Encoding issues

If Vietnamese text looks garbled:

1. Ensure CSV is UTF-8 encoded
2. Check `encoding: "utf-8"` in reader config

## Advanced Usage

### Using with Different CSV Files

To process a different CSV file:

1. Update the CSV path in the script or pass as argument
2. Update column names in config to match your CSV structure
3. Adjust metadata_columns and entity_types as needed

### Custom Entity Types

Edit the extractor config in `config_vn30_csv.yaml`:

```yaml
extractor:
  config:
    entity_types:
      - "YourEntityType1"
      - "YourEntityType2"
```

### Batch Processing

To process multiple CSV files, modify the scanner or create a loop in your script:

```python
csv_files = ["file1.csv", "file2.csv", "file3.csv"]
for csv_file in csv_files:
    results = workflow.run_pipeline(csv_file)
```

## Next Steps

1. **Test with sample data**: Run with `--mode sample --rows 10`
2. **Inspect output**: Check `./output/vn30_knowledge_graph/nodes.csv` and `edges.csv`
3. **Visualize graph**: Use graph visualization tools to explore the knowledge graph
4. **Iterate**: Adjust entity types, relationships, and filters as needed
5. **Full run**: Process the complete dataset with `--mode full`

## Support

- See the main [README](../README.md) for general pipeline documentation
- Check test file for usage examples: [test_csv_reader.py](../tests/test_csv_reader.py)
- Review the CSV reader source: [csv_reader.py](../knowledge_graphs/components/csv_reader.py)
