"""Claude API client implementation."""

import base64
import logging
import time
from typing import Dict, Union, List, Literal
import anthropic
from anthropic import APIError, RateLimitError
from anthropic.types import ImageBlockParam, TextBlockParam, Base64ImageSourceParam

# Constants
DEFAULT_MAX_RETRIES = 3
CLAUDE_TEMPERATURE = 0.3
BACKOFF_BASE = 2

# Type alias for supported image types
ImageMediaType = Literal['image/jpeg', 'image/png', 'image/gif', 'image/webp']


logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for interacting with Claude API."""
    
    def __init__(self, api_key: str, config):
        """
        Initialize Claude client.
        
        Args:
            api_key: Anthropic API key
            config: Configuration object with model and token settings
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.config = config
    
    def send_message(self, prompt: Dict[str, str], max_retries: int = DEFAULT_MAX_RETRIES) -> str:
        """
        Send a message to Claude and get response.
        
        Args:
            prompt: Dictionary with 'system' and 'user' prompts
            max_retries: Maximum number of retry attempts
            
        Returns:
            Claude's response as a string
        """
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Create message
                message = self.client.messages.create(
                    model=self.config.claude_model,
                    max_tokens=self.config.claude_max_tokens,
                    temperature=CLAUDE_TEMPERATURE,  # Lower temperature for more consistent formatting
                    system=prompt.get('system', ''),
                    messages=[
                        {
                            "role": "user",
                            "content": prompt.get('user', '')
                        }
                    ]
                )
                
                # Extract text from response - handle different content types
                response_text = self._extract_text_from_response(message.content)
                logger.info(f"Successfully received response from Claude")
                return response_text
                
            except RateLimitError as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Max retries exceeded for rate limit: {e}")
                    raise
                
                # Exponential backoff
                wait_time = (BACKOFF_BASE ** retry_count) * 1.0
                logger.warning(f"Rate limited, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
            except APIError as e:
                logger.error(f"Claude API error: {e}")
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error calling Claude API: {e}")
                raise
        
        # This should never be reached due to the raise statements above
        raise RuntimeError("Exceeded maximum retries without successful response")
    
    def send_multimodal_message(self, prompt: Dict[str, str], image_data: bytes, 
                               image_media_type: str, max_retries: int = DEFAULT_MAX_RETRIES) -> str:
        """
        Send a multimodal message (text + image) to Claude.
        
        Args:
            prompt: Dictionary with 'system' and 'user' prompts
            image_data: Image data as bytes
            image_media_type: MIME type of image (e.g., "image/jpeg")
            max_retries: Maximum number of retry attempts
            
        Returns:
            Claude's response as a string
        """
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Encode image data to base64
                image_b64 = base64.b64encode(image_data).decode('utf-8')
                
                # Validate and cast media type
                if image_media_type not in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']:
                    logger.warning(f"Unsupported media type: {image_media_type}, defaulting to image/jpeg")
                    validated_media_type: ImageMediaType = 'image/jpeg'
                else:
                    validated_media_type = image_media_type  # type: ignore[assignment]
                
                # Create properly typed content blocks
                image_source = Base64ImageSourceParam(
                    type="base64",
                    media_type=validated_media_type,
                    data=image_b64
                )
                
                content_blocks: List[Union[ImageBlockParam, TextBlockParam]] = [
                    ImageBlockParam(
                        type="image",
                        source=image_source
                    ),
                    TextBlockParam(
                        type="text",
                        text=prompt.get('user', '')
                    )
                ]
                
                # Create message with image
                message = self.client.messages.create(
                    model=self.config.claude_model,
                    max_tokens=self.config.claude_max_tokens,
                    temperature=CLAUDE_TEMPERATURE,
                    system=prompt.get('system', ''),
                    messages=[
                        {
                            "role": "user",
                            "content": content_blocks
                        }
                    ]
                )
                
                # Extract text from response
                response_text = self._extract_text_from_response(message.content)
                logger.info(f"Successfully received multimodal response from Claude")
                return response_text
                
            except RateLimitError as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Max retries exceeded for rate limit: {e}")
                    raise
                
                # Exponential backoff
                wait_time = (BACKOFF_BASE ** retry_count) * 1.0
                logger.warning(f"Rate limited, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
            except APIError as e:
                logger.error(f"Claude API error: {e}")
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error calling Claude API: {e}")
                raise
        
        # This should never be reached due to the raise statements above
        raise RuntimeError("Exceeded maximum retries without successful response")
    
    def _extract_text_from_response(self, content) -> str:
        """
        Extract text from Claude's response content, handling different block types.
        
        Args:
            content: Response content from Claude API
            
        Returns:
            Extracted text content
        """
        if not content:
            return ""
        
        # Handle list of content blocks
        for block in content:
            # Check if it's a TextBlock
            if hasattr(block, 'text') and hasattr(block, 'type') and block.type == 'text':
                return block.text
            # Fallback for other types that might have text
            elif hasattr(block, 'text'):
                return block.text
        
        # If no text block found, return empty string
        logger.warning("No text content found in Claude response")
        return ""