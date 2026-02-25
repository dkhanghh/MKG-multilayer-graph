"""Graph visualisation endpoints."""
import logging

from fastapi import APIRouter, Depends

from server.api.exceptions import APIError, ServiceUnavailableError
from server.api.routes.auth import User, get_current_active_user
from rag.retrievers import get_retriever

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/data")
async def get_graph_data(current_user: User = Depends(get_current_active_user)):
    """Retrieve graph data for visualisation from Neo4j."""
    try:
        retriever = get_retriever()
        if not retriever.driver:
            raise ServiceUnavailableError(detail="Neo4j connection not available")

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
                n, m, r = record["n"], record["m"], record["r"]

                n_id = n.get("id", n.element_id)
                if n_id not in nodes_dict:
                    labels = list(n.labels)
                    nodes_dict[n_id] = {
                        "id": n_id,
                        "group": labels[0] if labels else "Unknown",
                        "label": n.get("name", f"Node {n_id}"),
                    }

                m_id = m.get("id", m.element_id)
                if m_id not in nodes_dict:
                    labels = list(m.labels)
                    nodes_dict[m_id] = {
                        "id": m_id,
                        "group": labels[0] if labels else "Unknown",
                        "label": m.get("name", f"Node {m_id}"),
                    }

                links_list.append({
                    "source": n_id,
                    "target": m_id,
                    "type": r.type,
                    "label": r.type,
                })

        return {"nodes": list(nodes_dict.values()), "links": links_list}

    except (APIError, ServiceUnavailableError):
        raise
    except Exception as exc:
        logger.exception("Failed to fetch graph data")
        raise APIError(detail="Could not fetch graph data")
