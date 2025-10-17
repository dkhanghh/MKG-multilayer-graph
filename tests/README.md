# Test Suite

## Directory Structure

- `unit/` - Unit tests for individual components
- `integration/` - Integration tests for component interactions
- `e2e/` - End-to-end tests for full pipeline
- `component_tests/` - Specific component tests

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
pytest tests/component_tests/

# Run with coverage
pytest --cov=knowledge_graphs tests/
```

## Test Files

### End-to-End Tests
- `test_financebench_extraction.py` - FinanceBench pipeline test
- `test_batch_processing.py` - Batch processing test
- `test_hybrid_search.py` - Hybrid search test

### Component Tests
- Various component-specific tests
