"""
Basic example of using the KAG-LangGraph pipeline.

This example demonstrates how to run a simple knowledge graph extraction
pipeline on a document or directory of documents.
"""

import os
import sys
import logging
from pathlib import Path

# Add the package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graphs.pipeline import LangGraphExecutor, PipelineWorkflow
from knowledge_graphs.pipeline.config import load_config, create_default_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_basic_example():
    """Run basic pipeline example."""
    
    print("🚀 KAG-LangGraph Basic Pipeline Example")
    print("=" * 50)
    
    # Method 1: Using default configuration
    print("\n📋 Method 1: Using default configuration")
    
    try:
        # Create default configuration
        config = create_default_config()
        
        # Set up API key if available
        if "OPENAI_API_KEY" in os.environ:
            config["pipeline"]["components"]["extractor"]["config"]["api_key"] = os.environ["OPENAI_API_KEY"]
        else:
            print("⚠️  OPENAI_API_KEY not found. Using mock configuration.")
            # Use regex extractor instead for demo
            config["pipeline"]["components"]["extractor"] = {
                "type": "regex_extractor",
                "enabled": True,
                "config": {
                    "patterns": {
                        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                        "phone": r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
                    }
                }
            }
        
        # Create a simple test document
        test_doc_path = "./test_document.txt"
        with open(test_doc_path, 'w') as f:
            f.write("""
            John Doe is a software engineer at Tech Corp located in San Francisco.
            He can be reached at john.doe@techcorp.com or by phone at (555) 123-4567.
            
            Tech Corp is a technology company that develops innovative software solutions.
            The company was founded in 2010 and has grown to over 500 employees.
            
            Mary Johnson is the CEO of Tech Corp and previously worked at Big Tech Inc.
            She has a background in computer science and business administration.
            """)
        
        print(f"📄 Created test document: {test_doc_path}")
        
        # Create and run pipeline
        workflow = PipelineWorkflow(config=config)
        
        print("🔄 Running pipeline...")
        results = workflow.run_pipeline(test_doc_path)
        
        print("✅ Pipeline completed successfully!")
        print(f"📊 Results: {results['execution_summary']}")
        print(f"📝 Output saved to: {results.get('output_path', 'N/A')}")
        
        # Clean up
        os.remove(test_doc_path)
        
    except Exception as e:
        logger.error(f"Error in Method 1: {e}")
        print(f"❌ Error: {e}")


def run_config_file_example():
    """Run example using configuration file."""
    
    print("\n📋 Method 2: Using configuration file")
    
    try:
        config_path = Path(__file__).parent / "config.yaml"
        
        if not config_path.exists():
            print(f"⚠️  Configuration file not found: {config_path}")
            return
        
        # Load configuration from file
        workflow = PipelineWorkflow(config_path=str(config_path))
        
        # Create test document
        test_doc_path = "./test_document_2.txt"
        with open(test_doc_path, 'w') as f:
            f.write("""
            Alice Smith is a data scientist working at DataCorp in New York.
            Contact: alice.smith@datacorp.com, phone: (212) 555-0123.
            
            DataCorp specializes in big data analytics and machine learning.
            The company partners with universities for research initiatives.
            """)
        
        print(f"📄 Created test document: {test_doc_path}")
        
        # Run pipeline
        print("🔄 Running pipeline with config file...")
        results = workflow.run_pipeline(test_doc_path)
        
        print("✅ Pipeline completed successfully!")
        print(f"📊 Results: {results['execution_summary']}")
        print(f"📝 Output saved to: {results.get('output_path', 'N/A')}")
        
        # Clean up
        os.remove(test_doc_path)
        
    except Exception as e:
        logger.error(f"Error in Method 2: {e}")
        print(f"❌ Error: {e}")


def run_streaming_example():
    """Run example with streaming output."""
    
    print("\n📋 Method 3: Streaming pipeline execution")
    
    try:
        # Use simple configuration for streaming demo
        config = create_default_config()
        
        # Use regex extractor for reliable demo
        config["pipeline"]["components"]["extractor"] = {
            "type": "regex_extractor",
            "enabled": True,
            "config": {
                "patterns": {
                    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    "url": r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?'
                }
            }
        }
        
        # Create test document
        test_doc_path = "./test_streaming.txt"
        with open(test_doc_path, 'w') as f:
            f.write("""
            Visit our website at https://example.com for more information.
            Contact us at info@example.com or support@example.com.
            
            Our blog is available at https://blog.example.com with tutorials
            and technical articles. Follow us on social media for updates.
            """)
        
        print(f"📄 Created test document: {test_doc_path}")
        
        # Create workflow and stream execution
        workflow = PipelineWorkflow(config=config)
        
        print("🔄 Streaming pipeline execution...")
        for update in workflow.stream_pipeline(test_doc_path):
            component = update.get("current_component", "unknown")
            progress = update.get("progress", 0.0)
            status = update.get("status", "unknown")
            
            print(f"   📈 {component}: {status} ({progress:.1%} complete)")
        
        print("✅ Streaming pipeline completed!")
        
        # Clean up
        os.remove(test_doc_path)
        
    except Exception as e:
        logger.error(f"Error in Method 3: {e}")
        print(f"❌ Error: {e}")


async def run_async_example():
    """Run example asynchronously."""
    
    print("\n📋 Method 4: Asynchronous pipeline execution")
    
    try:
        config = create_default_config()
        
        # Use keyword extractor for demo
        config["pipeline"]["components"]["extractor"] = {
            "type": "keyword_extractor",
            "enabled": True,
            "config": {
                "keywords": {
                    "Person": ["John", "Jane", "Alice", "Bob"],
                    "Company": ["Tech Corp", "Data Inc", "AI Systems"],
                    "Technology": ["Python", "machine learning", "AI", "data science"]
                },
                "case_sensitive": False,
                "word_boundaries": True
            }
        }
        
        # Create test document
        test_doc_path = "./test_async.txt"
        with open(test_doc_path, 'w') as f:
            f.write("""
            John is a Python developer working on machine learning projects.
            Alice leads the AI team at Tech Corp, focusing on data science.
            The company uses advanced AI systems for automation.
            """)
        
        print(f"📄 Created test document: {test_doc_path}")
        
        # Run async pipeline
        workflow = PipelineWorkflow(config=config)
        
        print("🔄 Running async pipeline...")
        results = await workflow.arun_pipeline(test_doc_path)
        
        print("✅ Async pipeline completed!")
        print(f"📊 Results: {results['execution_summary']}")
        
        # Clean up
        os.remove(test_doc_path)
        
    except Exception as e:
        logger.error(f"Error in Method 4: {e}")
        print(f"❌ Error: {e}")


def main():
    """Run all examples."""
    
    # Ensure output directory exists
    os.makedirs("./output", exist_ok=True)
    
    # Run synchronous examples
    run_basic_example()
    run_config_file_example()
    run_streaming_example()
    
    # Run async example
    import asyncio
    asyncio.run(run_async_example())
    
    print("\n🎉 All examples completed!")
    print("\n📁 Check the './output' directory for generated knowledge graphs.")


if __name__ == "__main__":
    main()