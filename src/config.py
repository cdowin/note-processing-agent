"""Configuration management for the note assistant."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """Application configuration."""
    
    # Environment variables
    anthropic_api_key: str
    obsidian_vault_path: str
    
    # Processing settings
    max_note_size_kb: int = 10000
    max_notes_per_run: int = 10
    file_patterns: List[str] = field(default_factory=lambda: ["*"])
    
    # Folder configuration
    inbox_folder: str = "0-QuickNotes"
    para_folders: Dict[str, str] = field(default_factory=lambda: {
        "projects": "1-Projects",
        "areas": "2-Areas",
        "resources": "3-Resources",
        "archive": "4-Archive"
    })
    
    # API settings
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096
    retry_attempts: int = 1
    retry_delay_seconds: int = 2
    
    # Versioning
    processing_version: str = "1.0"
    
    def __init__(self):
        """Initialize configuration from environment and config files."""
        # Load from environment
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        self.obsidian_vault_path = os.environ.get('OBSIDIAN_VAULT_PATH', '')
        
        # Validate required environment variables
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        if not self.obsidian_vault_path:
            raise ValueError("OBSIDIAN_VAULT_PATH environment variable is required")
        
        # Load settings from YAML if exists
        config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
        if config_path.exists():
            with open(config_path, 'r') as f:
                settings = yaml.safe_load(f)
                self._load_settings(settings)
        # Defaults are now handled by field(default_factory=...)
    
    def _load_settings(self, settings: Dict[str, Any]):
        """Load settings from YAML configuration."""
        if 'processing' in settings:
            proc = settings['processing']
            self.max_note_size_kb = proc.get('max_note_size_kb', self.max_note_size_kb)
            self.max_notes_per_run = proc.get('max_notes_per_run', self.max_notes_per_run)
            self.file_patterns = proc.get('file_patterns', self.file_patterns)
        
        if 'folders' in settings:
            folders = settings['folders']
            self.inbox_folder = folders.get('inbox', self.inbox_folder)
            self.para_folders = folders.get('para', self.para_folders)
            
            # Override vault path if specified in settings
            vault_path_override = folders.get('obsidian_vault_path', '')
            if vault_path_override:
                self.obsidian_vault_path = vault_path_override
        
        if 'api_limits' in settings:
            api = settings['api_limits']
            self.claude_max_tokens = api.get('claude_max_tokens', self.claude_max_tokens)
            self.claude_model = api.get('claude_model', self.claude_model)
            self.retry_attempts = api.get('retry_attempts', self.retry_attempts)
            self.retry_delay_seconds = api.get('retry_delay_seconds', self.retry_delay_seconds)