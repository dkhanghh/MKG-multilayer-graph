# CSV Batch Processing - Checkpoint/Resume Guide

This guide explains how to use the checkpoint/resume functionality for CSV batch processing.

## Overview

When processing large CSV files, the batch processor automatically saves checkpoints after each batch. If the process is interrupted (crash, Ctrl+C, power failure, etc.), you can resume from where it left off by running the same command again.

**Key Features:**
- ✅ Automatic checkpoint after each batch
- ✅ Resume from exact batch where it stopped
- ✅ No data loss - all completed batches are preserved
- ✅ Minimal overhead - JSON-based checkpointing
- ✅ Can be disabled if not needed

## How It Works

1. **Checkpoint Creation**: After each batch is processed, a checkpoint file is saved to `{output_dir}/batch_checkpoint.json`
2. **Checkpoint Content**: Contains batch results, aggregated metrics, and progress information
3. **Resume Detection**: When you run the processor again with the same `output_dir`, it automatically detects and loads the checkpoint
4. **Automatic Cleanup**: When all batches complete successfully, the checkpoint is automatically deleted

## Usage

### Basic Usage (Automatic Checkpointing)

Checkpointing is **enabled by default**. Just process your CSV as normal:

```python
from knowledge_graphs.pipeline.csv_batch_processor import process_csv_in_batches
from server.core.config import load_config

config = load_config()

# First run - processes batches 1-10, then crashes at batch 11
results = process_csv_in_batches(
    csv_path=".data/large_file.csv",
    config=config,
    batch_size=100,
    output_dir="./output/my_batches"
)
```

If the process is interrupted:

```python
# Second run - automatically resumes from batch 11
# Uses the SAME parameters (especially output_dir)
results = process_csv_in_batches(
    csv_path=".data/large_file.csv",
    config=config,
    batch_size=100,
    output_dir="./output/my_batches"  # SAME output_dir
)
```

### Using the API Endpoint

The `/api/pipeline/run-csv-batch` endpoint also supports checkpointing:

```bash
# First run - gets interrupted
curl -X POST http://localhost:8000/api/pipeline/run-csv-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": ".data/large_file.csv",
    "batch_size": 100,
    "output_path": "./output/my_batches"
  }'
```

If interrupted, run the **exact same request** to resume:

```bash
# Second run - automatically resumes
curl -X POST http://localhost:8000/api/pipeline/run-csv-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": ".data/large_file.csv",
    "batch_size": 100,
    "output_path": "./output/my_batches"
  }'
```

### Disabling Checkpointing

If you don't want checkpointing (e.g., for testing):

```python
results = process_csv_in_batches(
    csv_path=".data/file.csv",
    config=config,
    batch_size=100,
    output_dir="./output/batches",
    enable_checkpointing=False  # Disable checkpointing
)
```

### Checking Checkpoint Status

To check if a checkpoint exists and see progress:

```python
import json
from pathlib import Path

checkpoint_file = Path("./output/my_batches/batch_checkpoint.json")

if checkpoint_file.exists():
    with open(checkpoint_file) as f:
        checkpoint = json.load(f)

    print(f"Completed: {checkpoint['completed_batches']}/{checkpoint['total_batches']} batches")
    print(f"Progress: {checkpoint['completed_batches']/checkpoint['total_batches']*100:.1f}%")
else:
    print("No checkpoint found - processing hasn't started or completed successfully")
```

### Manually Deleting Checkpoint

If you want to start fresh (ignore previous progress):

```bash
# Delete the checkpoint file
rm ./output/my_batches/batch_checkpoint.json

# Then run again - will start from batch 1
```

## Checkpoint File Format

The checkpoint file (`batch_checkpoint.json`) contains:

```json
{
  "csv_path": ".data/large_file.csv",
  "total_batches": 20,
  "completed_batches": 10,
  "batch_size": 100,
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
    },
    // ... more batch results
  ],
  "metrics": {
    "total_files_processed": 1,
    "total_chunks_created": 1000,
    "total_nodes_extracted": 280,
    "total_edges_extracted": 220
  },
  "errors": [],
  "last_updated": 1733308800.123
}
```

## Common Scenarios

### Scenario 1: Long-Running Process Gets Interrupted

**Problem**: Processing 10,000 rows takes 2 hours, but the server crashes after 1 hour.

**Solution**: Just run the same command again - it will resume from where it stopped.

```python
# First run - crashes after 50% completion
results = process_csv_in_batches(
    csv_path=".data/10000_rows.csv",
    config=config,
    batch_size=100,
    output_dir="./output/large_job"
)

# Second run - resumes from batch 51
results = process_csv_in_batches(
    csv_path=".data/10000_rows.csv",
    config=config,
    batch_size=100,
    output_dir="./output/large_job"  # SAME output_dir
)
```

### Scenario 2: Testing with Small Batches

**Problem**: Testing with a subset of data, don't want old checkpoint interfering.

**Solution**: Use different output directories or disable checkpointing.

```python
# Testing run
results = process_csv_in_batches(
    csv_path=".data/test_sample.csv",
    config=config,
    batch_size=10,
    output_dir="./output/test_run",  # Different directory
    enable_checkpointing=False  # Or disable checkpointing
)
```

### Scenario 3: Multiple CSV Files

**Problem**: Processing multiple CSV files, each needs independent checkpoints.

**Solution**: Use different output directories for each CSV.

```python
csv_files = [
    (".data/file1.csv", "./output/file1"),
    (".data/file2.csv", "./output/file2"),
    (".data/file3.csv", "./output/file3"),
]

for csv_path, output_dir in csv_files:
    # Each file has its own checkpoint
    results = process_csv_in_batches(
        csv_path=csv_path,
        config=config,
        batch_size=100,
        output_dir=output_dir
    )
```

### Scenario 4: Monitoring Progress

**Problem**: Want to track progress of a long-running job.

**Solution**: Check the checkpoint file periodically.

```python
import json
from pathlib import Path
import time

checkpoint_file = Path("./output/my_batches/batch_checkpoint.json")

while True:
    if checkpoint_file.exists():
        with open(checkpoint_file) as f:
            checkpoint = json.load(f)

        completed = checkpoint['completed_batches']
        total = checkpoint['total_batches']
        progress = completed / total * 100

        print(f"Progress: {completed}/{total} batches ({progress:.1f}%)")

        if completed >= total:
            print("Processing complete!")
            break
    else:
        print("Processing not started or already complete")
        break

    time.sleep(30)  # Check every 30 seconds
```

## Important Notes

### ✅ DO:
- Use the **same `output_dir`** when resuming
- Keep the checkpoint file in place until processing completes
- Use different output directories for different CSV files
- Check logs to confirm resume is working

### ❌ DON'T:
- Don't change `batch_size` between runs (will cause mismatch)
- Don't change `output_dir` (checkpoint won't be found)
- Don't manually edit the checkpoint file
- Don't delete individual batch output folders

### Limitations

1. **Batch size must remain the same**: If you change `batch_size`, the checkpoint becomes invalid
2. **Output directory must be the same**: Checkpoint is tied to the output directory
3. **No parallel processing**: Checkpointing assumes sequential batch processing
4. **Memory overhead**: Checkpoint file grows with number of batches (minimal for most use cases)

## Performance Impact

Checkpointing has minimal performance impact:

- **Time overhead**: ~10-50ms per batch (JSON write)
- **Space overhead**: ~1-5KB per batch (depends on result size)
- **Example**: For 100 batches, total overhead is ~1-5 seconds and ~500KB

For most use cases, this is negligible compared to batch processing time (minutes to hours).

## Troubleshooting

### Checkpoint not loading

**Issue**: Running again, but it starts from batch 1 instead of resuming.

**Solutions**:
1. Check that `output_dir` is exactly the same
2. Verify checkpoint file exists: `ls {output_dir}/batch_checkpoint.json`
3. Check logs for "Checkpoint loaded" message
4. Ensure checkpointing is enabled (default)

### Invalid checkpoint

**Issue**: Error loading checkpoint or unexpected behavior.

**Solutions**:
1. Delete checkpoint and start fresh: `rm {output_dir}/batch_checkpoint.json`
2. Check checkpoint file is valid JSON: `cat {output_dir}/batch_checkpoint.json | python -m json.tool`
3. Ensure batch_size matches the checkpoint

### Checkpoint not deleted after completion

**Issue**: Processing completed, but checkpoint file still exists.

**Solutions**:
1. Manually delete: `rm {output_dir}/batch_checkpoint.json`
2. Check if there were errors (checkpoint is kept if status is "completed_with_errors")
3. Review logs for checkpoint deletion failures

## API Examples

### Python Requests

```python
import requests

response = requests.post(
    "http://localhost:8000/api/pipeline/run-csv-batch",
    json={
        "input_path": ".data/large_file.csv",
        "batch_size": 100,
        "output_path": "./output/my_batches"
    }
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Completed: {result['execution_summary']['batches_processed']} batches")

# If interrupted, run the SAME request to resume
```

### cURL

```bash
# First run
curl -X POST http://localhost:8000/api/pipeline/run-csv-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": ".data/large_file.csv",
    "batch_size": 100,
    "output_path": "./output/my_batches"
  }'

# If interrupted, run SAME command to resume
curl -X POST http://localhost:8000/api/pipeline/run-csv-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": ".data/large_file.csv",
    "batch_size": 100,
    "output_path": "./output/my_batches"
  }'
```

### JavaScript/TypeScript

```typescript
async function processCsvWithResume() {
  const config = {
    input_path: '.data/large_file.csv',
    batch_size: 100,
    output_path: './output/my_batches'
  };

  try {
    const response = await fetch('http://localhost:8000/api/pipeline/run-csv-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });

    const result = await response.json();
    console.log(`Completed: ${result.execution_summary.batches_processed} batches`);
  } catch (error) {
    console.error('Error:', error);
    console.log('Run again with same config to resume');
  }
}

// First run
await processCsvWithResume();

// If interrupted, call again to resume
await processCsvWithResume();
```

## See Also

- [CSV Batch API Guide](CSV_BATCH_API_GUIDE.md) - Main API documentation
- [VN30 CSV Pipeline README](../examples/VN30_CSV_PIPELINE_README.md) - Example use case
- [Resume Example Script](../examples/resume_csv_batch_example.py) - Working code examples
