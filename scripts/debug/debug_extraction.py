"""
Debug script to check why extraction produces no subgraphs.
"""

import logging
import json
from knowledge_graphs.components.extractor import LLMExtractor
from knowledge_graphs.models.chunk import Chunk
from knowledge_graphs.models.pipeline_state import PipelineState

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create sample configuration
config = {
    "llm_provider": "ollama",  # or "openai"
    "model": "llama3.2",
    "temperature": 0.1,
    "max_tokens": 2000,
    "use_template": True,
    "template_name": "ner.md",
    "entity_types": ["Person", "Organization", "Location", "Concept"],
    "min_chunk_length": 10
}

# Create a test chunk
test_chunk = Chunk(
    id="test_chunk_1",
    content="Apple Inc. was founded by Steve Jobs in Cupertino, California. The company develops innovative technology products.",
    source_file="test.txt",
    page_number=1,
    chunk_index=0
)

logger.info(f"Test chunk length: {len(test_chunk.content)} characters")
logger.info(f"Test chunk content: {test_chunk.content[:100]}...")

# Create pipeline state
state = PipelineState()
state["chunks"] = [test_chunk]

try:
    # Initialize extractor
    logger.info("Initializing extractor...")
    extractor = LLMExtractor(config)
    
    # Process
    logger.info("Running extraction...")
    result_state = extractor.process(state)
    
    # Check results
    subgraphs = result_state.get("subgraphs", [])
    logger.info(f"\n{'='*60}")
    logger.info(f"RESULTS:")
    logger.info(f"  Total subgraphs: {len(subgraphs)}")
    
    if subgraphs:
        for i, sg in enumerate(subgraphs):
            logger.info(f"  Subgraph {i+1}:")
            logger.info(f"    - Nodes: {len(sg.nodes)}")
            logger.info(f"    - Edges: {len(sg.edges)}")
            
            if sg.nodes:
                logger.info(f"    - Node names: {[n.name for n in sg.nodes[:5]]}")
    else:
        logger.warning("NO SUBGRAPHS CREATED!")
        logger.warning("\nPossible reasons:")
        logger.warning("1. LLM not extracting entities")
        logger.warning("2. Invalid JSON response from LLM")
        logger.warning("3. Entities missing required fields")
        logger.warning("4. Check logs above for 'No valid entities found'")
    
    logger.info(f"{'='*60}\n")

except Exception as e:
    logger.error(f"Error during extraction: {e}", exc_info=True)

