"""ReAct agent setup for RAG chatbot."""
import datetime
import logging
from pathlib import Path

import pytz
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from jinja2 import Template

from .state import ChatState
from .tools import neo4j_hybrid_search_tool
from server.core.llm import create_chat_llm

logger = logging.getLogger(__name__)

# Module-level singleton
_react_agent = None

# Prompt template path (Jinja2 markdown)
_PROMPT_PATH = Path(__file__).parent / "prompts" / "react_agent_vi.md"


def _load_prompt() -> str:
    """Load and render the system prompt template."""
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    current_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    template_text = _PROMPT_PATH.read_text(encoding="utf-8")
    return Template(template_text).render(current_time=current_time)


def _load_mcp_tools() -> list:
    """Attempt to load MCP tools; return empty list on failure."""
    try:
        from rag.tools.mcp import get_mcp_tools

        mcp_tools = get_mcp_tools()
        if mcp_tools:
            logger.info("Loaded %d MCP tools", len(mcp_tools))
            for tool in mcp_tools:
                logger.debug("  MCP tool: %s", tool.name)
            return mcp_tools
        logger.info("No MCP tools available")
    except ImportError as exc:
        logger.warning("Could not import MCP tools: %s", exc)
    except Exception as exc:
        logger.error("Error loading MCP tools: %s", exc)
    return []


def get_react_agent():
    """Get or create the ReAct agent singleton."""
    global _react_agent

    if _react_agent is not None:
        return _react_agent

    llm = create_chat_llm()

    # Collect ALL tools first, then create agent ONCE
    tools = [neo4j_hybrid_search_tool]
    tools.extend(_load_mcp_tools())

    prompt = _load_prompt()

    _react_agent = create_react_agent(llm, tools, prompt=prompt)

    logger.info(
        "ReAct agent initialised with %d tools: %s",
        len(tools),
        [t.name for t in tools],
    )
    return _react_agent


def agent_node(state: ChatState) -> ChatState:
    """Agent node that invokes the ReAct agent.

    Args:
        state: Current chat state with messages.

    Returns:
        Updated state with the agent's response messages.
    """
    agent = get_react_agent()
    messages = list(state["messages"])

    logger.debug("Invoking ReAct agent with %d messages", len(messages))
    result = agent.invoke({"messages": messages})

    return {"messages": result["messages"]}
