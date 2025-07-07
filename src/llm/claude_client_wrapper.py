"""Wrapper for the existing Claude client to fit the LLM abstraction."""

import logging
from typing import Dict, Any, Optional

try:
    from ..claude_client import ClaudeClient
except ImportError:
    # Fallback for direct imports
    import sys
    from pathlib import Path
    src_path = Path(__file__).parent.parent
    sys.path.insert(0, str(src_path))
    from claude_client import ClaudeClient
from .base_client import BaseLLMClient


logger = logging.getLogger(__name__)


class ClaudeClientWrapper(BaseLLMClient):
    """Wrapper for the existing ClaudeClient to fit the LLM abstraction."""
    
    def __init__(self, config: Any):
        """
        Initialize Claude client wrapper.
        
        Args:
            config: Configuration object with Claude settings
        """
        super().__init__(config)
        
        # Create the original Claude client
        self.claude_client = ClaudeClient(config)
        
        # Extract configuration for compatibility
        self._model = getattr(config, 'claude_model', 'claude-3-opus-20240229')
        self._max_tokens = getattr(config, 'claude_max_tokens', 4096)
        self._retry_attempts = getattr(config, 'retry_attempts', 3)
        
        logger.info(f"Initialized Claude client wrapper with model: {self._model}")
    
    def send_message(self, prompt: Dict[str, str], **kwargs) -> str:
        """
        Send a message using the wrapped Claude client.
        
        Args:
            prompt: Dictionary with 'system' and 'user' prompts
            **kwargs: Additional parameters (max_retries)
            
        Returns:
            Claude's response as a string
        """
        max_retries = kwargs.get('max_retries', self._retry_attempts)
        
        # Use the existing Claude client
        response = self.claude_client.send_message(prompt, max_retries=max_retries)
        
        logger.info(f"Successfully received response from {self.provider_name}")
        return response
    
    def send_multimodal_message(self, prompt: Dict[str, str], image_data: bytes, 
                               image_media_type: str, **kwargs) -> str:
        """
        Send a multimodal message using the wrapped Claude client.
        
        Args:
            prompt: Dictionary with 'system' and 'user' prompts
            image_data: Image data as bytes
            image_media_type: MIME type of image
            **kwargs: Additional parameters
            
        Returns:
            Claude's response as a string
        """
        max_retries = kwargs.get('max_retries', self._retry_attempts)
        
        # Use the existing Claude client's multimodal method
        response = self.claude_client.send_multimodal_message(
            prompt, image_data, image_media_type, max_retries=max_retries
        )
        
        logger.info(f"Successfully received multimodal response from {self.provider_name}")
        return response
    
    @property
    def provider_name(self) -> str:
        """Return the name of the LLM provider."""
        return "anthropic/claude"
    
    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model
    
    def supports_multimodal(self) -> bool:
        """Return whether Claude supports multimodal inputs."""
        # Claude 3 models support vision
        return 'claude-3' in self._model.lower()
    
    def get_usage_info(self) -> Optional[Dict[str, Any]]:
        """
        Get usage information for the last request.
        
        Returns:
            None as the original Claude client doesn't track usage
        """
        return None
    
    def validate_config(self) -> bool:
        """Validate that the Claude client configuration is correct."""
        # Check if we have the required API key
        if not hasattr(self.config, 'anthropic_api_key') or not self.config.anthropic_api_key:
            logger.error("No Anthropic API key found in configuration")
            return False
        
        # Check if model is specified
        if not self._model:
            logger.error("No Claude model specified in configuration")
            return False
        
        return True