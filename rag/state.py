"""State definitions for the RAG chatbot graph."""
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    """State for the chat graph.

    Only ``messages`` is used by the ReAct agent flow.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
