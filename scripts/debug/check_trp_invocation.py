"""
Script to verify TRP invocation and debug issues.
"""

import logging
from knowledge_graphs.components.extractor import LLMExtractor
from knowledge_graphs.models.chunk import Chunk
from knowledge_graphs.models.pipeline_state import PipelineState

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# IMPORTANT: Set use_template=True for multi-step extraction
config = {
    "llm_provider": "ollama",
    "model": "llama3.2", 
    "use_template": True,  # ✅ MUST BE TRUE for TRP
    "template_name": "ner.md",
    "entity_types": ["Person", "Organization", "Location", "Concept"],
}

test_chunk = Chunk(
    id="test_1",
    content="Apple Inc. was founded by Steve Jobs in Cupertino. Tim Cook is the current CEO.",
    source_file="test.txt"
)

state = PipelineState()
state["chunks"] = [test_chunk]

try:
    extractor = LLMExtractor(config)
    result = extractor.process(state)
    
    subgraphs = result.get("subgraphs", [])
    
    print("\n" + "="*60)
    print("EXTRACTION RESULTS:")
    print(f"  Subgraphs: {len(subgraphs)}")
    
    if subgraphs:
        for sg in subgraphs:
            print(f"  Nodes: {len(sg.nodes)}")
            print(f"  Edges: {len(sg.edges)}")  # ← This should be > 0 if TRP worked
            
            if sg.edges:
                print("  ✅ TRP WAS INVOKED - Relationships found!")
                for edge in sg.edges[:3]:
                    print(f"    - {edge.source_id} -> {edge.relation_type} -> {edge.target_id}")
            else:
                print("  ❌ TRP NOT INVOKED or found no relationships")
                print("\nCheck logs above for:")
                print("  - 'Starting STD and TRP extraction'")
                print("  - 'Triple extraction completed'")
    
    print("="*60 + "\n")

except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
