"""Configuration management for the note assistant."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field

# Default configuration constants
DEFAULT_MAX_NOTE_SIZE_KB = 10000
DEFAULT_MAX_NOTES_PER_RUN = 10
DEFAULT_CLAUDE_MAX_TOKENS = 4096


@dataclass
class Config:
    """Application configuration."""
    
    # Environment variables (will be loaded in __post_init__)
    anthropic_api_key: str = ""
    obsidian_vault_path: str = ""
    
    # Processing settings
    max_note_size_kb: int = DEFAULT_MAX_NOTE_SIZE_KB
    max_notes_per_run: int = DEFAULT_MAX_NOTES_PER_RUN
    file_patterns: List[str] = field(default_factory=lambda: ["*.md", "*.txt", "*.org", "*.rst", "*.markdown"])
    recursive: bool = True
    exclude_folders: List[str] = field(default_factory=lambda: [".obsidian", ".trash", "templates", ".git"])
    
    # Folder configuration
    inbox_folder: str = "0-QuickNotes"
    para_folders: Dict[str, str] = field(default_factory=lambda: {
        "projects": "1-Projects",
        "areas": "2-Areas",
        "resources": "3-Resources",
        "archive": "4-Archive"
    })
    
    # LLM configuration
    llm: Dict[str, Any] = field(default_factory=dict)
    
    # Legacy API settings (for backward compatibility)
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = DEFAULT_CLAUDE_MAX_TOKENS
    retry_attempts: int = 1
    retry_delay_seconds: int = 2
    
    # Versioning
    processing_version: str = "1.0"
    
    def __post_init__(self):
        """Initialize configuration from environment and config files after dataclass init."""
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
            self.recursive = proc.get('recursive', self.recursive)
            self.exclude_folders = proc.get('exclude_folders', self.exclude_folders)
        
        if 'folders' in settings:
            folders = settings['folders']
            self.inbox_folder = folders.get('inbox', self.inbox_folder)
            self.para_folders = folders.get('para', self.para_folders)
            
            # Override vault path if specified in settings
            vault_path_override = folders.get('obsidian_vault_path', '')
            if vault_path_override:
                self.obsidian_vault_path = vault_path_override
        
        # Load LLM configuration
        if 'llm' in settings:
            self.llm = settings['llm']
        
        # Load legacy API settings for backward compatibility
        if 'api_limits' in settings:
            api = settings['api_limits']
            self.claude_max_tokens = api.get('claude_max_tokens', self.claude_max_tokens)
            self.claude_model = api.get('claude_model', self.claude_model)
            self.retry_attempts = api.get('retry_attempts', self.retry_attempts)
            self.retry_delay_seconds = api.get('retry_delay_seconds', self.retry_delay_seconds)