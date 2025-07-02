#!/usr/bin/env python3
"""Main entry point for the note processing system."""

import logging
import sys

from .config import Config
from .note_processor import NoteProcessor
from .file_system import FileSystemClient
from .claude_client import ClaudeClient
from .pipeline import NotePipeline



def setup_logging():
    """
    Configure logging for the application.
    
    Returns:
        Logger instance for the main module
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main entry point for local note processing."""
    logger = setup_logging()
    
    try:
        logger.info("Starting local note processing system")
        
        # Load configuration
        config = Config()
        
        # Initialize clients
        logger.info("Initializing file system client")
        file_client = FileSystemClient(
            vault_path=config.obsidian_vault_path
        )
        
        logger.info("Initializing Claude client")
        claude_client = ClaudeClient(
            api_key=config.anthropic_api_key,
            config=config
        )
        
        # Create pipeline
        pipeline = NotePipeline(
            file_client=file_client,
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