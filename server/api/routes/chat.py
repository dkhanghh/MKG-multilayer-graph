"""Chat endpoints."""
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from server.api.exceptions import APIError
from server.api.routes.auth import User, get_current_active_user
from rag.agent import get_react_agent

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: User = Depends(get_current_active_user)):
    """Send a chat message and receive an AI response."""
    try:
        agent = get_react_agent()

        messages = []
        for msg in request.history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=request.message))

        result = await agent.ainvoke({"messages": messages})
        response_content = result["messages"][-1].content

        return {"response": response_content}

    except Exception as exc:
        logger.exception("Chat request failed")
        raise APIError(detail="Chat request failed")
