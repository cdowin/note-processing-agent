"""Tests for configuration management."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import yaml

from config import Config


class TestConfig:
    """Test the Config class."""
    
    @pytest.fixture
    def env_vars(self):
        """Set up environment variables for testing."""
        original_env = {}
        test_vars = {
            'ANTHROPIC_API_KEY': 'test-api-key-123',
            'OBSIDIAN_VAULT_PATH': '/test/obsidian/vault'
        }
        
        # Save original values
        for key in test_vars:
            original_env[key] = os.environ.get(key)
            
        # Set test values
        for key, value in test_vars.items():
            os.environ[key] = value
            
        yield test_vars
        
        # Restore original values
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    @pytest.fixture
    def temp_config_file(self, sample_config):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        os.unlink(temp_path)
    
    def test_load_from_environment(self, env_vars):
        """Test loading configuration from environment variables."""
        with patch('config.Path.exists', return_value=False):  # No config file
            config = Config()
        
        assert config.anthropic_api_key == 'test-api-key-123'
        assert config.obsidian_vault_path == '/test/obsidian/vault'
    
    def test_missing_anthropic_key(self):
        """Test error when ANTHROPIC_API_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('config.Path.exists', return_value=False):
                with pytest.raises(ValueError, match="ANTHROPIC_API_KEY environment variable is required"):
                    Config()
    
    def test_missing_obsidian_path(self):
        """Test error when OBSIDIAN_VAULT_PATH is missing."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}, clear=True):
            with patch('config.Path.exists', return_value=False):
                with pytest.raises(ValueError, match="OBSIDIAN_VAULT_PATH environment variable is required"):
                    Config()
    
    def test_load_from_yaml(self, env_vars, sample_config):
        """Test loading settings from YAML file."""
        # Create a mock path that returns our sample config
        with patch('config.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                with patch('yaml.safe_load', return_value=sample_config):
                    config = Config()
        
        # Check processing settings
        assert config.max_note_size_kb == 100
        assert config.max_notes_per_run == 5
        assert config.file_patterns == ["*.md", "*.txt"]
        assert config.recursive == True
        assert config.exclude_folders == [".trash", ".obsidian", "templates"]
        
        # Check folder settings
        assert config.inbox_folder == "0-QuickNotes"
        assert config.para_folders["projects"] == "1-Projects"
        assert config.para_folders["areas"] == "2-Areas"
        
        # Check API settings
        assert config.claude_max_tokens == 4096
        assert config.claude_model == "claude-3-opus-20240229"
        assert config.retry_attempts == 3
        assert config.retry_delay_seconds == 1
    
    def test_default_values(self, env_vars):
        """Test default values when no config file exists."""
        with patch('config.Path.exists', return_value=False):
            config = Config()
        
        # Check defaults
        assert config.max_note_size_kb == 10000
        assert config.max_notes_per_run == 10
        assert config.file_patterns == ["*.md", "*.txt", "*.org", "*.rst", "*.markdown"]
        assert config.recursive == True
        assert config.exclude_folders == [".obsidian", ".trash", "templates", ".git"]
        assert config.claude_max_tokens == 4096
        assert config.processing_version == "1.0"
    
    def test_partial_yaml_config(self, env_vars):
        """Test loading partial YAML config (missing some sections)."""
        partial_config = {
            "processing": {
                "max_note_size_kb": 50
            }
            # Missing other sections
        }
        
        with patch('config.Path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with patch('yaml.safe_load', return_value=partial_config):
                    config = Config()
        
        # Changed value
        assert config.max_note_size_kb == 50
        
        # Defaults for missing values
        assert config.max_notes_per_run == 10
        assert config.inbox_folder == "0-QuickNotes"
        assert config.claude_model == "claude-sonnet-4-20250514"
    
    def test_vault_path_override_from_yaml(self, env_vars):
        """Test that vault path can be overridden from YAML."""
        config_with_override = {
            "folders": {
                "obsidian_vault_path": "/yaml/override/path"
            }
        }
        
        with patch('config.Path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with patch('yaml.safe_load', return_value=config_with_override):
                    config = Config()
        
        # Should use YAML value instead of environment
        assert config.obsidian_vault_path == "/yaml/override/path"
    
    def test_empty_vault_path_uses_env(self, env_vars):
        """Test that empty vault path in YAML uses environment variable."""
        config_with_empty_path = {
            "folders": {
                "obsidian_vault_path": ""  # Empty string
            }
        }
        
        with patch('config.Path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with patch('yaml.safe_load', return_value=config_with_empty_path):
                    config = Config()
        
        # Should use environment value
        assert config.obsidian_vault_path == '/test/obsidian/vault'
    
    def test_config_types(self, env_vars):
        """Test that configuration values have correct types."""
        with patch('config.Path.exists', return_value=False):
            config = Config()
        
        # Check types
        assert isinstance(config.anthropic_api_key, str)
        assert isinstance(config.obsidian_vault_path, str)
        assert isinstance(config.max_note_size_kb, int)
        assert isinstance(config.max_notes_per_run, int)
        assert isinstance(config.file_patterns, list)
        assert isinstance(config.recursive, bool)
        assert isinstance(config.exclude_folders, list)
        assert isinstance(config.inbox_folder, str)
        assert isinstance(config.para_folders, dict)
        assert isinstance(config.claude_model, str)
        assert isinstance(config.claude_max_tokens, int)
        assert isinstance(config.retry_attempts, int)
        assert isinstance(config.retry_delay_seconds, int)
        assert isinstance(config.processing_version, str)
    
    def test_para_folders_structure(self, env_vars):
        """Test PARA folders have correct structure."""
        with patch('config.Path.exists', return_value=False):
            config = Config()
        
        assert "projects" in config.para_folders
        assert "areas" in config.para_folders
        assert "resources" in config.para_folders
        assert "archive" in config.para_folders
        
        # Check all values are strings
        for key, value in config.para_folders.items():
            assert isinstance(key, str)
            assert isinstance(value, str)