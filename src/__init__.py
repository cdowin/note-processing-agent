"""Note Assistant - AI-powered note processing system."""

__version__ = "0.1.0"

from .config import Config
from .claude_client import ClaudeClient
from .file_system import FileSystemClient
from .pipeline import NotePipeline, Note
from .note_processor import NoteProcessor
from .prompt_manager import PromptManager

__all__ = [
    "Config",
    "ClaudeClient", 
    "FileSystemClient",
    "NotePipeline",
    "Note",
    "NoteProcessor",
    "PromptManager"
]