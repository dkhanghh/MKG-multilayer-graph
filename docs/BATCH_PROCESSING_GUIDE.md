# Batch Processing with Config File Guide

This guide shows you how to use the server's batch processing functionality with custom configuration files.

---

## 📋 Overview

The server provides a `/pipeline/run-batch` endpoint that processes directories of files in batches, preventing memory issues when dealing with large datasets.

---

## 🚀 Quick Start

### 1. Start the Server

```bash
# Start with default config
python run_server.py

# Or with custom config
PIPELINE_CONFIG_PATH=configs/financebench_pipeline.yaml python run_server.py
```

The server will run on `http://localhost:8000`

---

## 📝 Method 1: Using Config File Path (Recommended)

### Step 1: Prepare Your Config File

Your config file should be in YAML format (like `configs/financebench_pipeline.yaml`):

```yaml
pipeline:
  name: "financebench_extraction_pipeline"

  components:
    scanner:
      type: "file_scanner"
      enabled: true
      config:
        input_paths:
          - "./data/financebench"
        file_patterns:
          - "*.txt"
        recursive: false
        max_files: 100

    reader:
      type: "financebench_reader"
      enabled: true
      config:
        encoding: "utf-8"

    extractor:
      type: "llm_extractor"
      enabled: true
      config:
        llm_provider: "openai"
        model: "gpt-4"
        api_key: "${OPENAI_API_KEY}"

    writer:
      type: "neo4j_writer"
      enabled: true
      config:
        uri: "${NEO4J_URI}"
        username: "${NEO4J_USERNAME}"
        password: "${NEO4J_PASSWORD}"
        database: "financebench"
```

### Step 2: Load Config in Python

```python
import yaml
import requests

# Load config from YAML file
def load_config(config_path: str):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Load your config
config = load_config('configs/financebench_pipeline.yaml')

# Make batch processing request
response = requests.post(
    'http://localhost:8000/pipeline/run-batch',
    json={
        'input_path': './data/financebench',
        'config': config,  # Pass the loaded config
        'batch_size': 10,
        'output_path': './output/financebench_results'
    }
)

print(response.json())
```

### Step 3: Using curl

```bash
# First, convert YAML to JSON (you can use yq or python)
python -c "
import yaml
import json
with open('configs/financebench_pipeline.yaml') as f:
    config = yaml.safe_load(f)
with open('/tmp/config.json', 'w') as f:
    json.dump(config, f)
"

# Then send request with config
curl -X POST http://localhost:8000/pipeline/run-batch \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "./data/financebench",
    "config": '$(cat /tmp/config.json)',
    "batch_size": 10,
    "output_path": "./output/results"
  }'
```

---

## 📝 Method 2: Using Default Config

If you don't provide a config, the server uses the config loaded at startup:

```python
import requests

response = requests.post(
    'http://localhost:8000/pipeline/run-batch',
    json={
        'input_path': './data/financebench',
        'batch_size': 10,
        'output_path': './output/results'
    }
)

print(response.json())
```

---

## 🔧 Complete Python Example

```python
#!/usr/bin/env python3
"""
Batch process FinanceBench data with custom config
"""
import yaml
import requests
import os
from pathlib import Path

def load_yaml_config(config_path: str):
    """Load YAML config and resolve environment variables."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Resolve environment variables
    return resolve_env_vars(config)

def resolve_env_vars(obj):
    """Recursively resolve ${VAR_NAME} in config."""
    if isinstance(obj, dict):
        return {k: resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_env_vars(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
        var_name = obj[2:-1]
        return os.getenv(var_name, obj)
    return obj

def run_batch_processing(
    input_path: str,
    config_path: str,
    batch_size: int = 10,
    output_path: str = None
):
    """
    Run batch processing with custom config.

    Args:
        input_path: Directory containing files to process
        config_path: Path to YAML config file
        batch_size: Number of files per batch
        output_path: Where to save results
    """
    # Load config
    print(f"Loading config from {config_path}...")
    config = load_yaml_config(config_path)

    # Prepare request
    request_data = {
        'input_path': input_path,
        'config': config,
        'batch_size': batch_size
    }

    if output_path:
        request_data['output_path'] = output_path

    # Send request
    print(f"Starting batch processing...")
    print(f"  Input: {input_path}")
    print(f"  Batch size: {batch_size}")
    print(f"  Output: {output_path or 'default'}")

    response = requests.post(
        'http://localhost:8000/pipeline/run-batch',
        json=request_data,
        timeout=3600  # 1 hour timeout
    )

    # Check response
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Batch processing completed!")
        print(f"Pipeline ID: {result['pipeline_id']}")
        print(f"Status: {result['status']}")
        print(f"Processed: {result.get('metrics', {}).get('files_processed', 0)} files")
        print(f"Errors: {len(result.get('errors', []))}")

        if result.get('errors'):
            print("\nErrors:")
            for error in result['errors'][:5]:
                print(f"  - {error}")

        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    # Example usage
    result = run_batch_processing(
        input_path='./data/financebench',
        config_path='configs/financebench_pipeline.yaml',
        batch_size=10,
        output_path='./output/financebench_batch'
    )
```

---

## 📊 Batch Processing Parameters

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_path` | string | ✅ Yes | - | Directory containing files to process |
| `config` | object | ❌ No | DEFAULT_CONFIG | Custom pipeline configuration |
| `batch_size` | integer | ❌ No | 10 | Files per batch (1-100) |
| `output_path` | string | ❌ No | from config | Custom output directory |

### Response Format

```json
{
  "pipeline_id": "pipeline_20250118_123456",
  "status": "completed",
  "input_path": "./data/financebench",
  "output_path": "./output/results",
  "metrics": {
    "files_processed": 50,
    "total_entities": 1234,
    "total_relationships": 5678,
    "processing_time": 120.5
  },
  "errors": [],
  "execution_summary": {
    "batches": 5,
    "files_per_batch": 10,
    "successful_files": 50,
    "failed_files": 0
  },
  "timestamp": "2025-01-18T12:34:56.789Z"
}
```

---

## 🎯 Use Cases

### 1. Process FinanceBench Dataset

```python
run_batch_processing(
    input_path='./data/financebench',
    config_path='configs/financebench_pipeline.yaml',
    batch_size=10
)
```

### 2. Large Dataset with Custom Batch Size

```python
run_batch_processing(
    input_path='./data/large_dataset',
    config_path='configs/custom_pipeline.yaml',
    batch_size=5,  # Smaller batches for large files
    output_path='./output/large_results'
)
```

### 3. Test Run with Small Batch

```python
# Override max_files in config for testing
config = load_yaml_config('configs/financebench_pipeline.yaml')
config['pipeline']['components']['scanner']['config']['max_files'] = 5

response = requests.post(
    'http://localhost:8000/pipeline/run-batch',
    json={
        'input_path': './data/financebench',
        'config': config,
        'batch_size': 2
    }
)
```

---

## 🔍 Monitoring Progress

### Check Server Logs

```bash
# Server outputs progress in console
tail -f server.log
```

### Get Pipeline Status (if tracking endpoint exists)

```python
response = requests.get(
    f'http://localhost:8000/pipeline/status/{pipeline_id}'
)
print(response.json())
```

---

## ⚠️ Important Notes

1. **Environment Variables**: Make sure all `${VAR_NAME}` in config are set:
   ```bash
   export OPENAI_API_KEY=your-key
   export NEO4J_URI=bolt://localhost:7687
   export NEO4J_USERNAME=neo4j
   export NEO4J_PASSWORD=your-password
   ```

2. **Memory Management**: Adjust `batch_size` based on:
   - File sizes (larger files = smaller batch)
   - Available RAM
   - LLM rate limits

3. **Timeouts**: Large batches may take time, adjust request timeout:
   ```python
   requests.post(..., timeout=7200)  # 2 hours
   ```

4. **Server Config**: The server loads config at startup via `PIPELINE_CONFIG_PATH`:
   ```bash
   PIPELINE_CONFIG_PATH=configs/my_config.yaml python run_server.py
   ```

---

## 🔗 API Documentation

Full API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 💡 Tips

1. **Test First**: Use `max_files: 1` in config for initial testing
2. **Monitor Neo4j**: Check Neo4j memory usage during batch processing
3. **Parallel Processing**: Run multiple server instances for different datasets
4. **Error Handling**: Check `errors` array in response for failed files

---

## 📚 Related Documentation

- [Server README](../server/README.md)
- [Pipeline Configuration](../configs/README.md)
- [API Reference](../server/README.md#api-reference)
