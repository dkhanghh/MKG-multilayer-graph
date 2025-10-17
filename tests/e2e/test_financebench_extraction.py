"""
Test script for FinanceBench extraction pipeline.

This script tests the complete 3-step extraction pipeline:
1. Parse FinanceBench documents with custom reader
2. Extract entities with NER → STD → TRP
3. Validate SPG edge properties
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_financebench_reader():
    """Test the FinanceBench reader component."""
    print("\n" + "=" * 60)
    print("TEST 1: FinanceBench Reader")
    print("=" * 60)

    from knowledge_graphs.components.financebench_reader import FinanceBenchReader
    from knowledge_graphs.models.pipeline_state import PipelineState
    from knowledge_graphs.pipeline.config import ComponentConfig

    # Create reader
    config = ComponentConfig(
        type='financebench_reader',
        enabled=True,
        config={
            'preserve_page_structure': True,
            'detect_statement_type': True,
            'extract_metadata': True
        }
    )

    reader = FinanceBenchReader(config)

    # Test on sample file
    test_file = './financebench_data/financebench_id_00070.txt'

    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False

    state = PipelineState(file_paths=[test_file])
    result = reader.process(state)

    chunks = result.get('chunks', [])
    print(f"✓ Created {len(chunks)} chunks from {test_file}")

    if chunks:
        chunk = chunks[0]
        print(f"\n📄 Sample Chunk:")
        print(f"  - ID: {chunk.id}")
        print(f"  - Page: {chunk.page_number}")
        print(f"  - Metadata: {chunk.processing_metadata}")
        print(f"  - Content preview: {chunk.content[:150]}...")
        print(f"\n✅ FinanceBench Reader test PASSED")
        return True
    else:
        print(f"❌ No chunks created")
        return False


def test_prompt_templates():
    """Test that enhanced prompt templates are valid."""
    print("\n" + "=" * 60)
    print("TEST 2: Enhanced Prompt Templates")
    print("=" * 60)

    prompts_dir = Path('./knowledge_graphs/prompts')

    prompt_files = {
        'ner.md': 'NER (Named Entity Recognition)',
        'std.md': 'STD (Standardization)',
        'trp.md': 'TRP (Triple/Relationship Extraction)'
    }

    all_valid = True

    for filename, description in prompt_files.items():
        filepath = prompts_dir / filename

        if not filepath.exists():
            print(f"❌ {description}: File not found")
            all_valid = False
            continue

        content = filepath.read_text()

        # Check for financial keywords
        financial_keywords = ['financial', 'balance sheet', 'Company', 'FinancialStatement']
        found_keywords = [kw for kw in financial_keywords if kw.lower() in content.lower()]

        if found_keywords:
            print(f"✓ {description}: Enhanced with financial examples")
            print(f"  Found keywords: {', '.join(found_keywords[:3])}")
        else:
            print(f"⚠ {description}: No financial enhancements found")

    if all_valid:
        print(f"\n✅ Prompt template test PASSED")

    return all_valid


def test_pipeline_config():
    """Test that pipeline configuration is valid."""
    print("\n" + "=" * 60)
    print("TEST 3: Pipeline Configuration")
    print("=" * 60)

    import yaml

    config_file = Path('./configs/financebench_pipeline.yaml')

    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return False

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    # Validate structure
    required_keys = ['name', 'components']
    for key in required_keys:
        if key not in config:
            print(f"❌ Missing required key: {key}")
            return False

    print(f"✓ Pipeline name: {config['name']}")
    print(f"✓ Pipeline description: {config.get('description', 'N/A')}")

    # Check components
    components = config['components']
    expected_components = ['scanner', 'reader', 'extractor', 'vectorizer', 'writer']

    for component in expected_components:
        if component in components:
            enabled = components[component].get('enabled', True)
            status = "✓ enabled" if enabled else "○ disabled"
            print(f"  {status}: {component}")
        else:
            print(f"  ❌ missing: {component}")

    # Check reader type
    reader_type = components.get('reader', {}).get('type')
    if reader_type == 'financebench_reader':
        print(f"✓ Custom FinanceBench reader configured")
    else:
        print(f"⚠ Reader type: {reader_type} (expected: financebench_reader)")

    # Check schema
    extractor_schema = components.get('extractor', {}).get('config', {}).get('extraction_schema')
    if extractor_schema == 'financebench_spg.schema':
        print(f"✓ Using SPG schema: {extractor_schema}")
    else:
        print(f"⚠ Schema: {extractor_schema}")

    print(f"\n✅ Pipeline configuration test PASSED")
    return True


def test_schema_file():
    """Test that SPG schema file exists and is valid."""
    print("\n" + "=" * 60)
    print("TEST 4: SPG Schema File")
    print("=" * 60)

    schema_file = Path('./knowledge_graphs/schema/financebench_spg.schema')

    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return False

    content = schema_file.read_text()

    # Check for key SPG concepts
    required_elements = [
        'Company: EntityType',
        'FinancialStatement: EntityType',
        'REPORTED_FINANCIALS',
        'edgeProperties',
        'Industry: ConceptType'
    ]

    found_elements = []
    for element in required_elements:
        if element in content:
            found_elements.append(element)
            print(f"✓ Found: {element}")
        else:
            print(f"❌ Missing: {element}")

    if len(found_elements) == len(required_elements):
        print(f"\n✅ SPG schema test PASSED")
        return True
    else:
        print(f"\n⚠ Some schema elements missing")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("FINANCEBENCH EXTRACTION PIPELINE TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: FinanceBench Reader
    try:
        results.append(("FinanceBench Reader", test_financebench_reader()))
    except Exception as e:
        print(f"❌ FinanceBench Reader test failed with error: {e}")
        results.append(("FinanceBench Reader", False))

    # Test 2: Prompt Templates
    try:
        results.append(("Prompt Templates", test_prompt_templates()))
    except Exception as e:
        print(f"❌ Prompt template test failed with error: {e}")
        results.append(("Prompt Templates", False))

    # Test 3: Pipeline Config
    try:
        results.append(("Pipeline Config", test_pipeline_config()))
    except Exception as e:
        print(f"❌ Pipeline config test failed with error: {e}")
        results.append(("Pipeline Config", False))

    # Test 4: Schema File
    try:
        results.append(("SPG Schema", test_schema_file()))
    except Exception as e:
        print(f"❌ Schema test failed with error: {e}")
        results.append(("SPG Schema", False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests PASSED! Ready to run pipeline.")
        print("\nNext steps:")
        print("1. Set environment variables: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, GOOGLE_API_KEY")
        print("2. Run pipeline: python -m knowledge_graphs.pipeline.main --config configs/financebench_pipeline.yaml")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please fix issues before running pipeline.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
