"""
Graph node functions for RAG chatbot.
"""
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from .state import ChatState

from dotenv import load_dotenv

load_dotenv(override=True)


def preprocess_query_node(state: ChatState) -> ChatState:
    """
    Preprocessing node that detects intent and decomposes query into sub-questions.

    Args:
        state: Current chat state

    Returns:
        Updated state with intent, sub-questions, and original question
    """
    # Get the last user message
    messages = state["messages"]
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    if not last_user_message:
        # No user message found, skip preprocessing
        return {
            "intent": "unknown",
            "sub_questions": [],
            "original_question": ""
        }

    # Initialize LLM for preprocessing
    base_url = os.getenv("CHAT_OPENAI_BASE_URL", None)
    api_key = os.getenv("OPENAI_API_KEY")

    # If using custom base_url without api_key, use "EMPTY" as recommended by LangChain
    # See: https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html
    if base_url and not api_key:
        api_key = "EMPTY"

    llm_kwargs = {
        "model": os.getenv("CHAT_LLM_MODEL", "gpt-5"),
        "temperature": 1,  # Low temperature for more consistent analysis
        "api_key": api_key
    }

    # Add base_url if provided
    if base_url:
        llm_kwargs["base_url"] = base_url

        # Add headers to help bypass Cloudflare protection
        llm_kwargs["default_headers"] = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }

    llm = ChatOpenAI(**llm_kwargs)

    # Intent detection prompt
    intent_prompt = f"""Analyze the following user question and classify its intent into ONE of these categories:
- factual_lookup: Looking for specific facts or information
- comparison: Comparing multiple entities or concepts
- explanation: Asking for explanation or understanding of a concept
- procedure: Asking how to do something
- troubleshooting: Trying to solve a problem
- general_conversation: General chat or greeting

Question: {last_user_message}

Respond with ONLY the intent category name (e.g., "factual_lookup").
"""

    intent_response = llm.invoke([HumanMessage(content=intent_prompt)])
    detected_intent = intent_response.content.strip()

    # Entity extraction prompt - focused on entities that can help answer the question
    entity_prompt = f"""Identify the TOP 3 MOST IMPORTANT entities and concepts that would be relevant to finding information to answer this question.

Question: {last_user_message}

Extract EXACTLY 3 entities from these categories:
1. **Main Entities**: The primary subjects, objects, or concepts mentioned in the question
   - Named entities (organizations, products, standards, technologies, methods)
   - Technical terms and domain-specific concepts

2. **Related Entities**: Entities that might exist in a knowledge graph that could help answer the question
   - Related concepts, methods, or processes
   - Standards, specifications, or documents that might contain relevant information
   - Categories or types that the main entities belong to

3. **Contextual Entities**: Background concepts that provide necessary context
   - Domain areas (e.g., "materials testing", "software engineering")
   - General categories or classifications

Focus on entities that likely exist as nodes in a knowledge graph and could provide useful information through their relationships.

IMPORTANT: Return EXACTLY 3 entities, prioritized by importance.
Return ONLY a comma-separated list of 3 entities (e.g., "temperature cycling, thermal shock, reliability testing").
If fewer than 3 clear entities exist, return only those found.
If no clear entities are found, return "NONE".

Entities:"""

    entity_response = llm.invoke([HumanMessage(content=entity_prompt)])
    entity_text = entity_response.content.strip()

    # Parse entities from the response
    entities = []
    if entity_text and entity_text.upper() != "NONE":
        # Split by comma and clean up
        for entity in entity_text.split(','):
            entity = entity.strip()
            if entity:
                entities.append(entity)

    print(f"\n[Preprocessing] Intent: {detected_intent}")
    print(f"[Preprocessing] Original: {last_user_message}")
    print(f"[Preprocessing] Entities ({len(entities)}): {', '.join(entities) if entities else 'None'}")
    print()

    return {
        "intent": detected_intent,
        "original_question": last_user_message,
        "entities": entities
    }

