# KAG-LangGraph Pipeline Server

This document describes how to use the FastAPI server for running KAG-LangGraph pipelines.

## Installation

First, install the required dependencies:

```bash
pip install fastapi uvicorn
# Or install all requirements
pip install -r requirements.txt
```

## Starting the Server

### Method 1: Direct execution
```bash
python sever.py
```

### Method 2: Using uvicorn directly
```bash
uvicorn sever:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: With environment variables
```bash
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8000
export SERVER_RELOAD=true
export LOG_LEVEL=info
python sever.py
```

## API Endpoints

### 1. Health Check
- **GET** `/health`
- Returns server health status

### 2. Get Default Configuration
- **GET** `/pipeline/config`
- Returns the default pipeline configuration

### 3. List Available Components
- **GET** `/pipeline/components`
- Returns available pipeline components

### 4. Run Pipeline (Synchronous)
- **POST** `/pipeline/run`
- Body:
```json
{
    "input_path": "/path/to/your/document.txt",
    "config": {
        "pipeline": {
            "components": {
                "scanner": {"type": "file_scanner", "enabled": true},
                "reader": {"type": "txt_reader", "enabled": true}
            }
        }
    },
    "output_path": "/path/to/output.json"
}
```

### 5. Run Pipeline (Asynchronous)
- **POST** `/pipeline/run-async`
- Same body format as synchronous version

### 6. Stream Pipeline Execution
- **POST** `/pipeline/stream`
- Returns Server-Sent Events (SSE) stream with real-time updates
- Same body format as other run endpoints

### 7. Upload File and Run Pipeline
- **POST** `/pipeline/upload-and-run`
- Form data with file upload and optional config JSON string

## Usage Examples

### Using curl

#### Basic pipeline run:
```bash
curl -X POST "http://localhost:8000/pipeline/run" \
     -H "Content-Type: application/json" \
     -d '{
       "input_path": "./test_document.txt"
     }'
```

#### With custom configuration:
```bash
curl -X POST "http://localhost:8000/pipeline/run" \
     -H "Content-Type: application/json" \
     -d '{
       "input_path": "./test_document.txt",
       "config": {
         "pipeline": {
           "components": {
             "scanner": {"type": "file_scanner", "enabled": true},
             "reader": {"type": "txt_reader", "enabled": true},
             "writer": {
               "type": "json_writer",
               "enabled": true,
               "config": {"output_path": "./custom_output.json"}
             }
           }
         }
       }
     }'
```

#### File upload:
```bash
curl -X POST "http://localhost:8000/pipeline/upload-and-run" \
     -F "file=@./test_document.txt"
```

### Using Python requests

```python
import requests
import json

# Basic pipeline run
response = requests.post(
    "http://localhost:8000/pipeline/run",
    json={
        "input_path": "./test_document.txt"
    }
)
result = response.json()
print(f"Pipeline ID: {result['pipeline_id']}")
print(f"Status: {result['status']}")

# File upload
with open("test_document.txt", "rb") as f:
    response = requests.post(
        "http://localhost:8000/pipeline/upload-and-run",
        files={"file": f}
    )
result = response.json()
```

### Streaming Example

```python
import requests
import json

response = requests.post(
    "http://localhost:8000/pipeline/stream",
    json={"input_path": "./test_document.txt"},
    stream=True
)

for line in response.iter_lines():
    if line:
        # Parse SSE data
        if line.startswith(b'data: '):
            data = json.loads(line[6:])  # Remove 'data: ' prefix
            print(f"Update: {data}")
```

## Interactive API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Configuration

The server uses the following environment variables:

- `SERVER_HOST`: Host to bind to (default: 0.0.0.0)
- `SERVER_PORT`: Port to listen on (default: 8000)
- `SERVER_RELOAD`: Enable auto-reload for development (default: false)
- `LOG_LEVEL`: Logging level (default: info)

## Error Handling

The API returns standard HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid input)
- `500`: Internal Server Error

Error responses include details in the response body:
```json
{
    "detail": "Error description here"
}
```

## Notes

- The server includes CORS middleware configured to allow all origins (configure appropriately for production)
- Temporary files from uploads are automatically cleaned up
- The server maintains backward compatibility with the original `langgraph dev` setup
- All endpoints support both custom configurations and default settings
