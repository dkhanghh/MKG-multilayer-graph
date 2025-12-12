"""Chat endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from server.api.routes.auth import get_current_active_user, User
from chatbot_graphs.agent import get_react_agent
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    response: str

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: User = Depends(get_current_active_user)):
    try:
        agent = get_react_agent()
        
        # Convert history to LangChain messages
        messages = []
        for msg in request.history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current message
        messages.append(HumanMessage(content=request.message))
        
        # Invoke agent
        result = agent.invoke({"messages": messages})
        
        # Get last message content
        last_message = result["messages"][-1]
        response_content = last_message.content
        
        return {"response": response_content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
