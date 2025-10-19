"""
State definitions for the RAG chatbot graph.
"""
from typing import TypedDict, Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """State for the chat graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    retrieved_context: str
    intent: str  # Detected intent of the user query
    original_question: str  # The original user question
    entities: list[str]  # Extracted entities that are relevant to answering the query
