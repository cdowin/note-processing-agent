#!/usr/bin/env python3
"""Main entry point for the note processing system."""

import logging
import sys
from pathlib import Path

# Handle both package and direct execution imports
try:
    from .config import Config
    from .note_processor import NoteProcessor
    from .google_drive import GoogleDriveClient
    from .claude_client import ClaudeClient
    from .pipeline import NotePipeline
except ImportError:
    # Direct execution fallback
    from config import Config
    from note_processor import NoteProcessor
    from google_drive import GoogleDriveClient
    from claude_client import ClaudeClient
    from pipeline import NotePipeline


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main entry point for GitHub Actions."""
    logger = setup_logging()
    
    try:
        logger.info("Starting note processing system")
        
        # Load configuration
        config = Config()
        
        # Initialize clients
        logger.info("Initializing Google Drive client")
        drive_client = GoogleDriveClient(
            credentials_path=config.google_drive_credentials_path,
            folder_id=config.google_drive_folder_id
        )
        
        logger.info("Initializing Claude client")
        claude_client = ClaudeClient(
            api_key=config.anthropic_api_key,
            model=config.claude_model
        )
        
        # Create pipeline
        pipeline = NotePipeline(
            drive_client=drive_client,
            claude_client=claude_client,
            config=config
        )
        
        # Create processor and run
        processor = NoteProcessor(pipeline=pipeline, config=config)
        processed_count = processor.process_notes()
        
        logger.info(f"Successfully processed {processed_count} notes")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()