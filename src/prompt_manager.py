"""Prompt management for Claude API interactions."""

import json
import yaml
from pathlib import Path
from typing import Dict, Any
import logging


logger = logging.getLogger(__name__)


class PromptManager:
    """Manages prompts and response parsing for Claude interactions."""
    
    def __init__(self, config):
        """
        Initialize the prompt manager.
        
        Args:
            config: Configuration object containing settings
        """
        self.config = config
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompts from YAML configuration."""
        prompts_path = Path(__file__).parent.parent / 'config' / 'prompts.yaml'
        
        if prompts_path.exists():
            with open(prompts_path, 'r') as f:
                prompt_config = yaml.safe_load(f)
                return prompt_config.get('prompts', {})
        else:
            # Default prompts if config doesn't exist
            return {
                'system': """You are an AI assistant helping to organize and enhance notes.
Your task is to clean up raw notes, add relevant hashtags, and create summaries.

Always respond with a JSON object containing:
- content: The enhanced note content
- metadata: Object with summary and tags""",
                
                'user': """Please process this note:
1. Clean up formatting and grammar
2. Convert to clear bullet points where appropriate
3. Generate 3-5 relevant hashtags
4. Create a one-line summary

Note content:
{note_content}

Respond with JSON in this format:
{{
  "content": "enhanced note content here",
  "metadata": {{
    "summary": "one line summary",
    "tags": ["#tag1", "#tag2"]
  }}
}}"""
            }
    
    def format_note_prompt(self, note_content: str, is_binary: bool = False) -> Dict[str, str]:
        """
        Format a prompt for Claude to process a note.
        
        Args:
            note_content: The note content to process
            is_binary: Whether this is a binary file (image, etc)
            
        Returns:
            Dict with system and user prompts
        """
        if is_binary:
            user_prompt = self.prompts['user'].replace(
                "Note content:\n{note_content}",
                "This is a binary file (possibly an image). Please analyze and describe what you see, then provide organization suggestions."
            )
        else:
            user_prompt = self.prompts['user'].format(note_content=note_content)
        
        return {
            'system': self.prompts['system'],
            'user': user_prompt
        }
    
    def parse_claude_response(self, response: str) -> Dict[str, Any]:
        """
        Parse Claude's response into structured data.
        
        Args:
            response: Raw response from Claude
            
        Returns:
            Dict with 'content' and 'metadata' keys
        """
        try:
            # Try to parse as JSON
            parsed = json.loads(response)
            
            # Validate structure
            if 'content' not in parsed or 'metadata' not in parsed:
                raise ValueError("Response missing required fields")
            
            # Ensure metadata has required fields
            metadata = parsed['metadata']
            metadata.setdefault('summary', '')
            metadata.setdefault('tags', [])
            
            # Ensure tags are properly formatted
            metadata['tags'] = [
                tag if tag.startswith('#') else f'#{tag}'
                for tag in metadata['tags']
            ]
            
            return parsed
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Claude response as JSON: {e}")
            
            # Fallback: return original content with minimal metadata
            return {
                'content': response,
                'metadata': {
                    'summary': 'Failed to parse AI response',
                    'tags': ['#processing-error']
                }
            }