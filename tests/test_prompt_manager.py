"""Tests for the prompt manager module."""

import pytest
from unittest.mock import Mock, patch, mock_open
import json
import yaml
from pathlib import Path

from prompt_manager import PromptManager


class TestPromptManager:
    """Test the PromptManager class."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.processing_version = "1.0"
        return config
    
    @pytest.fixture
    def sample_prompts(self):
        """Sample prompt configuration."""
        return {
            "version": "1.0",
            "prompts": {
                "system": "You are a helpful note assistant.",
                "user": "Process this note:\n{note_content}\n\nPlease enhance it."
            }
        }
    
    @pytest.fixture
    def prompt_manager(self, mock_config, sample_prompts):
        """Create a PromptManager instance."""
        with patch('prompt_manager.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=yaml.dump(sample_prompts))):
                return PromptManager(mock_config)
    
    def test_initialization_loads_prompts(self, mock_config, sample_prompts):
        """Test that prompts are loaded during initialization."""
        with patch('prompt_manager.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=yaml.dump(sample_prompts))):
                manager = PromptManager(mock_config)
        
        assert manager.prompts == sample_prompts["prompts"]
    
    def test_initialization_missing_prompt_file(self, mock_config):
        """Test initialization when prompt file is missing uses defaults."""
        with patch('prompt_manager.Path.exists', return_value=False):
            manager = PromptManager(mock_config)
            
        # Should have default prompts
        assert 'system' in manager.prompts
        assert 'user' in manager.prompts
        assert 'AI assistant' in manager.prompts['system']
    
    def test_load_prompts_invalid_yaml(self, mock_config):
        """Test loading invalid YAML."""
        invalid_yaml = "invalid: yaml: content:"
        
        with patch('prompt_manager.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=invalid_yaml)):
                with pytest.raises(yaml.YAMLError):
                    PromptManager(mock_config)
    
    def test_format_note_prompt(self, prompt_manager):
        """Test formatting a note prompt."""
        note_content = "# Test Note\n\nThis is test content."
        
        formatted = prompt_manager.format_note_prompt(note_content)
        
        # Should combine system and user prompts
        expected_user = "Process this note:\n# Test Note\n\nThis is test content.\n\nPlease enhance it."
        assert formatted == {
            "system": "You are a helpful note assistant.",
            "user": expected_user
        }
    
    def test_format_note_prompt_unicode(self, prompt_manager):
        """Test formatting with unicode content."""
        note_content = "# 测试笔记\n\n内容 with émojis 🎉"
        
        formatted = prompt_manager.format_note_prompt(note_content)
        
        assert "测试笔记" in formatted["user"]
        assert "émojis 🎉" in formatted["user"]
    
    def test_format_note_prompt_empty_content(self, prompt_manager):
        """Test formatting with empty content."""
        formatted = prompt_manager.format_note_prompt("")
        
        expected_user = "Process this note:\n\n\nPlease enhance it."
        assert formatted["user"] == expected_user
    
    def test_parse_claude_response_valid_json(self, prompt_manager):
        """Test parsing valid JSON response from Claude."""
        response = json.dumps({
            "content": "# Enhanced Note\n\nImproved content",
            "metadata": {
                "summary": "A test note",
                "tags": ["#test", "#example"],
                "para_category": "resources"
            }
        })
        
        result = prompt_manager.parse_claude_response(response)
        
        assert result["content"] == "# Enhanced Note\n\nImproved content"
        assert result["metadata"]["summary"] == "A test note"
        assert result["metadata"]["tags"] == ["#test", "#example"]
        assert result["metadata"]["para_category"] == "resources"
    
    def test_parse_claude_response_invalid_json(self, prompt_manager):
        """Test parsing invalid JSON response returns fallback."""
        response = "This is not valid JSON {content: no quotes}"
        
        result = prompt_manager.parse_claude_response(response)
        
        # Should return fallback content
        assert result['content'] == response
        assert result['metadata']['summary'] == 'Failed to parse AI response'
        assert result['metadata']['tags'] == ['#processing-error']
    
    def test_parse_claude_response_missing_content(self, prompt_manager):
        """Test parsing response missing required content field returns fallback."""
        response = json.dumps({
            "metadata": {
                "summary": "A note"
            }
            # Missing 'content' field
        })
        
        result = prompt_manager.parse_claude_response(response)
        
        # Should return fallback due to missing content
        assert result['content'] == response
        assert result['metadata']['summary'] == 'Failed to parse AI response'
    
    def test_parse_claude_response_missing_metadata(self, prompt_manager):
        """Test parsing response missing metadata returns fallback."""
        response = json.dumps({
            "content": "Enhanced content"
            # Missing 'metadata' field
        })
        
        result = prompt_manager.parse_claude_response(response)
        
        # Should return fallback due to missing metadata
        assert result['content'] == response
        assert result['metadata']['summary'] == 'Failed to parse AI response'
    
    def test_parse_claude_response_extra_fields(self, prompt_manager):
        """Test parsing response with extra fields (they're ignored)."""
        response = json.dumps({
            "content": "Enhanced content",
            "metadata": {
                "summary": "Test",
                "tags": ["#test"]
            },
            "extra_field": "Will be ignored",
            "another_field": 123
        })
        
        result = prompt_manager.parse_claude_response(response)
        
        # Should only return content and metadata
        assert result["content"] == "Enhanced content"
        assert result["metadata"]["summary"] == "Test"
        assert len(result.keys()) == 2  # Only content and metadata
    
    def test_parse_claude_response_nested_json(self, prompt_manager):
        """Test parsing response with nested JSON structures."""
        response = json.dumps({
            "content": "Content",
            "metadata": {
                "summary": "Summary",
                "tags": ["#tag1", "#tag2"],
                "nested": {
                    "level2": {
                        "level3": "value"
                    }
                }
            }
        })
        
        result = prompt_manager.parse_claude_response(response)
        
        assert result["metadata"]["nested"]["level2"]["level3"] == "value"
    
    def test_prompt_loading_from_config(self, mock_config):
        """Test that prompts are loaded correctly from config."""
        test_prompts = {
            "version": "1.0",
            "prompts": {
                "system": "Custom system prompt",
                "user": "Custom user prompt: {note_content}"
            }
        }
        
        with patch('prompt_manager.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=yaml.dump(test_prompts))):
                manager = PromptManager(mock_config)
        
        assert manager.prompts["system"] == "Custom system prompt"
        assert manager.prompts["user"] == "Custom user prompt: {note_content}"
    
    def test_custom_prompt_template(self, mock_config):
        """Test using custom prompt templates."""
        custom_prompts = {
            "version": "1.0",
            "prompts": {
                "system": "You are Claude, an AI assistant specialized in {specialty}.",
                "user": "Task: {task}\nContent: {note_content}\nInstructions: {instructions}"
            }
        }
        
        with patch('prompt_manager.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=yaml.dump(custom_prompts))):
                manager = PromptManager(mock_config)
        
        # Test that templates are stored correctly
        assert "{specialty}" in manager.prompts["system"]
        assert "{task}" in manager.prompts["user"]
        assert "{note_content}" in manager.prompts["user"]
    
    def test_tag_formatting(self, prompt_manager):
        """Test that tags are properly formatted with # prefix."""
        response = json.dumps({
            "content": "Enhanced content",
            "metadata": {
                "summary": "Test note",
                "tags": ["test", "#already-prefixed", "meeting"]  # Mixed formats
            }
        })
        
        result = prompt_manager.parse_claude_response(response)
        
        # All tags should have # prefix
        expected_tags = ["#test", "#already-prefixed", "#meeting"]
        assert result["metadata"]["tags"] == expected_tags