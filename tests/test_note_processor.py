"""Tests for the note processor module."""

import pytest
from unittest.mock import Mock, MagicMock, call, patch
from pathlib import Path

from note_processor import NoteProcessor
from pipeline import Note, ProcessingResult


class TestNoteProcessor:
    """Test the NoteProcessor class."""
    
    @pytest.fixture
    def mock_pipeline(self):
        """Mock pipeline for testing."""
        pipeline = Mock()
        pipeline.file_client = Mock()
        pipeline.process_note = MagicMock(return_value=(True, ProcessingResult.SUCCESS))
        return pipeline
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.inbox_folder = "0-QuickNotes"
        config.max_notes_per_run = 5
        config.recursive = True
        config.file_patterns = ["*.md", "*.txt"]
        config.exclude_folders = [".trash"]
        return config
    
    @pytest.fixture
    def note_processor(self, mock_pipeline, mock_config):
        """Create a NoteProcessor instance."""
        return NoteProcessor(mock_pipeline, mock_config)
    
    def test_process_notes_empty_folder(self, note_processor, mock_pipeline):
        """Test processing when no files are found."""
        # Configure empty file list
        mock_pipeline.file_client.list_files.return_value = []
        
        result = note_processor.process_notes()
        
        assert result == 0
        mock_pipeline.process_note.assert_not_called()
    
    def test_process_notes_single_file(self, note_processor, mock_pipeline):
        """Test processing a single file."""
        # Configure file list
        mock_pipeline.file_client.list_files.return_value = [
            {
                'path': '/vault/0-QuickNotes/note.md',
                'name': 'note.md',
                'relative_path': 'note.md',
                'size': 100,
                'modified_time': 1234567890
            }
        ]
        
        # Configure file reading
        mock_pipeline.file_client.read_file.return_value = b"Test content"
        
        result = note_processor.process_notes()
        
        assert result == 1
        mock_pipeline.process_note.assert_called_once()
        
        # Check Note object was created correctly
        note_arg = mock_pipeline.process_note.call_args[0][0]
        assert isinstance(note_arg, Note)
        assert note_arg.name == 'note.md'
        assert note_arg.content == b"Test content"
    
    def test_process_notes_filters_underscore_files(self, note_processor, mock_pipeline):
        """Test that files starting with underscore are filtered out."""
        mock_pipeline.file_client.list_files.return_value = [
            {'path': '/path/note1.md', 'name': 'note1.md', 'size': 100, 'modified_time': 1},
            {'path': '/path/_processed.md', 'name': '_processed.md', 'size': 100, 'modified_time': 2},
            {'path': '/path/note2.md', 'name': 'note2.md', 'size': 100, 'modified_time': 3}
        ]
        
        mock_pipeline.file_client.read_file.return_value = b"Content"
        
        result = note_processor.process_notes()
        
        # Should only process 2 files (excluding _processed.md)
        assert result == 2
        assert mock_pipeline.process_note.call_count == 2
        
        # Verify the right files were processed
        processed_names = [
            call[0][0].name for call in mock_pipeline.process_note.call_args_list
        ]
        assert 'note1.md' in processed_names
        assert 'note2.md' in processed_names
        assert '_processed.md' not in processed_names
    
    def test_process_notes_respects_max_limit(self, note_processor, mock_pipeline, mock_config):
        """Test that max_notes_per_run limit is respected."""
        mock_config.max_notes_per_run = 2
        
        # Create 5 files
        files = [
            {'path': f'/path/note{i}.md', 'name': f'note{i}.md', 
             'size': 100, 'modified_time': i}
            for i in range(5)
        ]
        mock_pipeline.file_client.list_files.return_value = files
        mock_pipeline.file_client.read_file.return_value = b"Content"
        
        result = note_processor.process_notes()
        
        # Should only process 2 files due to limit
        assert result == 2
        assert mock_pipeline.process_note.call_count == 2
    
    def test_process_notes_handles_processing_failure(self, note_processor, mock_pipeline):
        """Test handling when a note fails to process."""
        mock_pipeline.file_client.list_files.return_value = [
            {'path': '/path/note1.md', 'name': 'note1.md', 'size': 100, 'modified_time': 1},
            {'path': '/path/note2.md', 'name': 'note2.md', 'size': 100, 'modified_time': 2},
            {'path': '/path/note3.md', 'name': 'note3.md', 'size': 100, 'modified_time': 3}
        ]
        
        mock_pipeline.file_client.read_file.return_value = b"Content"
        
        # Configure pipeline to fail on second note
        mock_pipeline.process_note.side_effect = [
            (True, ProcessingResult.SUCCESS), 
            (False, ProcessingResult.LLM_FAILED), 
            (True, ProcessingResult.SUCCESS)
        ]
        
        result = note_processor.process_notes()
        
        # Should process all 3, but only 2 succeed
        assert result == 2
        assert mock_pipeline.process_note.call_count == 3
    
    def test_process_notes_handles_read_error(self, note_processor, mock_pipeline):
        """Test handling when file reading fails."""
        mock_pipeline.file_client.list_files.return_value = [
            {'path': '/path/note.md', 'name': 'note.md', 'size': 100, 'modified_time': 1}
        ]
        
        # Configure read to fail
        mock_pipeline.file_client.read_file.side_effect = IOError("Read failed")
        
        result = note_processor.process_notes()
        
        # Should handle error gracefully
        assert result == 0
        mock_pipeline.process_note.assert_not_called()
    
    def test_create_note_from_file(self, note_processor, mock_pipeline):
        """Test creating Note object from file info."""
        file_info = {
            'path': '/vault/0-QuickNotes/subfolder/note.md',
            'name': 'note.md',
            'relative_path': 'subfolder/note.md',
            'size': 150,
            'modified_time': 1234567890
        }
        
        mock_pipeline.file_client.read_file.return_value = b"Note content"
        
        note = note_processor._create_note_from_file(file_info)
        
        assert isinstance(note, Note)
        assert note.file_path == '/vault/0-QuickNotes/subfolder/note.md'
        assert note.name == 'note.md'
        assert note.content == b"Note content"
        assert note.relative_path == 'subfolder/note.md'
    
    def test_recursive_processing_configuration(self, note_processor, mock_pipeline, mock_config):
        """Test that recursive configuration is passed to file listing."""
        mock_pipeline.file_client.list_files.return_value = []
        
        note_processor.process_notes()
        
        # Verify list_files was called with correct parameters
        mock_pipeline.file_client.list_files.assert_called_once_with(
            folder_name="0-QuickNotes",
            recursive=True,
            file_patterns=["*.md", "*.txt"],
            exclude_folders=[".trash"]
        )
    
    def test_process_notes_logging(self, note_processor, mock_pipeline):
        """Test that appropriate logging occurs during processing."""
        mock_pipeline.file_client.list_files.return_value = [
            {'path': '/path/note.md', 'name': 'note.md', 'size': 100, 'modified_time': 1}
        ]
        mock_pipeline.file_client.read_file.return_value = b"Content"
        mock_pipeline.process_note.return_value = (True, ProcessingResult.SUCCESS)
        
        with patch('note_processor.logger') as mock_logger:
            result = note_processor.process_notes()
        
        # Check key log messages
        assert any('Starting note processing batch' in str(call) 
                  for call in mock_logger.info.call_args_list)
        assert any('Successfully processed: note.md' in str(call) 
                  for call in mock_logger.info.call_args_list)
        assert any('Batch complete' in str(call) 
                  for call in mock_logger.info.call_args_list)
    
    def test_process_notes_with_subdirectories(self, note_processor, mock_pipeline):
        """Test processing notes in subdirectories."""
        mock_pipeline.file_client.list_files.return_value = [
            {
                'path': '/vault/0-QuickNotes/root.md',
                'name': 'root.md',
                'relative_path': 'root.md',
                'subfolder': '',
                'size': 100,
                'modified_time': 1
            },
            {
                'path': '/vault/0-QuickNotes/meetings/meeting1.md',
                'name': 'meeting1.md',
                'relative_path': 'meetings/meeting1.md',
                'subfolder': 'meetings',
                'size': 100,
                'modified_time': 2
            }
        ]
        
        mock_pipeline.file_client.read_file.return_value = b"Content"
        
        result = note_processor.process_notes()
        
        assert result == 2
        
        # Verify both files were processed with correct relative paths
        notes = [call[0][0] for call in mock_pipeline.process_note.call_args_list]
        assert any(note.relative_path == 'root.md' for note in notes)
        assert any(note.relative_path == 'meetings/meeting1.md' for note in notes)
    
    def test_process_notes_logging_filtered_results(self, note_processor, mock_pipeline):
        """Test logging for filtered processing results."""
        mock_pipeline.file_client.list_files.return_value = [
            {'path': '/path/note1.md', 'name': 'note1.md', 'size': 100, 'modified_time': 1},
            {'path': '/path/note2.md', 'name': 'note2.md', 'size': 100, 'modified_time': 2}
        ]
        mock_pipeline.file_client.read_file.return_value = b"Content"
        mock_pipeline.process_note.side_effect = [
            (False, ProcessingResult.FILTERED),
            (False, ProcessingResult.VALIDATION_FAILED)
        ]
        
        with patch('note_processor.logger') as mock_logger:
            result = note_processor.process_notes()
        
        # Should log appropriate messages for different failure types
        assert any('Note filtered out: note1.md' in str(call) 
                  for call in mock_logger.info.call_args_list)
        assert any('Note validation failed: note2.md' in str(call) 
                  for call in mock_logger.warning.call_args_list)
        assert result == 0
    
    def test_process_notes_logging_llm_errors(self, note_processor, mock_pipeline):
        """Test logging for LLM processing errors."""
        mock_pipeline.file_client.list_files.return_value = [
            {'path': '/path/note.md', 'name': 'note.md', 'size': 100, 'modified_time': 1}
        ]
        mock_pipeline.file_client.read_file.return_value = b"Content"
        mock_pipeline.process_note.return_value = (False, ProcessingResult.LLM_FAILED)
        
        with patch('note_processor.logger') as mock_logger:
            result = note_processor.process_notes()
        
        # Should log error for LLM failure
        assert any('LLM processing failed: note.md' in str(call) 
                  for call in mock_logger.error.call_args_list)
        assert result == 0