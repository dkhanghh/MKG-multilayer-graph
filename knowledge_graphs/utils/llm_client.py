"""
LLM client utilities for KAG-LangGraph.

This module provides abstracted interfaces for different LLM providers
including OpenAI, Ollama, and other compatible APIs.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, AsyncIterator, Iterator
import json
import logging
import os
from enum import Enum

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
    """Abstract base class for LLM clients."""
    
    def __init__(self, model: str, **kwargs):
        """
        Initialize LLM client.
        
        Args:
            model: Model name to use
            **kwargs: Additional client parameters
        """
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    def chat(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of messages
            **kwargs: Additional parameters
            
        Returns:
            LLM response
        """
        pass
    
    @abstractmethod
    async def achat(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """
        Send an async chat completion request.
        
        Args:
            messages: List of messages
            **kwargs: Additional parameters
            
        Returns:
            LLM response
        """
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
    
    def chat(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Send chat completion request to OpenAI."""
        prepared_messages = self._prepare_messages(messages)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=prepared_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage=response.usage.dict() if response.usage else {},
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "created": response.created,
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def achat(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Send async chat completion request to OpenAI."""
        prepared_messages = self._prepare_messages(messages)
        
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=prepared_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage=response.usage.dict() if response.usage else {},
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "created": response.created,
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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
    
    def chat(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """Send chat request to Ollama."""
        prepared_messages = self._prepare_messages(messages)
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=prepared_messages,
                **kwargs
            )
            
            return LLMResponse(
                content=response['message']['content'],
                model=self.model,
                usage={},  # Ollama doesn't provide token usage
                metadata={
                    "created_at": response.get('created_at'),
                    "done": response.get('done'),
                }
            )
            
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise
    
    async def achat(
        self,
        messages: List[Union[LLMMessage, Dict[str, Any]]],
        **kwargs
    ) -> LLMResponse:
        """Send async chat request to Ollama."""
        # Ollama client doesn't have native async support
        # Use asyncio.to_thread for now
        import asyncio
        return await asyncio.to_thread(self.chat, messages, **kwargs)


def create_llm_client(
    provider: Union[str, LLMProvider],
    model: str,
    **kwargs
) -> LLMClient:
    """
    Factory function to create LLM clients.
    
    Args:
        provider: LLM provider name
        model: Model name
        **kwargs: Additional client parameters
        
    Returns:
        LLM client instance
        
    Raises:
        ValueError: If provider is not supported
    """
    if isinstance(provider, str):
        provider = LLMProvider(provider.lower())
    
    if provider == LLMProvider.OPENAI:
        return OpenAIClient(model=model, **kwargs)
    elif provider == LLMProvider.OLLAMA:
        return OllamaClient(model=model, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


# Utility functions for common LLM tasks
def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling various formats.
    
    Args:
        response: LLM response text
        
    Returns:
        Parsed JSON dictionary or None if not found
    """
    # Try to find JSON in response
    import re
    
    # Look for JSON blocks
    json_patterns = [
        r'```json\s*(\{.*?\})\s*```',  # JSON code blocks
        r'```\s*(\{.*?\})\s*```',      # Generic code blocks with JSON
        r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',  # JSON objects
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    # Try parsing the entire response as JSON
    try:
        return json.loads(response)
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