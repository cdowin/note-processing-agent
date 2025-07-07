"""Tests for the LLM abstraction layer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from llm.base_client import BaseLLMClient
from llm.factory import create_llm_client, create_llm_client_with_fallback, list_available_providers
from llm.claude_client_wrapper import ClaudeClientWrapper


class TestBaseLLMClient:
    """Test the base LLM client abstract class."""
    
    def test_abstract_methods_raise_not_implemented(self):
        """Test that abstract methods raise NotImplementedError."""
        # Can't instantiate abstract class directly
        with pytest.raises(TypeError):
            BaseLLMClient(Mock())
    
    def test_supports_multimodal_default(self):
        """Test default multimodal support check."""
        # Create a concrete implementation for testing
        class TestClient(BaseLLMClient):
            def send_message(self, prompt, **kwargs):
                return "test"
            
            def send_multimodal_message(self, prompt, image_data, image_media_type, **kwargs):
                return "test"
            
            @property
            def provider_name(self):
                return "test"
            
            @property
            def model_name(self):
                return "test-model"
        
        client = TestClient(Mock())
        assert client.supports_multimodal() is True
    
    def test_get_usage_info_default(self):
        """Test default usage info returns None."""
        class TestClient(BaseLLMClient):
            def send_message(self, prompt, **kwargs):
                return "test"
            
            def send_multimodal_message(self, prompt, image_data, image_media_type, **kwargs):
                return "test"
            
            @property
            def provider_name(self):
                return "test"
            
            @property
            def model_name(self):
                return "test-model"
        
        client = TestClient(Mock())
        assert client.get_usage_info() is None
    
    def test_validate_config_default(self):
        """Test default config validation."""
        class TestClient(BaseLLMClient):
            def send_message(self, prompt, **kwargs):
                return "test"
            
            def send_multimodal_message(self, prompt, image_data, image_media_type, **kwargs):
                return "test"
            
            @property
            def provider_name(self):
                return "test"
            
            @property
            def model_name(self):
                return "test-model"
        
        # Test with valid config
        config = Mock()
        config.llm = {"test": "value"}
        client = TestClient(config)
        assert client.validate_config() is True
        
        # Test with invalid config
        config_invalid = Mock()
        config_invalid.llm = None
        client_invalid = TestClient(config_invalid)
        assert client_invalid.validate_config() is False


class TestClaudeClientWrapper:
    """Test the Claude client wrapper."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.anthropic_api_key = "test-key"
        config.claude_model = "claude-3-opus-20240229"
        config.claude_max_tokens = 4096
        config.retry_attempts = 3
        return config
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_initialization(self, mock_claude_client_class, mock_config):
        """Test Claude wrapper initialization."""
        wrapper = ClaudeClientWrapper(mock_config)
        
        # Check that original Claude client was created
        mock_claude_client_class.assert_called_once_with(mock_config)
        assert wrapper.claude_client == mock_claude_client_class.return_value
        assert wrapper.model_name == "claude-3-opus-20240229"
        assert wrapper.provider_name == "anthropic/claude"
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_send_message(self, mock_claude_client_class, mock_config):
        """Test sending message through wrapper."""
        mock_claude_client = mock_claude_client_class.return_value
        mock_claude_client.send_message.return_value = "Enhanced response"
        
        wrapper = ClaudeClientWrapper(mock_config)
        
        prompt = {"user": "Test prompt", "system": "System prompt"}
        result = wrapper.send_message(prompt)
        
        mock_claude_client.send_message.assert_called_once_with(prompt, max_retries=3)
        assert result == "Enhanced response"
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_send_multimodal_message(self, mock_claude_client_class, mock_config):
        """Test sending multimodal message through wrapper."""
        mock_claude_client = mock_claude_client_class.return_value
        mock_claude_client.send_multimodal_message.return_value = "Multimodal response"
        
        wrapper = ClaudeClientWrapper(mock_config)
        
        prompt = {"user": "Describe this image"}
        image_data = b"fake image data"
        image_type = "image/jpeg"
        
        result = wrapper.send_multimodal_message(prompt, image_data, image_type)
        
        mock_claude_client.send_multimodal_message.assert_called_once_with(
            prompt, image_data, image_type, max_retries=3
        )
        assert result == "Multimodal response"
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_supports_multimodal(self, mock_claude_client_class, mock_config):
        """Test multimodal support detection."""
        wrapper = ClaudeClientWrapper(mock_config)
        
        # Claude 3 models support multimodal
        assert wrapper.supports_multimodal() is True
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_validate_config_valid(self, mock_claude_client_class, mock_config):
        """Test config validation with valid config."""
        wrapper = ClaudeClientWrapper(mock_config)
        assert wrapper.validate_config() is True
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_validate_config_missing_api_key(self, mock_claude_client_class, mock_config):
        """Test config validation with missing API key."""
        mock_config.anthropic_api_key = ""
        wrapper = ClaudeClientWrapper(mock_config)
        assert wrapper.validate_config() is False
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_validate_config_missing_model(self, mock_claude_client_class, mock_config):
        """Test config validation with missing model."""
        wrapper = ClaudeClientWrapper(mock_config)
        wrapper._model = ""
        assert wrapper.validate_config() is False


class TestLLMFactory:
    """Test the LLM factory functions."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.llm = {
            'primary_provider': 'claude_direct',
            'fallback_provider': 'litellm',
            'providers': {
                'claude_direct': {'model': 'claude-3-opus'},
                'litellm': {'model': 'claude-3-sonnet'}
            }
        }
        config.anthropic_api_key = "test-key"
        config.claude_model = "claude-3-opus-20240229"
        config.claude_max_tokens = 4096
        config.retry_attempts = 3
        return config
    
    def test_list_available_providers(self):
        """Test listing available providers."""
        providers = list_available_providers()
        assert 'claude_direct' in providers
        assert 'litellm' in providers
        assert isinstance(providers, list)
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_create_llm_client_claude_direct(self, mock_claude_client_class, mock_config):
        """Test creating Claude direct client."""
        client = create_llm_client(mock_config, 'claude_direct')
        
        assert isinstance(client, ClaudeClientWrapper)
        assert client.provider_name == "anthropic/claude"
        mock_claude_client_class.assert_called_once_with(mock_config)
    
    def test_create_llm_client_unsupported_provider(self, mock_config):
        """Test creating client with unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_client(mock_config, 'unsupported_provider')
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_create_llm_client_from_config(self, mock_claude_client_class, mock_config):
        """Test creating client using config primary provider."""
        mock_config.llm['primary_provider'] = 'claude_direct'
        
        client = create_llm_client(mock_config)
        
        assert isinstance(client, ClaudeClientWrapper)
        assert client.provider_name == "anthropic/claude"
    
    @patch('llm.claude_client_wrapper.ClaudeClient')
    def test_create_llm_client_with_fallback_success(self, mock_claude_client_class, mock_config):
        """Test creating client with fallback - primary succeeds."""
        client = create_llm_client_with_fallback(mock_config)
        
        assert isinstance(client, ClaudeClientWrapper)
        assert client.provider_name == "anthropic/claude"
    
    @patch('llm.factory.create_llm_client')
    def test_create_llm_client_with_fallback_uses_fallback(self, mock_create_client, mock_config):
        """Test creating client with fallback - primary fails, fallback succeeds."""
        # Mock primary provider failure, fallback success
        mock_primary_client = Mock()
        mock_fallback_client = Mock()
        
        def side_effect(config, provider=None):
            if provider == 'claude_direct':
                raise Exception("Primary failed")
            elif provider == 'litellm':
                return mock_fallback_client
            else:
                raise Exception("Unknown provider")
        
        mock_create_client.side_effect = side_effect
        
        client = create_llm_client_with_fallback(mock_config)
        
        assert client == mock_fallback_client
        assert mock_create_client.call_count == 2  # Primary + fallback
    
    @patch('llm.factory.create_llm_client')
    def test_create_llm_client_with_fallback_all_fail(self, mock_create_client, mock_config):
        """Test creating client with fallback - all providers fail."""
        mock_create_client.side_effect = Exception("All providers failed")
        
        with pytest.raises(RuntimeError, match="Failed to create any LLM client"):
            create_llm_client_with_fallback(mock_config)