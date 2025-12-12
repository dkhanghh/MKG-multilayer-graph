# CSV Batch Processing API Guide

This guide explains how to use the CSV batch processing endpoint with `run_server.py`.

## Overview

The `/api/pipeline/run-csv-batch` endpoint processes large CSV files in row-based batches, avoiding memory issues and providing better progress tracking.

**Key Features:**
- ✅ Processes CSV files row-by-row in configurable batches
- ✅ Avoids loading entire CSV into memory
- ✅ Each batch gets its own output directory
- ✅ Aggregates results across all batches
- ✅ Tracks progress per batch

## Quick Start

### 1. Set Configuration

Set the `CONFIG_FILE` environment variable to use VN30 CSV configuration:

```bash
export CONFIG_FILE=examples/config_vn30_csv.yaml
export OPENAI_API_KEY=your-api-key-here
```

Or create a `.env` file in the `server/` directory:

```bash
# server/.env
CONFIG_FILE=examples/config_vn30_csv.yaml
OPENAI_API_KEY=your-api-key-here
```

### 2. Start the Server

```bash
python run_server.py
```

The server will start on `http://localhost:8000` by default.

### 3. Use the CSV Batch Endpoint

## API Endpoints

### POST `/api/pipeline/run-csv-batch`

Process a CSV file in row-based batches.

**Request Body:**

```json
{
  "input_path": ".data/data_vn30_first_100.csv",
  "batch_size": 100,
  "output_path": "./output/vn30_batches"
}
```

**Parameters:**
- `input_path` (required): Path to the CSV file
- `batch_size` (optional): Number of rows per batch (default: 100)
- `output_path` (optional): Output directory (default: `./output/csv_batches`)
- `config` (optional): Custom pipeline configuration (overrides CONFIG_FILE)

**Response:**

```json
{
  "pipeline_id": "csv-batch-abc123",
  "status": "completed",
  "input_path": ".data/data_vn30_first_100.csv",
  "output_path": "./output/vn30_batches",
  "metrics": {
    "total_files_processed": 1,
    "total_chunks_created": 1895,
    "total_nodes_extracted": 523,
    "total_edges_extracted": 412
  },
  "errors": [],
  "execution_summary": {
    "total_rows": 1895,
    "rows_processed": 1895,
    "batches_processed": 19,
    "batch_size": 100,
    "total_chunks": 1895,
    "total_nodes": 523,
    "total_edges": 412,
    "total_execution_time": 1234.56,
    "batch_results": [
      {
        "batch_number": 1,
        "start_row": 1,
        "end_row": 100,
        "row_count": 100,
        "execution_summary": {
          "total_nodes": 28,
          "total_edges": 22
        }
      }
      // ... more batches
    ]
  },
  "timestamp": "2025-12-04T10:30:00Z"
}
```

## Usage Examples

### Example 1: Python Requests

```python
import requests

# Start server first: python run_server.py

# Process CSV in batches of 100 rows
response = requests.post(
    "http://localhost:8000/api/pipeline/run-csv-batch",
    json={
        "input_path": ".data/data_vn30_first_100.csv",
        "batch_size": 100,
        "output_path": "./output/vn30_batches"
    }
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Total rows: {result['execution_summary']['total_rows']}")
print(f"Batches: {result['execution_summary']['batches_processed']}")
print(f"Nodes: {result['execution_summary']['total_nodes']}")
print(f"Edges: {result['execution_summary']['total_edges']}")
print(f"Time: {result['execution_summary']['total_execution_time']:.2f}s")

# Check individual batch results
for batch in result['execution_summary']['batch_results']:
    print(f"Batch {batch['batch_number']}: "
          f"rows {batch['start_row']}-{batch['end_row']} → "
          f"{batch['execution_summary']['total_nodes']} nodes")
```

### Example 2: cURL

```bash
# Basic request
curl -X POST http://localhost:8000/api/pipeline/run-csv-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": ".data/data_vn30_first_100.csv",
    "batch_size": 100
  }'

# With custom output path
curl -X POST http://localhost:8000/api/pipeline/run-csv-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": ".data/data_vn30_first_100.csv",
    "batch_size": 50,
    "output_path": "./output/my_custom_output"
  }'
```

### Example 3: JavaScript/TypeScript

```typescript
// Using fetch
const response = await fetch('http://localhost:8000/api/pipeline/run-csv-batch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    input_path: '.data/data_vn30_first_100.csv',
    batch_size: 100,
    output_path: './output/vn30_batches'
  })
});

const result = await response.json();
console.log('Processing completed!');
console.log(`Total rows: ${result.execution_summary.total_rows}`);
console.log(`Batches: ${result.execution_summary.batches_processed}`);
console.log(`Nodes: ${result.execution_summary.total_nodes}`);
console.log(`Edges: ${result.execution_summary.total_edges}`);
```

### Example 4: With Custom Configuration

```python
import requests

# Override CONFIG_FILE with custom config in request
custom_config = {
    "pipeline": {
        "components": {
            "reader": {
                "type": "csv_reader",
                "config": {
                    "content_column": "content",
                    "metadata_columns": ["company_code", "year"],
                    "use_existing_embeddings": True,
                    "filter_conditions": {
                        "year": "2023"
                    }
                }
            }
        }
    }
}

response = requests.post(
    "http://localhost:8000/api/pipeline/run-csv-batch",
    json={
        "input_path": ".data/data_vn30_first_100.csv",
        "batch_size": 100,
        "config": custom_config
    }
)

result = response.json()
print(f"Processed {result['execution_summary']['rows_processed']} rows (filtered to 2023)")
```

## Comparison: Regular vs CSV Batch Processing

### Regular Endpoint (`/api/pipeline/run`)
- Loads entire CSV into memory
- Good for: Small CSV files (<1000 rows)
- Single output directory
- Faster for small files

```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"input_path": "small_file.csv"}'
```

### CSV Batch Endpoint (`/api/pipeline/run-csv-batch`)
- Processes rows in batches
- Good for: Large CSV files (>1000 rows)
- Separate output per batch
- Better memory management
- Progress tracking per batch

```bash
curl -X POST http://localhost:8000/api/pipeline/run-csv-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "large_file.csv",
    "batch_size": 100
  }'
```

## Output Structure

When using CSV batch processing, the output is organized by batch:

```
./output/vn30_batches/
├── batch_0001/
│   ├── nodes.csv       # Nodes from rows 1-100
│   └── edges.csv       # Edges from rows 1-100
├── batch_0002/
│   ├── nodes.csv       # Nodes from rows 101-200
│   └── edges.csv       # Edges from rows 101-200
├── batch_0003/
│   ├── nodes.csv       # Nodes from rows 201-300
│   └── edges.csv       # Edges from rows 201-300
...
```

## Choosing Batch Size

**Small batch size (50-100 rows):**
- ✅ Lower memory usage
- ✅ Better for very large files
- ❌ More batches = more overhead
- ❌ Slower overall processing

**Large batch size (500-1000 rows):**
- ✅ Fewer batches = less overhead
- ✅ Faster overall processing
- ❌ Higher memory usage
- ❌ Risk of OOM on large rows

**Recommended:**
- Start with 100 rows per batch
- Increase to 200-500 for small row content
- Decrease to 50 for large row content or low memory

## Error Handling

The endpoint returns errors in the response:

```python
result = response.json()

if result['status'] == 'completed_with_errors':
    print(f"Completed with {len(result['errors'])} errors:")
    for error in result['errors']:
        print(f"  - {error}")
```

Errors can occur at batch level:
- Individual batch failures don't stop the entire process
- Other batches continue processing
- Failed batches are reported in errors array

## Monitoring Progress

Since batch processing can take a long time, you can implement polling:

```python
import requests
import time

# Start processing
response = requests.post(
    "http://localhost:8000/api/pipeline/run-csv-batch",
    json={
        "input_path": ".data/large_file.csv",
        "batch_size": 100
    }
)

# For real monitoring, you'd need to implement a progress endpoint
# or use the streaming endpoint instead

result = response.json()
print(f"Processing complete: {result['status']}")
```

## Related Endpoints

- `POST /api/pipeline/run` - Regular pipeline execution
- `POST /api/pipeline/run-batch` - Batch process multiple files
- `POST /api/pipeline/run-async` - Async pipeline execution
- `POST /api/pipeline/stream` - Streaming pipeline with progress

## Troubleshooting

### Configuration not loading

```bash
# Verify CONFIG_FILE is set
echo $CONFIG_FILE

# Check file exists
ls -la $CONFIG_FILE

# Restart server after changing CONFIG_FILE
```

### CSV file not found

```bash
# Use absolute paths
{
  "input_path": "/full/path/to/data.csv"
}

# Or relative from where server runs
{
  "input_path": ".data/data.csv"
}
```

### Out of memory errors

Reduce batch size:

```json
{
  "input_path": "large_file.csv",
  "batch_size": 50
}
```

### Slow processing

Increase batch size (if memory allows):

```json
{
  "input_path": "file.csv",
  "batch_size": 500
}
```

## See Also

- [VN30 CSV Pipeline README](../examples/VN30_CSV_PIPELINE_README.md)
- [Server Configuration Guide](CONFIG_LOADING.md)
- [CSV Reader Documentation](../knowledge_graphs/components/csv_reader.py)
- [Batch Processor Implementation](../knowledge_graphs/pipeline/csv_batch_processor.py)
