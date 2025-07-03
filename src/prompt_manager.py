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
    
    def format_note_prompt(self, note_content: str) -> Dict[str, str]:
        """
        Format a prompt for Claude to process a note.
        
        Args:
            note_content: The note content to process
            
        Returns:
            Dict with system and user prompts
        """
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
            # Strip markdown code blocks if present
            response_clean = response.strip()
            if response_clean.startswith('```json'):
                # Remove ```json from start and ``` from end
                lines = response_clean.split('\n')
                if lines[0].strip() == '```json' and lines[-1].strip() == '```':
                    response_clean = '\n'.join(lines[1:-1])
            elif response_clean.startswith('```'):
                # Remove generic ``` wrapper
                lines = response_clean.split('\n')
                if lines[0].strip() == '```' and lines[-1].strip() == '```':
                    response_clean = '\n'.join(lines[1:-1])
            
            # Try to parse as JSON
            parsed = json.loads(response_clean)
            logger.debug(f"Parsed JSON structure: {parsed}")
            logger.debug(f"Parsed JSON type: {type(parsed)}")
            logger.debug(f"Parsed JSON keys: {parsed.keys() if isinstance(parsed, dict) else 'Not a dict'}")
            
            # Validate structure
            if not isinstance(parsed, dict):
                raise ValueError(f"Response is not a dictionary, got {type(parsed)}")
            
            if 'content' not in parsed:
                raise ValueError(f"Response missing 'content' field. Available keys: {list(parsed.keys())}")
            
            if 'metadata' not in parsed:
                raise ValueError(f"Response missing 'metadata' field. Available keys: {list(parsed.keys())}")
            
            # Pass through metadata as-is, trusting Claude's response
            metadata = parsed['metadata'].copy()
            logger.debug(f"Extracted metadata: {metadata}")
            
            # Only ensure tags are properly formatted if they exist
            if 'tags' in metadata and isinstance(metadata['tags'], list):
                metadata['tags'] = [
                    tag if tag.startswith('#') else f'#{tag}'
                    for tag in metadata['tags']
                ]
            
            # Ensure content is properly formatted (unescape JSON strings)
            content = parsed['content']
            logger.debug(f"Extracted content type: {type(content)}")
            logger.debug(f"Extracted content preview: {content[:100] if isinstance(content, str) else str(content)}")
            
            if isinstance(content, str):
                # Replace escaped newlines with actual newlines
                content = content.replace('\\n', '\n')
            
            return {
                'content': content,
                'metadata': metadata
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Claude response as JSON: {e}")
            logger.debug(f"Raw response that failed to parse: {response}")
            
            # Fallback: return original content with minimal metadata
            return {
                'content': response,
                'metadata': {
                    'summary': 'Failed to parse AI response',
                    'tags': ['#processing-error']
                }
            }