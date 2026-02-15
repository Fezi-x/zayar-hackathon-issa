from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class LLMError(Exception):
    """Base exception for LLM related errors."""
    pass

class LLMProviderError(LLMError):
    """Exception raised when the LLM provider fails (network, 500, etc)."""
    pass

class LLMQuotaError(LLMError):
    """Exception raised when quota is exceeded (429)."""
    pass

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_message: str, **kwargs) -> str:
        """
        Generate a text response from the LLM.
        """
        pass

    @abstractmethod
    async def chat(self, messages: List[Dict], **kwargs) -> str:
        """
        OpenAI-style chat interface.
        """
        pass
