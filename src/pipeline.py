"""Note processing pipeline implementation."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Constants
BYTES_PER_KB = 1024


from prompt_manager import PromptManager
from utils import calculate_file_hash, parse_frontmatter, generate_frontmatter



logger = logging.getLogger(__name__)


class Note:
    """Represents a note being processed through the pipeline."""
    
    def __init__(self, file_path: str, name: str, content: bytes, relative_path: str = ""):
        """
        Initialize a Note object.
        
        Args:
            file_path: Full path to the note file
            name: Name of the note file
            content: Raw byte content of the file
            relative_path: Relative path from the inbox folder (optional)
        """
        self.file_path = file_path
        self.name = name
        self.content = content
        self.relative_path = relative_path or name
        self.text_content: str = ""
        self.content_without_frontmatter: str = ""
        self.existing_frontmatter: Dict[str, Any] = {}
        self.enhanced_content: str = ""
        self.metadata: Dict[str, Any] = {}


class NotePipeline:
    """Processing pipeline for notes."""
    
    def __init__(self, file_client, claude_client, config):
        """
        Initialize the processing pipeline.
        
        Args:
            file_client: Client for file system operations
            claude_client: Client for Claude API interactions
            config: Configuration object
        """
        self.file_client = file_client
        self.claude = claude_client
        self.config = config
        self.prompt_manager = PromptManager(config)
    
    def process_note(self, note: Note) -> bool:
        """
        Process a single note through all pipeline stages.
        
        Returns:
            bool: True if processing succeeded, False otherwise
        """
        try:
            # Log with relative path if available
            log_name = getattr(note, 'relative_path', note.name)
            logger.info(f"Processing note: {log_name}")
            
            if not self._filter(note):
                logger.info(f"Note filtered out: {note.name}")
                return False
            
            if not self._validate(note):
                logger.warning(f"Note validation failed: {note.name}")
                return False
            
            # Mark as processing immediately
            self._mark_as_processing(note)
            
            # Enhance with Claude
            if not self._enhance_with_claude(note):
                logger.error(f"Claude enhancement failed: {note.name}")
                return False
            
            # Generate metadata
            self._generate_metadata(note)
            
            # Save back to file system
            self._save_to_file_system(note)
            
            logger.info(f"Successfully processed: {note.name}")
            return True
            
        except Exception as e:
            logger.error(f"Pipeline error for {note.name}: {str(e)}", exc_info=True)
            return False
    
    def _filter(self, note: Note) -> bool:
        """Skip underscore files and check hashes."""
        # Skip files already marked as processed
        if note.name.startswith('_'):
            return False
        
        try:
            # Decode content for text processing
            note.text_content = note.content.decode('utf-8')
            
            # Parse existing frontmatter if any
            content_without_fm, frontmatter = parse_frontmatter(note.text_content)
            note.existing_frontmatter = frontmatter
            # Store content without frontmatter for processing
            note.content_without_frontmatter = content_without_fm
            
            # Check if note should be ignored (ignoreParse: true)
            ignore_parse = frontmatter.get('ignoreParse', False)
            if ignore_parse is True or (isinstance(ignore_parse, str) and ignore_parse.lower() == 'true'):
                logger.info(f"Note marked to ignore processing (ignoreParse: {ignore_parse}): {note.name}")
                return False
            
            # Check if already processed via hash
            if 'note_hash' in frontmatter:
                current_hash = calculate_file_hash(content_without_fm)
                if current_hash == frontmatter.get('note_hash'):
                    logger.info(f"Note unchanged (hash match): {note.name}")
                    return False
            
            return True
            
        except UnicodeDecodeError:
            # Should not happen for text files
            logger.error(f"Failed to decode text file as UTF-8: {note.name}")
            return False
    
    def _validate(self, note: Note) -> bool:
        """Check file size and format limits."""
        max_size = self.config.max_note_size_kb * BYTES_PER_KB
        
        if len(note.content) > max_size:
            logger.warning(f"Note too large ({len(note.content)} bytes): {note.name}")
            return False
        
        return True
    
    def _mark_as_processing(self, note: Note):
        """Rename with underscore prefix."""
        new_name = f"_{note.name}"
        logger.info(f"Marking as processing: {note.name} -> {new_name}")
        
        self.file_client.rename_file(note.file_path, new_name)
        # Update note object with new path
        from pathlib import Path
        old_path = Path(note.file_path)
        note.file_path = str(old_path.parent / new_name)
        note.name = new_name
    
    def _enhance_with_claude(self, note: Note) -> bool:
        """Send to Claude for processing."""
        try:
            # Get appropriate prompt - use content without frontmatter
            prompt = self.prompt_manager.format_note_prompt(
                note_content=note.content_without_frontmatter
            )
            
            # Send to Claude
            response = self.claude.send_message(prompt)
            
            # Parse response
            enhanced_data = self.prompt_manager.parse_claude_response(response)
            logger.info(f"Claude response type: {type(enhanced_data)}")
            logger.info(f"Enhanced data keys: {enhanced_data.keys() if isinstance(enhanced_data, dict) else 'Not a dict'}")
            
            # Extract content and metadata
            content = enhanced_data.get('content', note.content_without_frontmatter)
            metadata = enhanced_data.get('metadata', {})
            
            # Debug logging
            logger.debug(f"Extracted content preview: {content[:100] if isinstance(content, str) else str(type(content))}")
            logger.debug(f"Extracted metadata: {metadata}")
            
            note.enhanced_content = content
            note.metadata.update(metadata)
            
            return True
            
        except Exception as e:
            logger.error(f"Claude processing error: {str(e)}")
            return False
    
    def _generate_metadata(self, note: Note):
        """Create YAML frontmatter."""
        # Calculate hash of enhanced content
        content_hash = calculate_file_hash(note.enhanced_content)
        
        # Build metadata - only essential fields
        # Format timestamp as human-readable: "Jan 07, 2025 14:30:25 UTC"
        utc_now = datetime.now(timezone.utc)
        human_timestamp = utc_now.strftime("%b %d, %Y %H:%M:%S UTC")
        
        note.metadata.update({
            'processed_datetime': human_timestamp,
            'note_hash': content_hash
        })
        
        # Ensure required fields have defaults
        note.metadata.setdefault('summary', 'No summary generated')
        note.metadata.setdefault('tags', [])
    
    def _save_to_file_system(self, note: Note):
        """Save processed note back to file system."""
        # Generate final content with frontmatter
        final_content = generate_frontmatter(note.metadata)
        final_content += note.enhanced_content
        
        # Remove underscore from name
        final_name = note.name[1:] if note.name.startswith('_') else note.name
        
        logger.info(f"Saving processed note: {final_name}")
        
        # Save to file system
        self.file_client.update_file(
            file_path=note.file_path,
            new_name=final_name,
            content=final_content.encode('utf-8')
        )