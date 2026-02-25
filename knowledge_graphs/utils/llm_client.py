"""
LLM client utilities for KAG-LangGraph.

This module provides abstracted interfaces for different LLM providers
including OpenAI, Ollama, and other compatible APIs with LangGraph tracing support.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, AsyncIterator, Iterator
import json
import logging
import os
from enum import Enum

from .retry import retry_with_backoff, async_retry_with_backoff

# LangSmith tracing imports
try:
    from langsmith import traceable, trace
    from langsmith.run_helpers import get_current_run_tree
    HAS_LANGSMITH = True
except ImportError:
    HAS_LANGSMITH = False
    # Create no-op decorators if langsmith not available
    def traceable(func=None, *, name=None, **kwargs):
        if func is None:
            return lambda f: f
        return func

    def trace(**kwargs):
        return lambda func: func

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    
    OPENAI = "openai"
    OLLAMA = "ollama"
    AZURE = "azure"


class LLMMessage:
    """Represents a message in an LLM conversation."""
    
    def __init__(self, role: str, content: str, **kwargs):
        """
        Initialize an LLM message.
        
        Args:
            role: Message role (system, user, assistant)
            content: Message content
            **kwargs: Additional message parameters
        """
        self.role = role
        self.content = content
        self.metadata = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "role": self.role,
            "content": self.content,
            **self.metadata
        }


class LLMResponse:
    """Represents a response from an LLM."""
    
    def __init__(
        self,
        content: str,
        model: str,
        usage: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an LLM response.
        
        Args:
            content: Response content
            model: Model name used
            usage: Token usage information
            metadata: Additional response metadata
        """
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "metadata": self.metadata
        }


class LLMClient(ABC):
    """Abstract base class for LLM clients with LangGraph tracing support."""

    def __init__(self, model: str, **kwargs):
        """
        Initialize LLM client.

        Args:
            model: Model name to use
            **kwargs: Additional client parameters
        """
        self.model = model
        self.config = kwargs
        self.tracing_enabled = kwargs.get('enable_tracing', True)

    def _get_trace_metadata(self, messages: List[Union[LLMMessage, Dict[str, Any]]], **kwargs) -> Dict[str, Any]:
        """Get metadata for tracing."""
        return {
            "model": self.model,
            "provider": self.__class__.__name__.replace("Client", "").lower(),
            "message_count": len(messages),
            "temperature": kwargs.get("temperature"),
            "max_tokens": kwargs.get("max_tokens"),
        }

    @traceable(name="llm_chat")
    def chat(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat completion request with tracing.

        Args:
            messages: List of messages
            **kwargs: Additional parameters

        Returns:
            LLM response
        """
        # Add tracing metadata
        if HAS_LANGSMITH and self.tracing_enabled:
            run_tree = get_current_run_tree()
            if run_tree:
                run_tree.extra.update(self._get_trace_metadata(messages, **kwargs))
                run_tree.inputs = {
                    "messages": [msg.to_dict() if isinstance(msg, LLMMessage) else msg for msg in messages],
                    "model": self.model,
                    **kwargs
                }

        # Merge stored config with runtime kwargs, filtering out client-specific params
        # Only pass API parameters to the LLM, not client configuration
        api_params = ['temperature', 'max_tokens', 'max_completion_tokens', 'top_p', 'frequency_penalty', 'presence_penalty', 'stop']
        filtered_config = {k: v for k, v in self.config.items() if k in api_params}
        merged_kwargs = {**filtered_config, **kwargs}

        # Handle parameter name change for newer models and filter None values
        # GPT-5 and some GPT-4 models use max_completion_tokens instead of max_tokens
        if 'max_tokens' in merged_kwargs:
            if merged_kwargs['max_tokens'] is None:
                # Remove None values completely
                merged_kwargs.pop('max_tokens')
            elif self.model and ('gpt-5' in self.model.lower() or 'gpt-4o' in self.model.lower()):
                # Convert to max_completion_tokens for newer models
                merged_kwargs['max_completion_tokens'] = merged_kwargs.pop('max_tokens')

        # Filter out any remaining None values to avoid API errors
        filtered_kwargs = {k: v for k, v in merged_kwargs.items() if v is not None}

        return self._chat_impl(messages, **filtered_kwargs)

    @traceable(name="llm_achat")
    async def achat(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """
        Send an async chat completion request with tracing.

        Args:
            messages: List of messages
            **kwargs: Additional parameters

        Returns:
            LLM response
        """
        # Add tracing metadata
        if HAS_LANGSMITH and self.tracing_enabled:
            run_tree = get_current_run_tree()
            if run_tree:
                run_tree.extra.update(self._get_trace_metadata(messages, **kwargs))
                run_tree.inputs = {
                    "messages": [msg.to_dict() if isinstance(msg, LLMMessage) else msg for msg in messages],
                    "model": self.model,
                    **kwargs
                }

        # Merge stored config with runtime kwargs, filtering out client-specific params
        # Only pass API parameters to the LLM, not client configuration
        api_params = ['temperature', 'max_tokens', 'max_completion_tokens', 'top_p', 'frequency_penalty', 'presence_penalty', 'stop']
        filtered_config = {k: v for k, v in self.config.items() if k in api_params}
        merged_kwargs = {**filtered_config, **kwargs}

        # Handle parameter name change for newer models and filter None values
        # GPT-5 and some GPT-4 models use max_completion_tokens instead of max_tokens
        if 'max_tokens' in merged_kwargs:
            if merged_kwargs['max_tokens'] is None:
                # Remove None values completely
                merged_kwargs.pop('max_tokens')
            elif self.model and ('gpt-5' in self.model.lower() or 'gpt-4o' in self.model.lower()):
                # Convert to max_completion_tokens for newer models
                merged_kwargs['max_completion_tokens'] = merged_kwargs.pop('max_tokens')

        # Filter out any remaining None values to avoid API errors
        filtered_kwargs = {k: v for k, v in merged_kwargs.items() if v is not None}

        return await self._achat_impl(messages, **filtered_kwargs)

    @abstractmethod
    def _chat_impl(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """Implementation of chat method (to be overridden)."""
        pass

    @abstractmethod
    async def _achat_impl(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """Implementation of async chat method (to be overridden)."""
        pass
    
    def simple_chat(self, prompt: str, **kwargs) -> str:
        """
        Simple chat interface with just a prompt.
        
        Args:
            prompt: User prompt
            **kwargs: Additional parameters
            
        Returns:
            Response content
        """
        messages = [LLMMessage("user", prompt)]
        response = self.chat(messages, **kwargs)
        return response.content
    
    async def asimple_chat(self, prompt: str, **kwargs) -> str:
        """
        Async simple chat interface.
        
        Args:
            prompt: User prompt
            **kwargs: Additional parameters
            
        Returns:
            Response content
        """
        messages = [LLMMessage("user", prompt)]
        response = await self.achat(messages, **kwargs)
        return response.content
    
    def _prepare_messages(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Prepare messages for API call.
        
        Args:
            messages: List of messages
            
        Returns:
            List of message dictionaries
        """
        prepared = []
        for msg in messages:
            if isinstance(msg, LLMMessage):
                prepared.append(msg.to_dict())
            elif isinstance(msg, dict):
                prepared.append(msg)
            else:
                raise TypeError(f"Invalid message type: {type(msg)}")
        return prepared


class OpenAIClient(LLMClient):
    """OpenAI API client."""
    
    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize OpenAI client.
        
        Args:
            model: Model name (e.g., gpt-4, gpt-3.5-turbo)
            api_key: OpenAI API key (or from environment)
            base_url: Optional base URL for API
            **kwargs: Additional client parameters
        """
        if not HAS_OPENAI:
            raise ImportError("openai package not installed. Install with: pip install openai")
        
        super().__init__(model, **kwargs)
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and not found in environment")
        
        # Initialize OpenAI client
        client_kwargs = {"api_key": self.api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
            
        self.client = openai.OpenAI(**client_kwargs)
        self.async_client = openai.AsyncOpenAI(**client_kwargs)
    
    def _chat_impl(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Send chat completion request to OpenAI."""
        prepared_messages = self._prepare_messages(messages)

        # Build API parameters, filtering out None values
        api_params = {
            "model": self.model,
            "messages": prepared_messages,
            "temperature": temperature,
            **kwargs
        }

        # Only add max_tokens if it's not None
        if max_tokens is not None:
            # Handle GPT-5 model parameter name
            if self.model and ('gpt-5' in self.model.lower() or 'gpt-4o' in self.model.lower()):
                api_params["max_completion_tokens"] = max_tokens
            else:
                api_params["max_tokens"] = max_tokens

        @retry_with_backoff(max_attempts=3, base_delay=2.0, max_delay=30.0)
        def _call_api():
            return self.client.chat.completions.create(**api_params)

        try:
            response = _call_api()

            llm_response = LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage=response.usage.dict() if response.usage else {},
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "created": response.created,
                }
            )

            # Add response to trace if tracing is enabled
            if HAS_LANGSMITH and self.tracing_enabled:
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.outputs = {
                        "content": llm_response.content,
                        "model": llm_response.model,
                        "usage": llm_response.usage,
                        "finish_reason": llm_response.metadata.get("finish_reason")
                    }

            return llm_response

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            if HAS_LANGSMITH and self.tracing_enabled:
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.error = str(e)
            raise

    async def _achat_impl(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Send async chat completion request to OpenAI."""
        prepared_messages = self._prepare_messages(messages)

        # Build API parameters, filtering out None values
        api_params = {
            "model": self.model,
            "messages": prepared_messages,
            "temperature": temperature,
            **kwargs
        }

        # Only add max_tokens if it's not None
        if max_tokens is not None:
            # Handle GPT-5 model parameter name
            if self.model and ('gpt-5' in self.model.lower() or 'gpt-4o' in self.model.lower()):
                api_params["max_completion_tokens"] = max_tokens
            else:
                api_params["max_tokens"] = max_tokens

        @async_retry_with_backoff(max_attempts=3, base_delay=2.0, max_delay=30.0)
        async def _call_api():
            return await self.async_client.chat.completions.create(**api_params)

        try:
            response = await _call_api()

            llm_response = LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage=response.usage.dict() if response.usage else {},
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "created": response.created,
                }
            )

            # Add response to trace if tracing is enabled
            if HAS_LANGSMITH and self.tracing_enabled:
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.outputs = {
                        "content": llm_response.content,
                        "model": llm_response.model,
                        "usage": llm_response.usage,
                        "finish_reason": llm_response.metadata.get("finish_reason")
                    }

            return llm_response

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            if HAS_LANGSMITH and self.tracing_enabled:
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.error = str(e)
            raise


class OllamaClient(LLMClient):
    """Ollama API client."""
    
    def __init__(
        self,
        model: str = "llama2",
        host: str = "http://localhost:11434",
        **kwargs
    ):
        """
        Initialize Ollama client.
        
        Args:
            model: Model name (e.g., llama2, codellama)
            host: Ollama server host
            **kwargs: Additional client parameters
        """
        if not HAS_OLLAMA:
            raise ImportError("ollama package not installed. Install with: pip install ollama")
        
        super().__init__(model, **kwargs)
        self.host = host
        self.client = ollama.Client(host=host)
    
    def _chat_impl(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """Send chat request to Ollama."""
        prepared_messages = self._prepare_messages(messages)

        @retry_with_backoff(max_attempts=3, base_delay=2.0, max_delay=30.0)
        def _call_api():
            return self.client.chat(
                model=self.model,
                messages=prepared_messages,
                **kwargs
            )

        try:
            response = _call_api()

            llm_response = LLMResponse(
                content=response['message']['content'],
                model=self.model,
                usage={},  # Ollama doesn't provide token usage
                metadata={
                    "created_at": response.get('created_at'),
                    "done": response.get('done'),
                }
            )

            # Add response to trace if tracing is enabled
            if HAS_LANGSMITH and self.tracing_enabled:
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.outputs = {
                        "content": llm_response.content,
                        "model": llm_response.model,
                        "created_at": llm_response.metadata.get("created_at"),
                        "done": llm_response.metadata.get("done")
                    }

            return llm_response

        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            if HAS_LANGSMITH and self.tracing_enabled:
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.error = str(e)
            raise

    async def _achat_impl(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """Send async chat request to Ollama."""
        # Ollama client doesn't have native async support
        # Use asyncio.to_thread for now
        import asyncio
        return await asyncio.to_thread(self._chat_impl, messages, **kwargs)


def create_llm_client(
    provider: Union[str, LLMProvider],
    model: str,
    enable_tracing: bool = True,
    **kwargs
) -> LLMClient:
    """
    Factory function to create LLM clients with tracing support.

    Args:
        provider: LLM provider name
        model: Model name
        enable_tracing: Whether to enable LangSmith tracing (default: True)
        **kwargs: Additional client parameters

    Returns:
        LLM client instance with tracing enabled

    Raises:
        ValueError: If provider is not supported
    """
    if isinstance(provider, str):
        provider = LLMProvider(provider.lower())

    kwargs['enable_tracing'] = enable_tracing

    if provider == LLMProvider.OPENAI:
        return OpenAIClient(model=model, **kwargs)
    elif provider == LLMProvider.OLLAMA:
        return OllamaClient(model=model, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def configure_tracing(
    project_name: Optional[str] = None,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None
) -> None:
    """
    Configure LangSmith tracing for LLM clients.

    Args:
        project_name: LangSmith project name (or use LANGCHAIN_PROJECT env var)
        api_key: LangSmith API key (or use LANGCHAIN_API_KEY env var)
        endpoint: LangSmith endpoint (or use LANGCHAIN_ENDPOINT env var)

    Usage:
        # Configure tracing before creating LLM clients
        configure_tracing(project_name="my-kg-project")

        # Create traced LLM client
        client = create_llm_client("openai", "gpt-4", enable_tracing=True)
    """
    if not HAS_LANGSMITH:
        logger.warning("langsmith not installed. Install with: pip install langsmith")
        return

    # Set environment variables for LangSmith
    if project_name:
        os.environ["LANGCHAIN_PROJECT"] = project_name
    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
    if endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    # Enable tracing
    os.environ["LANGCHAIN_TRACING_V2"] = "true"

    logger.info(f"LangSmith tracing configured for project: {project_name or os.getenv('LANGCHAIN_PROJECT', 'default')}")


# Utility functions for common LLM tasks
def extract_json_from_response(response: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
    """
    Extract JSON from LLM response, handling various formats including arrays.

    Args:
        response: LLM response text

    Returns:
        Parsed JSON dictionary, list, or None if not found
    """
    # Try to find JSON in response
    import re

    # Look for JSON blocks (both objects and arrays)
    json_patterns = [
        r'```json\s*(\[.*?\])\s*```',  # JSON code blocks with arrays
        r'```json\s*(\{.*?\})\s*```',  # JSON code blocks with objects
        r'```\s*(\[.*?\])\s*```',      # Generic code blocks with arrays
        r'```\s*(\{.*?\})\s*```',      # Generic code blocks with objects
        r'(\[[^\[\]]*(?:\{[^\{\}]*\}[^\[\]]*)*\])',  # JSON arrays
        r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',  # JSON objects
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                # Prefer arrays over objects (arrays contain more data)
                if isinstance(parsed, list):
                    return parsed
                # Store object as fallback
                if not isinstance(parsed, list):
                    fallback = parsed
            except json.JSONDecodeError:
                continue

    # Return fallback object if no array found
    if 'fallback' in locals():
        return fallback

    # Try parsing the entire response as JSON
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    return None


def create_extraction_prompt(
    text: str,
    schema: Dict[str, Any],
    instructions: str = ""
) -> str:
    """
    Create a prompt for structured extraction.
    
    Args:
        text: Text to extract from
        schema: JSON schema for extraction
        instructions: Additional instructions
        
    Returns:
        Formatted prompt
    """
    base_prompt = f"""
Extract structured information from the following text according to the provided schema.

Text:
{text}

Schema:
{json.dumps(schema, indent=2)}

{instructions}

Please respond with valid JSON that matches the schema. Use null for missing values.

Response:"""

    return base_prompt.strip()


# Example usage with LangGraph tracing
"""
USAGE EXAMPLES WITH LANGGRAPH TRACING:

1. Basic setup with tracing:
```python
from knowledge_graphs.utils.llm_client import configure_tracing, create_llm_client

# Configure LangSmith tracing
configure_tracing(project_name="knowledge-graph-extraction")

# Create traced LLM client
llm_client = create_llm_client(
    provider="openai",
    model="gpt-4",
    api_key="your-openai-key",
    enable_tracing=True
)

# Use in your extractor
response = llm_client.simple_chat("Extract entities from: John works at Microsoft")
```

2. Use with LangGraph nodes:
```python
from langgraph import Graph
from knowledge_graphs.utils.llm_client import create_llm_client

def extraction_node(state):
    # This will be traced automatically in LangGraph
    llm_client = create_llm_client("openai", "gpt-4", enable_tracing=True)

    result = llm_client.simple_chat(f"Extract entities from: {state['text']}")
    return {"extracted_entities": result}

# Create LangGraph with tracing
graph = Graph()
graph.add_node("extract", extraction_node)
```

3. Environment variables for tracing:
```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT="your-project-name"
export LANGCHAIN_API_KEY="your-langsmith-api-key"
export OPENAI_API_KEY="your-openai-key"
```

4. Disable tracing for specific client:
```python
# Create client without tracing
llm_client = create_llm_client(
    provider="openai",
    model="gpt-4",
    enable_tracing=False  # Disable tracing
)
```

The traced LLM calls will appear in your LangSmith dashboard with:
- Input messages and parameters
- Output content and metadata
- Token usage and timing
- Error information if failures occur
- Full integration with LangGraph execution traces
"""