"""Test configuration and fixtures for pytest."""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock
import pytest
import yaml

# Add src to path so we can import modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def temp_vault_dir():
    """Create a temporary directory structure mimicking an Obsidian vault."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        
        # Create standard PARA structure
        (vault_path / "0-QuickNotes").mkdir()
        (vault_path / "1-Projects").mkdir()
        (vault_path / "2-Areas").mkdir()
        (vault_path / "3-Resources").mkdir()
        (vault_path / "4-Archive").mkdir()
        
        # Create some subdirectories for testing
        (vault_path / "0-QuickNotes" / "meetings").mkdir()
        (vault_path / "0-QuickNotes" / "ideas").mkdir()
        (vault_path / "0-QuickNotes" / ".trash").mkdir()  # Should be excluded
        
        yield vault_path


@pytest.fixture
def sample_notes():
    """Provide sample note content for testing."""
    return {
        "simple_note.md": "# Simple Note\n\nThis is a simple test note.",
        "meeting_note.md": "Meeting with team about project X\n- Discussed timeline\n- Action items",
        "unicode_note.md": "# Unicode Test 测试\n\nContent with émojis 🎉 and symbols ∑∏",
        "large_note.md": "# Large Note\n\n" + ("This is a line of text.\n" * 1000),
        "with_frontmatter.md": """---
processed_datetime: "2025-01-01T12:00:00Z"
note_hash: "sha256:abc123"
summary: "Test note"
tags: ["#test"]
---

# Content
This note already has frontmatter."""
    }


@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    return {
        "processing": {
            "max_note_size_kb": 100,
            "max_notes_per_run": 5,
            "file_patterns": ["*.md", "*.txt"],
            "recursive": True,
            "exclude_folders": [".trash", ".obsidian", "templates"]
        },
        "folders": {
            "obsidian_vault_path": "",
            "inbox": "0-QuickNotes",
            "para": {
                "projects": "1-Projects",
                "areas": "2-Areas",
                "resources": "3-Resources",
                "archive": "4-Archive"
            }
        },
        "api_limits": {
            "claude_max_tokens": 4096,
            "claude_model": "claude-3-opus-20240229",
            "retry_attempts": 3,
            "retry_delay_seconds": 1
        }
    }


@pytest.fixture
def mock_claude_client():
    """Mock Claude API client for testing."""
    client = Mock()
    client.send_message = MagicMock(return_value={
        "content": "# Enhanced Note\n\nThis is the enhanced content.",
        "metadata": {
            "summary": "An enhanced test note",
            "tags": ["#test", "#enhanced"],
            "para_category": "resources"
        }
    })
    return client


@pytest.fixture
def mock_config(sample_config, temp_vault_dir):
    """Create a mock configuration object."""
    from config import Config
    
    # Create a mock config with test values
    config = Mock(spec=Config)
    config.obsidian_vault_path = str(temp_vault_dir)
    config.anthropic_api_key = "test-api-key"
    config.max_note_size_kb = sample_config["processing"]["max_note_size_kb"]
    config.max_notes_per_run = sample_config["processing"]["max_notes_per_run"]
    config.file_patterns = sample_config["processing"]["file_patterns"]
    config.recursive = sample_config["processing"]["recursive"]
    config.exclude_folders = sample_config["processing"]["exclude_folders"]
    config.inbox_folder = sample_config["folders"]["inbox"]
    config.para_folders = sample_config["folders"]["para"]
    config.claude_model = sample_config["api_limits"]["claude_model"]
    config.claude_max_tokens = sample_config["api_limits"]["claude_max_tokens"]
    config.retry_attempts = sample_config["api_limits"]["retry_attempts"]
    config.retry_delay_seconds = sample_config["api_limits"]["retry_delay_seconds"]
    
    return config


@pytest.fixture
def create_test_files(temp_vault_dir, sample_notes):
    """Helper fixture to create test files in the vault."""
    def _create_files(folder_path: str = "0-QuickNotes", files: Dict[str, str] = None):
        if files is None:
            files = sample_notes
            
        target_dir = temp_vault_dir / folder_path
        created_files = []
        
        for filename, content in files.items():
            file_path = target_dir / filename
            file_path.write_text(content, encoding='utf-8')
            created_files.append(file_path)
            
        return created_files
    
    return _create_files


@pytest.fixture
def mock_prompt_config():
    """Mock prompt configuration for testing."""
    return {
        "version": "1.0",
        "prompts": {
            "system": "You are a note assistant.",
            "user": "Process this note:\n{note_content}"
        }
    }