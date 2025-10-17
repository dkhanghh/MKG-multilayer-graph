# LangSmith Integration Guide

## Overview

The KAG-LangGraph server now includes comprehensive LangSmith tracing integration for monitoring, debugging, and analyzing pipeline executions. This integration provides detailed visibility into pipeline performance, component behavior, and execution flows.

## ✅ Integration Status

### Features Implemented:
- ✅ **Automatic Tracing**: All pipeline endpoints are automatically traced
- ✅ **Execution Metadata**: Detailed context for each pipeline run
- ✅ **Error Tracking**: Comprehensive error logging and tracing
- ✅ **Performance Monitoring**: Execution time and resource usage tracking
- ✅ **Multi-mode Support**: Sync, async, streaming, and upload executions
- ✅ **Graceful Fallback**: Server works with or without LangSmith

### Traced Endpoints:
1. **`/pipeline/run`** → `pipeline_run_sync`
2. **`/pipeline/run-async`** → `pipeline_run_async`
3. **`/pipeline/stream`** → `pipeline_stream`
4. **`/pipeline/upload-and-run`** → `pipeline_upload_and_run`

## 🚀 Setup Instructions

### 1. Install Dependencies

The required packages are already included in `requirements.txt` and `setup.py`:

```bash
# Install via requirements
uv pip install -r requirements.txt

# Or install specific packages
uv pip install langsmith>=0.1.0 langchain>=0.1.0
```

### 2. Configure Environment Variables

Set the following environment variables to enable LangSmith tracing:

```bash
# Required: Your LangSmith API key
export LANGSMITH_API_KEY="your-langsmith-api-key-here"

# Optional: Custom project name (default: kag-langgraph-server)
export LANGSMITH_PROJECT="my-kag-project"

# Optional: Custom endpoint (default: https://api.smith.langchain.com)
export LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
```

### 3. Get Your LangSmith API Key

1. Go to [LangSmith](https://smith.langchain.com/)
2. Sign up or log in to your account
3. Navigate to Settings → API Keys
4. Create a new API key
5. Copy the key and set it as `LANGSMITH_API_KEY`

## 📊 Usage Examples

### Basic Usage

Once configured, tracing happens automatically:

```bash
# Start the server (tracing will be enabled automatically)
uv run python sever.py

# Run any pipeline - it will be automatically traced
curl -X POST "http://localhost:8000/pipeline/run" \
  -H "Content-Type: application/json" \
  -d '{"input_path": "document.pdf"}'
```

### Environment Configuration Examples

```bash
# Minimal setup
export LANGSMITH_API_KEY="lsv2_pt_..."
uv run python sever.py

# Custom project setup
export LANGSMITH_API_KEY="lsv2_pt_..."
export LANGSMITH_PROJECT="research-pipeline"
uv run python sever.py

# Development setup with custom endpoint
export LANGSMITH_API_KEY="lsv2_pt_..."
export LANGSMITH_PROJECT="dev-kag-pipeline"
export LANGSMITH_ENDPOINT="https://dev.smith.langchain.com"
uv run python sever.py
```

## 🔍 Trace Information

### Metadata Captured

Each trace includes:

**Input Data:**
- `input_path`: Source document path
- `output_path`: Destination path (if specified)
- `has_custom_config`: Whether custom configuration was provided

**Execution Metadata:**
- `execution_mode`: sync/async/streaming/upload
- `server_version`: Server version information
- `timestamp`: Execution timestamp
- `pipeline_id`: Unique execution identifier

**Performance Data:**
- Execution duration
- Component processing times
- Memory usage patterns
- Error rates and types

### Trace Names and Structure

```
📊 LangSmith Project: kag-langgraph-server
├── 🔄 pipeline_run_sync
│   ├── Input: {input_path, output_path, config}
│   ├── Metadata: {execution_mode: "synchronous"}
│   └── Output: {pipeline_id, status, metrics}
├── ⚡ pipeline_run_async
│   ├── Input: {input_path, output_path, config}
│   ├── Metadata: {execution_mode: "asynchronous"}
│   └── Output: {pipeline_id, status, metrics}
├── 🌊 pipeline_stream
│   ├── Input: {input_path, output_path, config}
│   ├── Metadata: {execution_mode: "streaming"}
│   └── Output: {streaming_events, final_status}
└── 📤 pipeline_upload_and_run
    ├── Input: {file_info, config}
    ├── Metadata: {execution_mode: "upload"}
    └── Output: {pipeline_id, status, metrics}
```

## 🧪 Testing

### Run Integration Tests

```bash
# Test LangSmith integration
uv run python test_langsmith_integration.py
```

### Expected Test Output

```
======================================================================
LangSmith Integration Test Suite
======================================================================
Checking LangSmith configuration...
  LANGSMITH_API_KEY: ✓ Set
  LANGSMITH_PROJECT: ✓ Set (kag-langgraph-server)
  LANGSMITH_ENDPOINT: - Using default (https://api.smith.langchain.com)
✓ LangSmith configuration is complete

✓ Server is running

Testing traced pipeline execution...
  Testing synchronous execution...
    ✓ Sync execution successful (ID: abc-123)
  Testing asynchronous execution...
    ✓ Async execution successful (ID: def-456)
  Testing streaming execution...
    ✓ Streaming execution successful (5 events received)

Testing upload and run with tracing...
  ✓ Upload and run successful (ID: ghi-789)

Checking LangSmith traces...
  ✓ LangSmith is configured
  📊 View traces at: https://smith.langchain.com/
  📁 Project: kag-langgraph-server
  🔍 Look for traces with names:
    - pipeline_run_sync
    - pipeline_run_async
    - pipeline_stream
    - pipeline_upload_and_run

======================================================================
Results: 2/2 tests passed
======================================================================
🎉 All tests passed! LangSmith tracing is working.

📊 Check your LangSmith dashboard to see the traces:
   https://smith.langchain.com/
```

## 📈 Monitoring and Analysis

### LangSmith Dashboard

After running pipelines, visit your LangSmith dashboard to:

1. **View Execution Traces**: See detailed execution flows
2. **Analyze Performance**: Monitor execution times and bottlenecks
3. **Debug Issues**: Investigate errors and failures
4. **Track Usage**: Monitor API usage and patterns
5. **Compare Runs**: Analyze different configurations and inputs

### Key Metrics to Monitor

- **Execution Time**: Total pipeline duration
- **Component Performance**: Individual component processing times
- **Error Rates**: Success/failure ratios
- **Throughput**: Documents processed per hour
- **Resource Usage**: Memory and CPU utilization patterns

## 🔧 Configuration Options

### Server-Level Configuration

The server automatically detects and configures LangSmith based on environment variables:

```python
# Automatic configuration in sever.py
langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
langsmith_project = os.getenv("LANGSMITH_PROJECT", "kag-langgraph-server")
langsmith_endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
```

### Custom Project Names

Use different project names for different environments:

```bash
# Production
export LANGSMITH_PROJECT="kag-production"

# Staging
export LANGSMITH_PROJECT="kag-staging"

# Development
export LANGSMITH_PROJECT="kag-development"
```

## 🚨 Troubleshooting

### Common Issues

**1. Tracing Not Working**
```bash
# Check if API key is set
echo $LANGSMITH_API_KEY

# Check server logs for LangSmith initialization
uv run python sever.py | grep -i langsmith
```

**2. Invalid API Key**
```
ERROR: Failed to initialize LangSmith: Invalid API key
```
- Verify your API key is correct
- Check if the key has proper permissions

**3. Network Issues**
```
ERROR: Failed to initialize LangSmith: Connection timeout
```
- Check internet connectivity
- Verify LANGSMITH_ENDPOINT is accessible

**4. Missing Dependencies**
```
WARNING: LangSmith not available: No module named 'langsmith'
```
- Install missing packages: `uv pip install langsmith langchain`

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_DEBUG=true
uv run python sever.py
```

## 🔒 Security Considerations

### API Key Security

- **Never commit API keys** to version control
- Use environment variables or secure secret management
- Rotate API keys regularly
- Use different keys for different environments

### Data Privacy

- LangSmith traces may contain sensitive data from your documents
- Review LangSmith's privacy policy and data handling practices
- Consider using on-premises solutions for sensitive data

## 📚 Additional Resources

- **LangSmith Documentation**: https://docs.smith.langchain.com/
- **LangChain Tracing Guide**: https://python.langchain.com/docs/langsmith/
- **API Reference**: https://api.smith.langchain.com/docs
- **Python SDK**: https://github.com/langchain-ai/langsmith-sdk

## ✅ Summary

LangSmith integration is now fully implemented in the KAG-LangGraph server:

- ✅ **Automatic tracing** for all pipeline endpoints
- ✅ **Comprehensive metadata** capture
- ✅ **Error tracking** and performance monitoring
- ✅ **Easy configuration** via environment variables
- ✅ **Graceful fallback** when not configured
- ✅ **Full test coverage** with integration tests

Set your `LANGSMITH_API_KEY` and start monitoring your pipeline executions today!
