"""Base abstract class for LLM clients."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    def __init__(self, config: Any):
        """
        Initialize the LLM client.
        
        Args:
            config: Configuration object containing LLM settings
        """
        self.config = config
    
    @abstractmethod
    def send_message(self, prompt: Dict[str, str], **kwargs) -> str:
        """
        Send a message to the LLM and get response.
        
        Args:
            prompt: Dictionary with 'system' and 'user' prompts
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            LLM's response as a string
            
        Raises:
            Exception: If the LLM call fails
        """
        pass
    
    @abstractmethod
    def send_multimodal_message(self, prompt: Dict[str, str], image_data: bytes, 
                               image_media_type: str, **kwargs) -> str:
        """
        Send a multimodal message (text + image) to the LLM.
        
        Args:
            prompt: Dictionary with 'system' and 'user' prompts
            image_data: Image data as bytes
            image_media_type: MIME type of image (e.g., "image/jpeg")
            **kwargs: Additional parameters
            
        Returns:
            LLM's response as a string
            
        Raises:
            Exception: If the LLM call fails
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the LLM provider."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name being used."""
        pass
    
    def supports_multimodal(self) -> bool:
        """
        Return whether this client supports multimodal inputs.
        
        Returns:
            True if multimodal is supported, False otherwise
        """
        try:
            # Try to get the method - if it exists and isn't abstract, it's supported
            method = getattr(self.__class__, 'send_multimodal_message')
            return not getattr(method, '__isabstractmethod__', False)
        except AttributeError:
            return False
    
    def get_usage_info(self) -> Optional[Dict[str, Any]]:
        """
        Get usage information for the last request (tokens, cost, etc.).
        
        Returns:
            Dictionary with usage information, or None if not available
        """
        return None
    
    def validate_config(self) -> bool:
        """
        Validate that the client configuration is correct.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        return hasattr(self.config, 'llm') and self.config.llm is not None