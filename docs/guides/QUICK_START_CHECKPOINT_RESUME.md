# Quick Start: Checkpoint/Resume for CSV Batch Processing

## TL;DR

CSV batch processing now **automatically saves checkpoints** and can resume from where it left off if interrupted. Just run the same command again!

## Basic Usage

```python
from knowledge_graphs.pipeline.csv_batch_processor import process_csv_in_batches
from server.core.config import load_config

config = load_config()

# Process CSV in batches
results = process_csv_in_batches(
    csv_path=".data/your_file.csv",
    config=config,
    batch_size=100,
    output_dir="./output/my_batches"
)

# If interrupted, run the SAME command to resume!
```

## API Usage

```bash
# First run (may get interrupted)
curl -X POST http://localhost:8000/api/pipeline/run-csv-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": ".data/your_file.csv",
    "batch_size": 100,
    "output_path": "./output/my_batches"
  }'

# If interrupted, run SAME request to resume
curl -X POST http://localhost:8000/api/pipeline/run-csv-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": ".data/your_file.csv",
    "batch_size": 100,
    "output_path": "./output/my_batches"
  }'
```

## How It Works

1. ✅ **Automatic checkpoint** after each batch
2. ✅ **Automatic resume** when you run again
3. ✅ **Automatic cleanup** when complete
4. ✅ **No manual intervention** needed

## What Gets Saved

Checkpoint file: `{output_dir}/batch_checkpoint.json`

Contains:
- Completed batch results
- Aggregated metrics (nodes, edges, etc.)
- Progress information
- Error tracking

## Important Rules

### ✅ DO:
- Use the **same output_dir** when resuming
- Keep the checkpoint file until processing completes
- Check logs for "Checkpoint loaded" message

### ❌ DON'T:
- Don't change `batch_size` between runs
- Don't change `output_dir` between runs
- Don't delete the checkpoint file manually (unless you want to start fresh)

## Checking Progress

```python
import json
from pathlib import Path

checkpoint = Path("./output/my_batches/batch_checkpoint.json")

if checkpoint.exists():
    with open(checkpoint) as f:
        data = json.load(f)

    completed = data['completed_batches']
    total = data['total_batches']
    progress = completed / total * 100

    print(f"Progress: {completed}/{total} batches ({progress:.1f}%)")
```

## Starting Fresh

To ignore a checkpoint and start from scratch:

```bash
# Delete the checkpoint file
rm ./output/my_batches/batch_checkpoint.json

# Then run again - starts from batch 1
```

## Disabling Checkpoints

```python
results = process_csv_in_batches(
    csv_path=".data/your_file.csv",
    config=config,
    batch_size=100,
    output_dir="./output/my_batches",
    enable_checkpointing=False  # Disable checkpointing
)
```

## Examples

Run the example script:

```bash
python examples/resume_csv_batch_example.py
```

## Tests

Run the test suite:

```bash
python tests/test_checkpoint_resume.py
```

## Full Documentation

- **Detailed Guide**: [CSV_BATCH_RESUME_GUIDE.md](server/CSV_BATCH_RESUME_GUIDE.md)
- **API Documentation**: [CSV_BATCH_API_GUIDE.md](server/CSV_BATCH_API_GUIDE.md)
- **Implementation Summary**: [CHECKPOINT_IMPLEMENTATION_SUMMARY.md](CHECKPOINT_IMPLEMENTATION_SUMMARY.md)

## Troubleshooting

### Checkpoint not loading?
- Check that `output_dir` is exactly the same
- Verify checkpoint file exists: `ls {output_dir}/batch_checkpoint.json`
- Check logs for "Checkpoint loaded" message

### Want to start fresh?
- Delete checkpoint: `rm {output_dir}/batch_checkpoint.json`

### Multiple CSV files?
- Use different `output_dir` for each file
- Each gets independent checkpoint

## That's It!

Checkpointing works automatically. Just run your batch processing commands normally, and if they get interrupted, run them again to resume! 🚀
