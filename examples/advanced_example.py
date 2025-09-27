"""
Advanced example demonstrating KAG-LangGraph features.

This example shows more advanced pipeline configurations including:
- Directory scanning with multiple file types
- Semantic text splitting
- Custom entity and relation extraction
- Advanced vectorization
- Multiple output formats
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from typing import List

# Add the package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graphs.pipeline import PipelineWorkflow
from knowledge_graphs.pipeline.config import create_example_configs, save_config


def create_sample_documents(output_dir: Path) -> List[Path]:
    """Create sample documents for testing."""
    
    documents = []
    
    # Document 1: Company information
    doc1 = output_dir / "company_info.txt"
    doc1.write_text("""
    TechCorp Inc. is a leading technology company founded in 2010 by John Smith and Sarah Johnson.
    The company is headquartered in San Francisco, California, and has offices in New York and London.
    
    CEO: John Smith (john.smith@techcorp.com)
    CTO: Sarah Johnson (sarah.johnson@techcorp.com)
    CFO: Michael Brown (michael.brown@techcorp.com)
    
    TechCorp specializes in artificial intelligence and machine learning solutions.
    The company has partnerships with major universities including Stanford University and MIT.
    
    Key products:
    - AI Platform: Advanced machine learning infrastructure
    - DataViz Pro: Business intelligence and visualization tool
    - CloudSync: Enterprise data synchronization service
    
    Recent achievements:
    - Raised $50M in Series C funding in 2023
    - Launched AI Platform 2.0 with improved performance
    - Expanded team to over 200 employees worldwide
    """)
    documents.append(doc1)
    
    # Document 2: Research paper abstract
    doc2 = output_dir / "research_abstract.md"
    doc2.write_text("""
    # Deep Learning Advances in Natural Language Processing
    
    ## Abstract
    
    This paper presents recent advances in deep learning architectures for natural language processing tasks.
    Authors: Dr. Alice Chen (Stanford University), Prof. Robert Davis (MIT), Dr. Lisa Wang (CMU).
    
    ## Key Contributions
    
    1. **Transformer Architecture Enhancement**: We propose a novel attention mechanism that improves 
       performance on long-sequence tasks by 15%.
    
    2. **Multi-modal Integration**: Our approach combines text and image processing for better 
       understanding of document content.
    
    3. **Efficiency Improvements**: The new model reduces computational requirements by 30% while 
       maintaining accuracy.
    
    ## Experimental Results
    
    - Tested on datasets: GLUE, SuperGLUE, SQuAD 2.0
    - Performance improvements across all benchmarks
    - Particularly strong results on reading comprehension tasks
    
    ## Contact Information
    
    For questions about this research, contact:
    - Alice Chen: alice.chen@stanford.edu
    - Robert Davis: rdavis@mit.edu  
    - Lisa Wang: lwang@cmu.edu
    
    Research conducted at Stanford AI Lab in collaboration with MIT CSAIL and CMU Machine Learning Department.
    """)
    documents.append(doc2)
    
    # Document 3: News article
    doc3 = output_dir / "news_article.txt" 
    doc3.write_text("""
    BREAKING: TechCorp Announces Major AI Breakthrough
    
    San Francisco, CA - December 15, 2023
    
    TechCorp Inc. (NASDAQ: TECH) announced today a significant breakthrough in artificial intelligence
    that could revolutionize how machines understand human language.
    
    The announcement was made by CEO John Smith during the company's annual AI Summit, held at the
    Moscone Center in San Francisco. "This represents five years of intensive research by our team,"
    Smith said to an audience of over 1,000 technology leaders.
    
    Key Details:
    - New AI model achieves 95% accuracy on language understanding tasks
    - Technology will be integrated into existing TechCorp products in Q1 2024
    - Partnership announced with Google Cloud and Microsoft Azure for deployment
    
    The breakthrough was developed by TechCorp's AI Research Division, led by CTO Sarah Johnson.
    The team includes researchers from partnerships with Stanford University, MIT, and Carnegie Mellon.
    
    Industry Impact:
    "This could change everything we know about AI capabilities," said Dr. Michael Thompson,
    AI researcher at UC Berkeley. "TechCorp has consistently pushed the boundaries of what's possible."
    
    Stock Market Response:
    TechCorp shares (TECH) rose 12% in after-hours trading following the announcement.
    The company's market capitalization now exceeds $10 billion.
    
    About TechCorp:
    Founded in 2010, TechCorp is a leader in AI and machine learning technologies.
    Headquarters: San Francisco, CA
    Employees: 200+ worldwide
    Website: https://www.techcorp.com
    Investor Relations: investors@techcorp.com
    """)
    documents.append(doc3)
    
    return documents


def run_semantic_pipeline_example():
    """Run pipeline with semantic text splitting."""
    
    print("🧠 Semantic Pipeline Example")
    print("=" * 40)
    
    # Create sample documents
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        documents = create_sample_documents(temp_path)
        
        print(f"📁 Created {len(documents)} sample documents")
        
        # Create semantic configuration
        config = {
            "pipeline": {
                "name": "Semantic Knowledge Extraction",
                "description": "Pipeline with semantic splitting and advanced extraction",
                "components": {
                    "scanner": {
                        "type": "directory_scanner",
                        "enabled": True,
                        "config": {
                            "recursive": False,
                            "file_patterns": ["*.txt", "*.md"],
                            "supported_extensions": [".txt", ".md"]
                        }
                    },
                    "reader": {
                        "type": "mixed_reader", 
                        "enabled": True,
                        "config": {
                            "supported_types": ["txt", "md"]
                        }
                    },
                    "splitter": {
                        "type": "sentence_splitter",
                        "enabled": True,
                        "config": {
                            "max_sentences": 3,
                            "sentence_overlap": 1,
                            "min_chunk_length": 50
                        }
                    },
                    "extractor": {
                        "type": "keyword_extractor", 
                        "enabled": True,
                        "config": {
                            "keywords": {
                                "Person": ["John Smith", "Sarah Johnson", "Michael Brown", "Alice Chen", "Robert Davis", "Lisa Wang", "Michael Thompson"],
                                "Company": ["TechCorp", "Stanford University", "MIT", "CMU", "Google Cloud", "Microsoft Azure", "UC Berkeley"],
                                "Technology": ["AI", "machine learning", "artificial intelligence", "deep learning", "transformer", "natural language processing"],
                                "Location": ["San Francisco", "California", "New York", "London", "Moscone Center"]
                            },
                            "case_sensitive": False,
                            "word_boundaries": True
                        }
                    },
                    "vectorizer": {
                        "type": "no_op_vectorizer",
                        "enabled": True
                    },
                    "writer": {
                        "type": "json_writer",
                        "enabled": True,
                        "config": {
                            "output_path": "./output/semantic_knowledge_graph.json",
                            "pretty_print": True,
                            "include_metadata": True
                        }
                    }
                }
            }
        }
        
        # Run pipeline
        workflow = PipelineWorkflow(config=config)
        
        print("🔄 Running semantic pipeline...")
        results = workflow.run_pipeline(str(temp_path))
        
        print("✅ Semantic pipeline completed!")
        print(f"📊 Results: {results['execution_summary']}")
        print(f"📝 Output: {results.get('output_path')}")
        
        # Show extracted knowledge
        if results.get('output_path') and os.path.exists(results['output_path']):
            with open(results['output_path'], 'r') as f:
                data = json.load(f)
            
            print(f"\n📈 Extracted Knowledge:")
            print(f"   - Nodes: {len(data.get('nodes', []))}")
            print(f"   - Edges: {len(data.get('edges', []))}")
            
            # Show some example entities
            nodes = data.get('nodes', [])
            if nodes:
                print(f"\n🏷️  Example Entities:")
                for node in nodes[:5]:  # Show first 5
                    print(f"   - {node['name']} ({node['node_type']})")


def run_multi_format_output_example():
    """Run pipeline with multiple output formats."""
    
    print("\n📄 Multi-Format Output Example")
    print("=" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a simple test document
        test_doc = temp_path / "contacts.txt"
        test_doc.write_text("""
        Business Contacts:
        
        John Doe - CEO at Innovation Corp
        Email: john.doe@innovation.com
        Phone: (555) 123-4567
        Website: https://www.innovation.com
        
        Jane Smith - CTO at TechStart
        Email: jane.smith@techstart.io  
        Phone: (555) 987-6543
        Website: https://www.techstart.io
        
        Mike Johnson - Founder of DataSys
        Email: mike@datasys.net
        Phone: (555) 456-7890
        Website: https://datasys.net
        """)
        
        # Configuration with regex extraction and multiple outputs
        config = {
            "pipeline": {
                "name": "Multi-Format Output Pipeline",
                "components": {
                    "scanner": {
                        "type": "file_scanner",
                        "enabled": True
                    },
                    "reader": {
                        "type": "txt_reader",
                        "enabled": True
                    },
                    "splitter": {
                        "type": "length_splitter",
                        "enabled": True,
                        "config": {"chunk_size": 500}
                    },
                    "extractor": {
                        "type": "regex_extractor",
                        "enabled": True, 
                        "config": {
                            "patterns": {
                                "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                                "phone": r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                                "url": r'https?://(?:[-\w.])+(?:\.[A-Z|a-z]{2,})+(?:/[^\s]*)?'
                            },
                            "case_sensitive": False
                        }
                    },
                    "vectorizer": {
                        "type": "no_op_vectorizer",
                        "enabled": True
                    },
                    "writer": {
                        "type": "csv_writer",
                        "enabled": True,
                        "config": {
                            "output_dir": "./output",
                            "nodes_filename": "entities.csv", 
                            "edges_filename": "relationships.csv",
                            "include_embeddings": False
                        }
                    }
                }
            }
        }
        
        # Run pipeline
        workflow = PipelineWorkflow(config=config)
        
        print("🔄 Running multi-format pipeline...")
        results = workflow.run_pipeline(str(test_doc))
        
        print("✅ Multi-format pipeline completed!")
        print(f"📊 Results: {results['execution_summary']}")
        
        # Show CSV output
        nodes_csv = "./output/entities.csv"
        if os.path.exists(nodes_csv):
            print(f"\n📋 Generated CSV file: {nodes_csv}")
            with open(nodes_csv, 'r') as f:
                lines = f.readlines()
                print(f"   Header: {lines[0].strip()}")
                for i, line in enumerate(lines[1:4], 1):  # Show first 3 data rows
                    print(f"   Row {i}: {line.strip()}")


async def run_async_streaming_example():
    """Run async pipeline with streaming."""
    
    print("\n🌊 Async Streaming Example")
    print("=" * 30)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test document
        test_doc = temp_path / "streaming_test.txt"
        test_doc.write_text("""
        Technology News Update:
        
        Apple Inc. announced new iPhone features at their event in Cupertino.
        CEO Tim Cook presented the innovations to developers and media.
        
        Google unveiled improvements to their AI assistant technology.
        The updates will be available through Google Cloud Platform.
        
        Microsoft Azure expanded their machine learning services.
        Satya Nadella emphasized the importance of AI in business transformation.
        """)
        
        # Simple configuration for streaming demo
        config = {
            "pipeline": {
                "name": "Streaming Demo Pipeline",
                "components": {
                    "scanner": {"type": "file_scanner", "enabled": True},
                    "reader": {"type": "txt_reader", "enabled": True},
                    "splitter": {
                        "type": "length_splitter", 
                        "enabled": True,
                        "config": {"chunk_size": 200}
                    },
                    "extractor": {
                        "type": "keyword_extractor",
                        "enabled": True,
                        "config": {
                            "keywords": {
                                "Company": ["Apple", "Google", "Microsoft"],
                                "Person": ["Tim Cook", "Satya Nadella"], 
                                "Technology": ["iPhone", "AI", "machine learning", "Azure", "Cloud Platform"],
                                "Location": ["Cupertino"]
                            }
                        }
                    },
                    "vectorizer": {"type": "no_op_vectorizer", "enabled": True},
                    "writer": {
                        "type": "json_writer",
                        "enabled": True, 
                        "config": {"output_path": "./output/streaming_result.json"}
                    }
                }
            }
        }
        
        # Run with streaming
        workflow = PipelineWorkflow(config=config)
        
        print("🔄 Streaming pipeline execution...")
        async for update in workflow.stream_pipeline(str(test_doc)):
            component = update.get("current_component", "unknown")
            progress = update.get("progress", 0.0)
            status = update.get("status", "unknown")
            timestamp = update.get("timestamp", "")
            
            print(f"   📡 [{timestamp[:19]}] {component}: {status} ({progress:.1%})")
        
        print("✅ Streaming pipeline completed!")


def create_configuration_examples():
    """Create and save example configuration files."""
    
    print("\n⚙️  Configuration Examples")
    print("=" * 30)
    
    # Get example configurations
    example_configs = create_example_configs()
    
    # Ensure output directory exists
    os.makedirs("./output/configs", exist_ok=True)
    
    # Save each configuration
    for name, config in example_configs.items():
        output_path = f"./output/configs/{name}_config.yaml"
        save_config(config, output_path)
        print(f"💾 Saved {name} configuration: {output_path}")
    
    print(f"\n📁 Created {len(example_configs)} example configurations in ./output/configs/")


def main():
    """Run all advanced examples."""
    
    print("🚀 KAG-LangGraph Advanced Examples")
    print("=" * 50)
    
    # Ensure output directory exists
    os.makedirs("./output", exist_ok=True)
    
    try:
        # Run examples
        run_semantic_pipeline_example()
        run_multi_format_output_example()
        
        # Run async example
        asyncio.run(run_async_streaming_example())
        
        # Create configuration examples
        create_configuration_examples()
        
        print("\n🎉 All advanced examples completed successfully!")
        print("\n📋 What was demonstrated:")
        print("   ✅ Semantic text processing with sentence splitting")
        print("   ✅ Advanced keyword-based entity extraction")  
        print("   ✅ Multi-format output (JSON, CSV)")
        print("   ✅ Regex-based pattern extraction")
        print("   ✅ Asynchronous pipeline execution")
        print("   ✅ Real-time streaming updates")
        print("   ✅ Configuration file generation")
        
        print("\n📁 Check these directories for results:")
        print("   - ./output/ - Generated knowledge graphs and data")
        print("   - ./output/configs/ - Example configuration files")
        
    except Exception as e:
        print(f"❌ Error in advanced examples: {e}")
        raise


if __name__ == "__main__":
    main()