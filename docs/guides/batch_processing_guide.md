# Batch Processing Guide

**Purpose:** Process large numbers of files in smaller batches to avoid memory issues and prevent the pipeline from getting stuck.

---

## Problem

When processing many files at once (e.g., 150 files), the pipeline can:
- Run out of memory
- Get stuck or freeze
- Take too long without progress indication
- Be difficult to recover from failures

## Solution: Batch Processing

Process files in **batches of 10** (or any number you choose) to:
- ✅ Keep memory usage low
- ✅ See progress after each batch
- ✅ Recover easily from failures
- ✅ Better resource management

---

## How It Works

```
Directory: financebench_data/ (150 files)
Batch Size: 10

┌──────────────────────────────────────────────┐
│ Batch 1: Files 1-10                          │
│ Process → Extract → Vectorize → Write        │
│ ✓ Complete                                   │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ Batch 2: Files 11-20                         │
│ Process → Extract → Vectorize → Write        │
│ ✓ Complete                                   │
└──────────────────────────────────────────────┘

... (continue for all batches)

┌──────────────────────────────────────────────┐
│ Batch 15: Files 141-150                      │
│ Process → Extract → Vectorize → Write        │
│ ✓ Complete                                   │
└──────────────────────────────────────────────┘

Results: Aggregated from all 15 batches
```

---

## Usage

### Method 1: Using the API Server

#### Start the server:
```bash
python server.py
```

#### Use the batch processing endpoint:

**POST `/pipeline/run-batch`**

```python
import requests

response = requests.post(
    "http://localhost:8000/pipeline/run-batch",
    json={
        "input_path": "./financebench_data",
        "batch_size": 10,  # Process 10 files at a time
        "output_path": "./output"
    }
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Total files: {result['execution_summary']['total_files']}")
print(f"Batches processed: {result['execution_summary']['batches_processed']}")
print(f"Total nodes: {result['execution_summary']['total_nodes']}")
print(f"Total edges: {result['execution_summary']['total_edges']}")
```

### Method 2: Using Python Directly

```python
from knowledge_graphs.pipeline.batch_processor import process_directory_in_batches

# Your pipeline configuration
config = {
    "pipeline": {
        "components": {
            "scanner": {...},
            "reader": {...},
            "splitter": {...},
            "extractor": {...},
            "vectorizer": {
                "type": "gemini_vectorizer",
                "batch_size": 100,  # Embedding batch size
                "max_retries": 3,
                "retry_delay": 10
            },
            "writer": {...}
        }
    }
}

# Process with batch_size=10 files per batch
results = process_directory_in_batches(
    input_path="./financebench_data",
    config=config,
    batch_size=10  # FILE batch size
)

print(f"Processed {results['execution_summary']['total_files']} files")
print(f"In {results['execution_summary']['batches_processed']} batches")
print(f"Total nodes: {results['execution_summary']['total_nodes']}")
print(f"Total edges: {results['execution_summary']['total_edges']}")
```

### Method 3: Using BatchPipelineProcessor Class

```python
from knowledge_graphs.pipeline.batch_processor import BatchPipelineProcessor

# Create processor with batch size
processor = BatchPipelineProcessor(
    config=your_config,
    batch_size=10
)

# Process directory
results = processor.process_directory_in_batches("./financebench_data")
```

---

## Configuration

### Two Different Batch Sizes

**Important:** There are TWO different `batch_size` parameters:

1. **File Batch Size** (new - in batch processor)
   - How many FILES to process in each batch
   - Recommended: 10 files
   - Controls memory usage and progress granularity

2. **Embedding Batch Size** (existing - in vectorizer)
   - How many ITEMS (nodes/edges) in each API request
   - Recommended: 100 for Paid Tier 1
   - Controls API efficiency

```python
{
    "pipeline": {
        "components": {
            "vectorizer": {
                "type": "gemini_vectorizer",
                "batch_size": 100,  # ← Embedding batch size (items per API request)
                "max_retries": 3,
                "retry_delay": 10
            }
        }
    }
}

# When calling batch processor:
results = process_directory_in_batches(
    input_path="./financebench_data",
    config=config,
    batch_size=10  # ← FILE batch size (files per batch)
)
```

---

## Recommended Settings

### For 150 FinanceBench Files

```python
{
    # File processing batches
    "file_batch_size": 10,  # Process 10 files at a time

    # Vectorizer settings
    "vectorizer": {
        "type": "gemini_vectorizer",
        "batch_size": 100,    # 100 items per API request
        "max_retries": 3,
        "retry_delay": 10
    }
}
```

**Processing breakdown:**
- 150 files ÷ 10 = 15 file batches
- Each batch processes 10 files
- Each file generates ~18 items (nodes + edges)
- 180 items per file batch ÷ 100 = ~2 API requests per file batch
- Total: 15 file batches × ~2 API requests = ~30 API requests

**Time estimate:**
- ~2 minutes per file batch
- 15 batches × 2 min = ~30 minutes total
- With clear progress indication after each batch

---

## Benefits

### 1. Memory Efficiency
```
Without batching: Process all 150 files at once → 🔴 High memory usage
With batching: Process 10 files at a time → ✅ Low memory usage
```

### 2. Progress Visibility
```
Without batching:
  Starting...
  (waiting 30 minutes...)
  ❌ Failed at file 143 (no idea where)

With batching:
  Batch 1/15 complete ✓
  Batch 2/15 complete ✓
  ...
  Batch 14/15 complete ✓
  ❌ Batch 15 failed (easy to retry just this batch)
```

### 3. Failure Recovery
```
Without batching:
  Process 150 files → Fails at file 100
  Result: Lost all progress, must restart from beginning

With batching:
  Process batch 1 (files 1-10) ✓ Saved to database
  Process batch 2 (files 11-20) ✓ Saved to database
  ...
  Process batch 10 (files 91-100) ❌ Failed
  Result: 90 files already saved, only retry batch 10
```

### 4. Resource Management
```
Without batching:
  - All vectorizer embeddings cached in memory
  - All subgraphs held until end
  - Database connection held for entire duration

With batching:
  - Embeddings cached per batch, then cleared
  - Subgraphs written immediately per batch
  - Database connection can be reused efficiently
```

---

## Output Structure

### Response Format

```json
{
  "pipeline_id": "batch-12345",
  "status": "completed",
  "input_path": "./financebench_data",
  "output_path": "./output/kg_graph.json",
  "metrics": {
    "total_files_processed": 150,
    "total_chunks_created": 4500,
    "total_nodes_extracted": 7500,
    "total_edges_extracted": 9000,
    "total_execution_time": 1800.5
  },
  "execution_summary": {
    "total_files": 150,
    "files_processed": 150,
    "batches_processed": 15,
    "batch_size": 10,
    "total_nodes": 7500,
    "total_edges": 9000,
    "total_execution_time": 1800.5,
    "batch_results": [
      {
        "batch_number": 1,
        "batch_files": ["file1.txt", "file2.txt", ...],
        "files_processed": 10,
        "total_nodes": 500,
        "total_edges": 600
      },
      ...
    ]
  },
  "errors": []
}
```

---

## Monitoring Progress

### Using Logs

The batch processor provides detailed logging:

```
INFO: Found 150 files to process in 15 batches
INFO: Processing batch 1/15 (10 files)
INFO:   Processing file 1/10: financebench_id_00005.txt
INFO:   Processing file 2/10: financebench_id_00070.txt
...
INFO: Batch 1/15 completed. Nodes: 500, Edges: 600
INFO: Processing batch 2/15 (10 files)
...
INFO: All batches completed! Total files: 150, Batches: 15, Total nodes: 7500, Total edges: 9000, Time: 1800.23s
```

### Progress Calculation

```python
# In your application
total_batches = 15
current_batch = 7

progress_percentage = (current_batch / total_batches) * 100
print(f"Progress: {progress_percentage:.1f}% ({current_batch}/{total_batches} batches)")
# Output: Progress: 46.7% (7/15 batches)
```

---

## Troubleshooting

### Issue 1: Batch Too Large (Out of Memory)

**Symptoms:**
- Process crashes during a batch
- Memory error messages

**Solution:**
```python
# Reduce batch size
batch_size=5  # Instead of 10
```

### Issue 2: Batch Too Small (Too Slow)

**Symptoms:**
- Too many batches
- Excessive logging
- Slow overall progress

**Solution:**
```python
# Increase batch size
batch_size=20  # Instead of 10
```

### Issue 3: Batch Fails Midway

**Symptoms:**
- Some batches complete, then one fails

**Solution:**
```python
# Check the batch results to see which batch failed
for batch in results['execution_summary']['batch_results']:
    if batch.get('status') == 'failed':
        print(f"Batch {batch['batch_number']} failed")
        print(f"Files: {batch['batch_files']}")

# Reprocess just the failed batch manually
failed_files = batch['batch_files']
# Process these files separately
```

---

## Best Practices

### 1. Choose Appropriate Batch Size

```python
# Small files (~1-2 KB each)
batch_size = 20

# Medium files (~10-50 KB each)
batch_size = 10  # ← Recommended for FinanceBench

# Large files (>100 KB each)
batch_size = 5
```

### 2. Monitor First Batch

```python
# Test with one batch first
processor = BatchPipelineProcessor(config, batch_size=10)

# Process just first 10 files to test
test_files = all_files[:10]
# Check memory usage, time, and results
# Adjust batch_size if needed
```

### 3. Save Results After Each Batch

The batch processor automatically writes to the database after each batch, so you don't lose progress if something fails.

### 4. Use Logging

```python
import logging
logging.basicConfig(level=logging.INFO)

# Now you'll see detailed progress:
# INFO: Processing batch 3/15...
# INFO: Batch 3/15 completed...
```

---

## Comparison: Standard vs Batch Processing

| Aspect | Standard Processing | Batch Processing (10 files) |
|--------|--------------------|-----------------------------|
| **Memory Usage** | High (all files at once) | Low (10 files at a time) |
| **Progress Visibility** | None until complete | After each batch |
| **Failure Recovery** | Restart from beginning | Resume from failed batch |
| **Processing Time** | Same total time | Same total time + logging overhead |
| **Reliability** | Can crash with many files | More reliable |
| **Debugging** | Difficult to find issues | Easy to isolate problems |

---

## Example: Processing FinanceBench

### Using API:

```bash
# Start server
python server.py

# In another terminal, run:
curl -X POST "http://localhost:8000/pipeline/run-batch" \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "./financebench_data",
    "batch_size": 10
  }'
```

### Using Python:

```python
from knowledge_graphs.pipeline.batch_processor import process_directory_in_batches

results = process_directory_in_batches(
    input_path="./financebench_data",
    config=DEFAULT_CONFIG,
    batch_size=10
)

print(f"✓ Processed {results['execution_summary']['total_files']} files")
print(f"  Nodes: {results['execution_summary']['total_nodes']}")
print(f"  Edges: {results['execution_summary']['total_edges']}")
print(f"  Time: {results['execution_summary']['total_execution_time']:.2f}s")
```

---

## Summary

✅ **Use batch processing when:**
- Processing more than 20 files
- Memory usage is a concern
- You want progress visibility
- You need failure recovery

⚙️ **Recommended settings:**
- File batch size: 10
- Embedding batch size: 100
- Max retries: 3
- Retry delay: 10s

📊 **For 150 FinanceBench files:**
- 15 batches of 10 files each
- ~2 minutes per batch
- ~30 minutes total
- Clear progress after each batch
- Easy to recover from failures

---

**Status:** ✅ Batch processing implemented and ready to use!
