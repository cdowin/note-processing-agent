"""LiteLLM client implementation for unified LLM access."""

import base64
import logging
import time
from typing import Dict, Any, Optional

try:
    import litellm
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

from .base_client import BaseLLMClient


logger = logging.getLogger(__name__)


class LiteLLMClient(BaseLLMClient):
    """LiteLLM client for unified access to multiple LLM providers."""
    
    def __init__(self, config: Any):
        """
        Initialize LiteLLM client.
        
        Args:
            config: Configuration object with LLM settings
        """
        super().__init__(config)
        
        if not LITELLM_AVAILABLE:
            raise ImportError(
                "LiteLLM is not installed. Install it with: pip install litellm"
            )
        
        # Extract LiteLLM configuration
        self.llm_config = getattr(config, 'llm', {})
        self.provider_config = self.llm_config.get('providers', {}).get('litellm', {})
        
        # Core parameters
        self._model = self.provider_config.get('model', 'claude-3-5-sonnet-20241022')
        self._max_tokens = self.provider_config.get('max_tokens', 4096)
        self._temperature = self.provider_config.get('temperature', 0.3)
        self._retry_attempts = self.provider_config.get('retry_attempts', 3)
        self._retry_delay = self.provider_config.get('retry_delay_seconds', 2)
        
        # Optional API key override (if not using environment variables)
        api_key = self.provider_config.get('api_key')
        if api_key:
            # Set API key for the specific provider
            provider_name = self._extract_provider_from_model(self._model)
            self._set_api_key(provider_name, api_key)
        
        # Configure LiteLLM settings
        litellm.set_verbose = self.provider_config.get('verbose', False)
        
        # Track usage for the last request
        self._last_usage = None
        
        logger.info(f"Initialized LiteLLM client with model: {self._model}")
    
    def send_message(self, prompt: Dict[str, str], **kwargs) -> str:
        """
        Send a message using LiteLLM.
        
        Args:
            prompt: Dictionary with 'system' and 'user' prompts
            **kwargs: Additional parameters to override defaults
            
        Returns:
            LLM's response as a string
        """
        messages = []
        
        # Add system message if provided
        if prompt.get('system'):
            messages.append({
                "role": "system",
                "content": prompt['system']
            })
        
        # Add user message
        messages.append({
            "role": "user", 
            "content": prompt.get('user', '')
        })
        
        # Prepare completion parameters
        completion_kwargs = {
            'model': self._model,
            'messages': messages,
            'max_tokens': kwargs.get('max_tokens', self._max_tokens),
            'temperature': kwargs.get('temperature', self._temperature),
        }
        
        # Add any additional provider-specific parameters
        extra_params = kwargs.get('extra_params', {})
        completion_kwargs.update(extra_params)
        
        # Execute with retry logic
        for attempt in range(self._retry_attempts + 1):
            try:
                response = completion(**completion_kwargs)
                
                # Store usage information
                self._last_usage = getattr(response, 'usage', None)
                
                # Extract response content
                content = response.choices[0].message.content
                logger.info(f"Successfully received response from {self.provider_name}")
                return content
                
            except Exception as e:
                attempt_num = attempt + 1
                if attempt_num > self._retry_attempts:
                    logger.error(f"Max retries exceeded for {self.provider_name}: {e}")
                    raise
                
                wait_time = self._retry_delay * (2 ** attempt)
                logger.warning(f"LLM request failed (attempt {attempt_num}/{self._retry_attempts + 1}), "
                             f"retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        raise RuntimeError("Exceeded maximum retries without successful response")
    
    def send_multimodal_message(self, prompt: Dict[str, str], image_data: bytes, 
                               image_media_type: str, **kwargs) -> str:
        """
        Send a multimodal message (text + image) using LiteLLM.
        
        Args:
            prompt: Dictionary with 'system' and 'user' prompts
            image_data: Image data as bytes
            image_media_type: MIME type of image (e.g., "image/jpeg")
            **kwargs: Additional parameters
            
        Returns:
            LLM's response as a string
        """
        # Check if the current model supports multimodal
        if not self._model_supports_vision():
            raise ValueError(f"Model {self._model} does not support vision/multimodal inputs")
        
        messages = []
        
        # Add system message if provided
        if prompt.get('system'):
            messages.append({
                "role": "system",
                "content": prompt['system']
            })
        
        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        image_url = f"data:{image_media_type};base64,{image_b64}"
        
        # Create multimodal user message
        user_content = [
            {
                "type": "text",
                "text": prompt.get('user', '')
            },
            {
                "type": "image_url",
                "image_url": {"url": image_url}
            }
        ]
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        # Prepare completion parameters
        completion_kwargs = {
            'model': self._model,
            'messages': messages,
            'max_tokens': kwargs.get('max_tokens', self._max_tokens),
            'temperature': kwargs.get('temperature', self._temperature),
        }
        
        # Execute with retry logic
        for attempt in range(self._retry_attempts + 1):
            try:
                response = completion(**completion_kwargs)
                
                # Store usage information
                self._last_usage = getattr(response, 'usage', None)
                
                # Extract response content
                content = response.choices[0].message.content
                logger.info(f"Successfully received multimodal response from {self.provider_name}")
                return content
                
            except Exception as e:
                attempt_num = attempt + 1
                if attempt_num > self._retry_attempts:
                    logger.error(f"Max retries exceeded for multimodal {self.provider_name}: {e}")
                    raise
                
                wait_time = self._retry_delay * (2 ** attempt)
                logger.warning(f"Multimodal LLM request failed (attempt {attempt_num}/{self._retry_attempts + 1}), "
                             f"retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        raise RuntimeError("Exceeded maximum retries without successful response")
    
    @property
    def provider_name(self) -> str:
        """Return the name of the LLM provider."""
        provider = self._extract_provider_from_model(self._model)
        return f"litellm/{provider}"
    
    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model
    
    def supports_multimodal(self) -> bool:
        """Return whether the current model supports multimodal inputs."""
        return self._model_supports_vision()
    
    def get_usage_info(self) -> Optional[Dict[str, Any]]:
        """
        Get usage information for the last request.
        
        Returns:
            Dictionary with usage information, or None if not available
        """
        if self._last_usage is None:
            return None
        
        return {
            'prompt_tokens': getattr(self._last_usage, 'prompt_tokens', None),
            'completion_tokens': getattr(self._last_usage, 'completion_tokens', None),
            'total_tokens': getattr(self._last_usage, 'total_tokens', None),
        }
    
    def validate_config(self) -> bool:
        """Validate that the client configuration is correct."""
        if not super().validate_config():
            return False
        
        # Check if model is specified
        if not self._model:
            logger.error("No model specified in LiteLLM configuration")
            return False
        
        return True
    
    def _extract_provider_from_model(self, model: str) -> str:
        """Extract the provider name from the model string."""
        # LiteLLM model naming conventions
        if model.startswith('claude'):
            return 'anthropic'
        elif model.startswith('gpt'):
            return 'openai'
        elif model.startswith('gemini'):
            return 'google'
        elif model.startswith('llama'):
            return 'meta'
        elif '/' in model:
            # Format like "anthropic/claude-3-opus" or "openai/gpt-4"
            return model.split('/')[0]
        else:
            # Default fallback
            return 'unknown'
    
    def _set_api_key(self, provider: str, api_key: str):
        """Set API key for a specific provider."""
        # LiteLLM uses environment variables or direct assignment
        if provider == 'anthropic':
            import os
            os.environ['ANTHROPIC_API_KEY'] = api_key
        elif provider == 'openai':
            import os
            os.environ['OPENAI_API_KEY'] = api_key
        elif provider == 'google':
            import os
            os.environ['GOOGLE_API_KEY'] = api_key
        # Add more providers as needed
    
    def _model_supports_vision(self) -> bool:
        """Check if the current model supports vision/multimodal inputs."""
        vision_models = [
            'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku',
            'claude-3-5-sonnet', 'claude-3-5-haiku',
            'gpt-4-vision-preview', 'gpt-4o', 'gpt-4o-mini',
            'gemini-pro-vision', 'gemini-1.5-pro', 'gemini-1.5-flash'
        ]
        
        # Check if any vision model name is contained in the current model
        return any(vm in self._model.lower() for vm in vision_models)