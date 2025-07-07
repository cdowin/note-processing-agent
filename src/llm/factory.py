"""Factory for creating LLM clients based on configuration."""

import logging
from typing import Any, Optional

from .base_client import BaseLLMClient
from .litellm_client import LiteLLMClient
from .claude_client_wrapper import ClaudeClientWrapper


logger = logging.getLogger(__name__)


# Registry of available LLM clients
CLIENT_REGISTRY = {
    'litellm': LiteLLMClient,
    'claude_direct': ClaudeClientWrapper,
    # Add more providers here as they are implemented
}


def create_llm_client(config: Any, provider_name: Optional[str] = None) -> BaseLLMClient:
    """
    Create an LLM client based on configuration.
    
    Args:
        config: Configuration object containing LLM settings
        provider_name: Optional override for the provider name
        
    Returns:
        BaseLLMClient: Configured LLM client instance
        
    Raises:
        ValueError: If the provider is not supported or configuration is invalid
        ImportError: If required dependencies are not installed
    """
    # Determine provider name
    if provider_name is None:
        # Get from config
        llm_config = getattr(config, 'llm', {})
        provider_name = llm_config.get('primary_provider', 'claude_direct')
    
    # Validate provider is supported
    if provider_name not in CLIENT_REGISTRY:
        available_providers = list(CLIENT_REGISTRY.keys())
        raise ValueError(
            f"Unsupported LLM provider: {provider_name}. "
            f"Available providers: {available_providers}"
        )
    
    # Get client class
    client_class = CLIENT_REGISTRY[provider_name]
    
    try:
        # Create client instance
        client = client_class(config)
        
        # Validate configuration
        if not client.validate_config():
            raise ValueError(f"Invalid configuration for {provider_name} provider")
        
        logger.info(f"Created {provider_name} client: {client.model_name}")
        return client
        
    except ImportError as e:
        logger.error(f"Failed to import dependencies for {provider_name}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create {provider_name} client: {e}")
        raise


def create_llm_client_with_fallback(config: Any) -> BaseLLMClient:
    """
    Create an LLM client with automatic fallback to alternative providers.
    
    Args:
        config: Configuration object containing LLM settings
        
    Returns:
        BaseLLMClient: Configured LLM client instance
        
    Raises:
        RuntimeError: If no providers can be created successfully
    """
    llm_config = getattr(config, 'llm', {})
    primary_provider = llm_config.get('primary_provider', 'claude_direct')
    fallback_provider = llm_config.get('fallback_provider', None)
    
    # Try primary provider first
    try:
        client = create_llm_client(config, primary_provider)
        logger.info(f"Successfully created primary LLM client: {primary_provider}")
        return client
    except Exception as e:
        logger.warning(f"Failed to create primary provider {primary_provider}: {e}")
        
        # Try fallback provider if available
        if fallback_provider and fallback_provider != primary_provider:
            try:
                client = create_llm_client(config, fallback_provider)
                logger.info(f"Successfully created fallback LLM client: {fallback_provider}")
                return client
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback provider {fallback_provider}: {fallback_error}")
        
        # Try other available providers as last resort
        available_providers = [p for p in CLIENT_REGISTRY.keys() 
                             if p not in [primary_provider, fallback_provider]]
        
        for provider in available_providers:
            try:
                client = create_llm_client(config, provider)
                logger.warning(f"Successfully created emergency fallback LLM client: {provider}")
                return client
            except Exception as emergency_error:
                logger.debug(f"Emergency provider {provider} also failed: {emergency_error}")
                continue
    
    # If we get here, no providers worked
    raise RuntimeError(
        "Failed to create any LLM client. Please check your configuration and "
        "ensure required dependencies are installed."
    )


def list_available_providers() -> list[str]:
    """
    Get a list of available LLM providers.
    
    Returns:
        List of provider names that can be used
    """
    return list(CLIENT_REGISTRY.keys())


def get_provider_info(provider_name: str) -> dict[str, Any]:
    """
    Get information about a specific provider.
    
    Args:
        provider_name: Name of the provider
        
    Returns:
        Dictionary with provider information
        
    Raises:
        ValueError: If provider is not found
    """
    if provider_name not in CLIENT_REGISTRY:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    client_class = CLIENT_REGISTRY[provider_name]
    
    return {
        'name': provider_name,
        'class': client_class.__name__,
        'module': client_class.__module__,
        'supports_multimodal': hasattr(client_class, 'send_multimodal_message'),
    }