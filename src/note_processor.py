"""Note processor for batch processing operations."""

import logging

try:
    from .pipeline import Note
except ImportError:
    # Fallback for direct imports in tests
    from pipeline import Note



logger = logging.getLogger(__name__)


class NoteProcessor:
    """Orchestrates batch processing of notes."""
    
    def __init__(self, pipeline, config):
        self.pipeline = pipeline
        self.config = config
    
    def process_notes(self) -> int:
        """
        Process all eligible notes in the inbox folder.
        
        Returns:
            Number of successfully processed notes
        """
        logger.info("Starting note processing batch")
        
        # Get list of files from inbox folder
        files = self.pipeline.file_client.list_files(
            folder_name=self.config.inbox_folder,
            recursive=self.config.recursive,
            file_patterns=self.config.file_patterns,
            exclude_folders=self.config.exclude_folders
        )
        
        if not files:
            logger.info("No files found to process")
            return 0
        
        # Filter to only non-underscore files
        eligible_files = [f for f in files if not f['name'].startswith('_')]
        
        # Limit to max notes per run
        files_to_process = eligible_files[:self.config.max_notes_per_run]
        
        logger.info(f"Found {len(eligible_files)} eligible files, "
                   f"processing {len(files_to_process)}")
        
        processed_count = 0
        
        for file_info in files_to_process:
            try:
                # Create Note object
                note = self._create_note_from_file(file_info)
                
                # Process through pipeline
                if self.pipeline.process_note(note):
                    processed_count += 1
                    log_path = file_info.get('relative_path', file_info['name'])
                    logger.info(f"Successfully processed: {log_path}")
                else:
                    log_path = file_info.get('relative_path', file_info['name'])
                    logger.warning(f"Failed to process: {log_path}")
                    
            except Exception as e:
                log_path = file_info.get('relative_path', file_info['name'])
                logger.error(f"Error processing {log_path}: {str(e)}", 
                           exc_info=True)
        
        logger.info(f"Batch complete. Processed {processed_count}/{len(files_to_process)} notes")
        return processed_count
    
    def _create_note_from_file(self, file_info: dict) -> Note:
        """
        Create a Note object from local file info.
        
        Args:
            file_info: File metadata from file system
            
        Returns:
            Note object ready for processing
        """
        file_path = file_info['path']
        file_name = file_info['name']
        
        # Read file content
        # Use relative path for logging if available
        log_path = file_info.get('relative_path', file_name)
        logger.info(f"Reading file: {log_path}")
        content = self.pipeline.file_client.read_file(file_path)
        
        # Create Note object with relative path info
        return Note(
            file_path=file_path,
            name=file_name,
            content=content,
            relative_path=file_info.get('relative_path', file_name)
        )