#!/usr/bin/env python3
"""Main entry point for the note processing system."""

import logging
import sys

from .config import Config
from .note_processor import NoteProcessor
from .file_system import FileSystemClient
from .pipeline import NotePipeline
from .llm import create_llm_client_with_fallback



def setup_logging():
    """
    Configure logging for the application.
    
    Returns:
        Logger instance for the main module
    """
    logging.basicConfig(
        level=logging.DEBUG,
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
        
        logger.info("Initializing LLM client")
        llm_client = create_llm_client_with_fallback(config)
        logger.info(f"Using LLM provider: {llm_client.provider_name} ({llm_client.model_name})")
        
        # Create pipeline
        pipeline = NotePipeline(
            file_client=file_client,
            llm_client=llm_client,
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