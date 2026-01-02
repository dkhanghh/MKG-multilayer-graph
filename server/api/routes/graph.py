"""Graph visualization endpoints."""
import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List

from server.api.routes.auth import get_current_active_user, User
from server.core.config import DEFAULT_CONFIG
from chatbot_graphs.retrievers import get_retriever

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/data")
async def get_graph_data(current_user: User = Depends(get_current_active_user)):
    """
    Retrieve graph data for visualization from Neo4j.
    """
    try:
        retriever = get_retriever()
        if not retriever.driver:
             # Fallback to dummy data if driver is not available/configured
             logger.warning("Neo4j driver not available, returning dummy data")
             return {
                "nodes": [
                    {"id": "Node1", "group": "Entity", "label": "No Database Connection"},
                ],
                "links": []
            }

        # Cypher query to get a subgraph
        # Limiting to 300 relationships to prevent overwhelming the UI
        query = """
        MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT 300
        """
        
        nodes_dict = {}
        links_list = []
        
        with retriever.driver.session(database=retriever.database) as session:
            result = session.run(query)
            
            for record in result:
                n = record["n"]
                m = record["m"]
                r = record["r"]
                
                # Process source node
                # Use 'id' property if available, otherwise element_id or id()
                n_id = n.get("id", n.element_id)
                if n_id not in nodes_dict:
                    # Get the first label as the group
                    labels = list(n.labels)
                    group = labels[0] if labels else "Unknown"
                    
                    nodes_dict[n_id] = {
                        "id": n_id,
                        "group": group,
                        "label": n.get("name", f"Node {n_id}")
                    }
                
                # Process target node
                m_id = m.get("id", m.element_id)
                if m_id not in nodes_dict:
                    labels = list(m.labels)
                    group = labels[0] if labels else "Unknown"
                    
                    nodes_dict[m_id] = {
                        "id": m_id,
                        "group": group,
                        "label": m.get("name", f"Node {m_id}")
                    }
                
                # Process relationship
                links_list.append({
                    "source": n_id,
                    "target": m_id,
                    "type": r.type,
                    "label": r.type
                })
        
        return {
            "nodes": list(nodes_dict.values()),
            "links": links_list
        }

    except Exception as e:
        logger.error(f"Error fetching graph data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
