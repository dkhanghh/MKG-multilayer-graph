# Pipeline Configuration Loading

## Overview

The server API endpoints now load pipeline configuration from a YAML file by default, instead of using a hardcoded configuration dictionary.

## Changes Made

### Modified Files

- **[server/api/routes/pipeline.py](api/routes/pipeline.py)**: Updated all endpoints to use `load_config()` instead of `DEFAULT_CONFIG.copy()`
- **[server/.env.example](.env.example)**: Added example environment configuration

### How It Works

The `load_config()` function (defined in [server/core/config.py](core/config.py)) follows this priority:

1. **Environment Variable**: If `CONFIG_FILE` environment variable is set, loads from that YAML file
2. **Function Parameter**: If a path is passed to `load_config(config_path)`, uses that file
3. **Default Fallback**: If neither is set, uses the hardcoded `DEFAULT_CONFIG` dictionary

## Usage

### Option 1: Using Environment Variable (Recommended)

Set the `CONFIG_FILE` environment variable to point to your YAML configuration:

```bash
# Using .env file
echo "CONFIG_FILE=examples/config_vn30_csv.yaml" >> server/.env

# Or export directly
export CONFIG_FILE=examples/config_vn30_csv.yaml

# Start the server
python -m uvicorn server.api.app:app --reload
```

### Option 2: Default Configuration

If no `CONFIG_FILE` is set, the server uses the default configuration from `server/core/config.py`:

```bash
# Start server without CONFIG_FILE set
python -m uvicorn server.api.app:app --reload
```

### Option 3: Per-Request Configuration

You can still override the configuration for individual API requests by passing a custom config in the request body:

```python
import requests

# Custom config for this request only
custom_config = {
    "pipeline": {
        "components": {
            "reader": {
                "type": "csv_reader",
                "config": {
                    "content_column": "content",
                    "metadata_columns": ["company_code", "year"]
                }
            }
        }
    }
}

response = requests.post(
    "http://localhost:8000/api/pipeline/run",
    json={
        "input_path": ".data/data_vn30_first_100.csv",
        "config": custom_config
    }
)
```

## Available Configuration Files

The project includes several pre-configured YAML files:

1. **[examples/config_vn30_csv.yaml](../examples/config_vn30_csv.yaml)** - For processing VN30 CSV financial reports
   - Uses CSV reader
   - Pre-computed embeddings
   - Configured for financial entity extraction

2. **[examples/config.yaml](../examples/config.yaml)** - Basic pipeline configuration
   - Standard document processing
   - PDF/TXT reader support

3. **[examples/config_with_templates.yaml](../examples/config_with_templates.yaml)** - Template-based extraction
   - Uses prompt templates
   - Schema-guided extraction

## Configuration Priority

When an API endpoint is called:

1. **Request Config** (highest priority): If `config` is provided in the request body
2. **Environment Variable**: If `CONFIG_FILE` is set
3. **Default Config** (lowest priority): Hardcoded in `server/core/config.py`

## Example: Using VN30 CSV Configuration

To process VN30 financial reports via the API:

```bash
# 1. Set the configuration
export CONFIG_FILE=examples/config_vn30_csv.yaml

# 2. Set your API key
export OPENAI_API_KEY=your-key-here

# 3. Start the server
python -m uvicorn server.api.app:app --reload

# 4. Make a request (in another terminal)
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": ".data/data_vn30_first_100.csv",
    "output_path": "./output/vn30_api_results"
  }'
```

## Benefits

✅ **Flexibility**: Change pipeline behavior without code changes
✅ **Environment-specific**: Different configs for dev/staging/prod
✅ **Maintainability**: Configuration separated from code
✅ **Reusability**: Share YAML configs across CLI and API
✅ **Backward Compatible**: Still supports inline config in requests

## Migration from Old Code

**Before:**
```python
config = request.config if request.config else DEFAULT_CONFIG.copy()
```

**After:**
```python
config = request.config if request.config else load_config()
```

This change allows the configuration to be loaded from a YAML file (via `CONFIG_FILE` env var) or fall back to the default config if no file is specified.

## Testing

Verify the configuration is loaded correctly:

```bash
# Test with environment variable
export CONFIG_FILE=examples/config_vn30_csv.yaml
python -m pytest tests/test_api_flow.py -v

# Test without environment variable (uses default)
unset CONFIG_FILE
python -m pytest tests/test_api_flow.py -v
```

## Troubleshooting

### Configuration file not found

```
FileNotFoundError: Configuration file not found: path/to/config.yaml
```

**Solution**: Verify the `CONFIG_FILE` path is correct and the file exists:
```bash
ls -la $CONFIG_FILE
```

### Invalid YAML syntax

```
yaml.scanner.ScannerError: ...
```

**Solution**: Validate your YAML file:
```bash
python -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))"
```

### Still using default config

If your changes to the YAML file aren't being picked up:

1. Verify the environment variable is set: `echo $CONFIG_FILE`
2. Restart the server to reload the configuration
3. Check that the YAML file path is relative to where you run the server

## See Also

- [VN30 CSV Pipeline README](../examples/VN30_CSV_PIPELINE_README.md) - Guide for CSV ingestion
- [Pipeline Configuration Schema](core/config.py) - Default configuration reference
- [Example Configurations](../examples/) - Pre-built config files
