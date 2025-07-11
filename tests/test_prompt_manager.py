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
        """Sample prompt configuration matching the actual prompts.yaml structure."""
        return {
            "version": "1.0",
            "prompts": {
                "system": "You are an AI assistant helping to organize and enhance notes.\nYour task is to clean up raw notes, add relevant hashtags, and create summaries.\n\nAlways respond with a JSON object containing:\n- content: The enhanced note content\n- metadata: Object with summary, tags, and other frontmatter\n",
                "user": "Please process this note. Leave as much of the original text as appropriate. You are to keep the voice of the author and only apply a light touch.:\n1. Clean up formatting and grammar.\n2. Add clear bullet points where appropriate.\n3. Anywhere you see the potential for future expansion, a clear citation, or to challenge the author with questions, make an inline note using (()) to denote your thoughts.\n4. If you see any text noted between (()), expand the thoughts or text outlined. These are notes from the user for you to contemplate.\n5. If you see any obvious literary references, names, published articles, or published media, do some research to find those references and create appropriate links, hashtags, or a reference section in the document.\n4. Generate 3-5 relevant hashtags.\n5. Create a one-line summary.\n6. Create a one-line takeaway describing why this note is important or how it links to other notes/thoughts.\n7. If the note has any tags (#) in the body, add those to the metadata returned. If the tags are embedded in text, leave them alone, otherwise if they're standalone remove them from the enhanced note.\n\nNote content:\n{note_content}\n\nRespond with JSON in this format:\n{{\n  \"content\": \"enhanced note content here\",\n  \"metadata\": {{\n    \"summary\": \"one line summary\",\n    \"takeaway\": \"one line takeaway\",\n    \"tags\": [\"#tag1\", \"#tag2\"]\n  }}\n}}"
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
        assert "system" in formatted
        assert "user" in formatted
        assert note_content in formatted["user"]
        assert "AI assistant helping to organize" in formatted["system"]
        assert "enhanced note content" in formatted["system"]
    
    def test_format_note_prompt_unicode(self, prompt_manager):
        """Test formatting with unicode content."""
        note_content = "# 测试笔记\n\n内容 with émojis 🎉"
        
        formatted = prompt_manager.format_note_prompt(note_content)
        
        assert "测试笔记" in formatted["user"]
        assert "émojis 🎉" in formatted["user"]
    
    def test_format_note_prompt_empty_content(self, prompt_manager):
        """Test formatting with empty content."""
        formatted = prompt_manager.format_note_prompt("")
        
        # Should still contain the prompt structure
        assert "system" in formatted
        assert "user" in formatted
        assert "Note content:" in formatted["user"]
    
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
    
    def test_prompt_expansion_functionality(self, prompt_manager):
        """Test that prompts include expansion instructions for (()) markers."""
        note_content = "Test note with ((expand this thought)) marker"
        
        formatted = prompt_manager.format_note_prompt(note_content)
        
        # Should include instructions for handling (()) markers
        assert "(()" in formatted["user"]
        assert "expand the thoughts" in formatted["user"]
    
    def test_prompt_reference_extraction(self, prompt_manager):
        """Test that prompts include reference extraction instructions."""
        note_content = "Reading Marcus Aurelius's Meditations"
        
        formatted = prompt_manager.format_note_prompt(note_content)
        
        # Should include instructions for reference extraction
        assert "literary references" in formatted["user"]
        assert "research" in formatted["user"]
    
    def test_parse_response_with_references(self, prompt_manager):
        """Test parsing response that includes a references section."""
        response = json.dumps({
            "content": "Enhanced content\n\n**References:**\n- Book: Title by Author\n- Article: Title",
            "metadata": {
                "summary": "Test with references",
                "tags": ["#test", "#references"]
            }
        })
        
        result = prompt_manager.parse_claude_response(response)
        
        assert "**References:**" in result["content"]
        assert "Book: Title by Author" in result["content"]
        assert result["metadata"]["tags"] == ["#test", "#references"]
    
    def test_parse_response_with_expanded_thoughts(self, prompt_manager):
        """Test parsing response with expanded (()) thoughts."""
        response = json.dumps({
            "content": "Note content ((This is an expanded thought with detailed analysis))",
            "metadata": {
                "summary": "Note with expanded thoughts",
                "tags": ["#expanded", "#analysis"]
            }
        })
        
        result = prompt_manager.parse_claude_response(response)
        
        assert "((This is an expanded thought with detailed analysis))" in result["content"]
        assert result["metadata"]["tags"] == ["#expanded", "#analysis"]
    
    def test_parse_response_with_takeaway_field(self, prompt_manager):
        """Test parsing response that includes takeaway field."""
        response = json.dumps({
            "content": "Enhanced content",
            "metadata": {
                "summary": "Test note",
                "takeaway": "This is why the note is important",
                "tags": ["#test"]
            }
        })
        
        result = prompt_manager.parse_claude_response(response)
        
        assert result["metadata"]["takeaway"] == "This is why the note is important"
        assert result["metadata"]["summary"] == "Test note"
        assert result["metadata"]["tags"] == ["#test"]
    
    def test_full_integration_new_features(self, prompt_manager):
        """Test integration of all new prompt features together."""
        # Complex note with multiple features
        note_content = """Just read "The Power of Now" by Eckhart Tolle. 
        ((Compare with Buddhist mindfulness practices))
        
        Key insights from Marcus Aurelius's Meditations:
        - Focus on present moment
        - Control what you can control
        
        ((Need to research neuroscience of meditation))"""
        
        formatted = prompt_manager.format_note_prompt(note_content)
        
        # Verify all new instructions are included
        user_prompt = formatted["user"]
        assert "expand the thoughts" in user_prompt
        assert "literary references" in user_prompt
        assert "research" in user_prompt
        assert "takeaway" in user_prompt
        assert note_content in user_prompt
        
        # Test parsing complex response
        complex_response = json.dumps({
            "content": """Enhanced note with ((expanded thoughts about Buddhist practices and their neurological effects)) and proper references.
            
            **References:**
            - Tolle, Eckhart. *The Power of Now*
            - Aurelius, Marcus. *Meditations*""",
            "metadata": {
                "summary": "Comparison of Western and Eastern mindfulness approaches",
                "takeaway": "Both traditions emphasize present-moment awareness",
                "tags": ["#mindfulness", "#philosophy", "#research"]
            }
        })
        
        result = prompt_manager.parse_claude_response(complex_response)
        
        # Verify all components are preserved
        assert "((expanded thoughts about Buddhist practices" in result["content"]
        assert "**References:**" in result["content"]
        assert "Tolle, Eckhart" in result["content"]
        assert result["metadata"]["takeaway"] == "Both traditions emphasize present-moment awareness"
        assert len(result["metadata"]["tags"]) == 3
        assert all(tag.startswith("#") for tag in result["metadata"]["tags"])