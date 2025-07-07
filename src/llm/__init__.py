"""LLM abstraction layer for the note assistant."""

from .base_client import BaseLLMClient
from .factory import (
    create_llm_client, 
    create_llm_client_with_fallback,
    list_available_providers,
    get_provider_info
)
from .litellm_client import LiteLLMClient
from .claude_client_wrapper import ClaudeClientWrapper

__all__ = [
    'BaseLLMClient',
    'LiteLLMClient', 
    'ClaudeClientWrapper',
    'create_llm_client',
    'create_llm_client_with_fallback',
    'list_available_providers',
    'get_provider_info'
]