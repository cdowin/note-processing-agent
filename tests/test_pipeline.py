"""Tests for the note processing pipeline."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path

from pipeline import Note, NotePipeline, ProcessingResult
from utils import calculate_file_hash, generate_frontmatter


class TestNote:
    """Test the Note class."""
    
    def test_note_initialization(self):
        """Test Note object initialization."""
        note = Note(
            file_path="/path/to/note.md",
            name="note.md",
            content=b"Test content",
            relative_path="subfolder/note.md"
        )
        
        assert note.file_path == "/path/to/note.md"
        assert note.name == "note.md"
        assert note.content == b"Test content"
        assert note.relative_path == "subfolder/note.md"
        assert note.text_content == ""
        assert note.content_without_frontmatter == ""
        assert note.existing_frontmatter == {}
        assert note.enhanced_content == ""
        assert note.metadata == {}
    
    def test_note_initialization_default_relative_path(self):
        """Test Note initialization with default relative path."""
        note = Note(
            file_path="/path/to/note.md",
            name="note.md",
            content=b"Test content"
        )
        
        assert note.relative_path == "note.md"


class TestNotePipeline:
    """Test the NotePipeline class."""
    
    @pytest.fixture
    def mock_file_client(self):
        """Mock file client for testing."""
        client = Mock()
        client.rename_file = MagicMock()
        client.update_file = MagicMock()
        return client
    
    @pytest.fixture
    def pipeline(self, mock_file_client, mock_claude_client, mock_config):
        """Create a pipeline instance for testing."""
        return NotePipeline(mock_file_client, mock_claude_client, mock_config)
    
    @pytest.fixture
    def sample_note(self):
        """Helper fixture to create sample notes."""
        def _create_note(name: str, content: str):
            return Note(
                file_path=f"/path/{name}",
                name=name,
                content=content.encode('utf-8')
            )
        return _create_note
    
    def test_filter_already_processed_files(self, pipeline):
        """Test filtering of files with underscore prefix."""
        note = Note(
            file_path="/path/_processed.md",
            name="_processed.md",
            content=b"Content"
        )
        
        result = pipeline._filter(note)
        assert result is False
    
    def test_filter_unchanged_content(self, pipeline):
        """Test filtering of unchanged content via hash."""
        # Content as it would appear after frontmatter extraction (with leading newline)
        content_after_extraction = "\nTest content without frontmatter"
        existing_hash = calculate_file_hash(content_after_extraction)
        
        frontmatter_content = f"""---
processed_datetime: "2025-01-01T12:00:00Z"
note_hash: "{existing_hash}"
summary: "Test"
tags: ["#test"]
---

Test content without frontmatter"""
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=frontmatter_content.encode('utf-8')
        )
        
        result = pipeline._filter(note)
        assert result is False  # Should filter out unchanged content
    
    def test_filter_changed_content(self, pipeline):
        """Test that changed content passes filter."""
        frontmatter_content = """---
processed_datetime: "2025-01-01T12:00:00Z"
note_hash: "sha256:old_hash"
summary: "Test"
tags: ["#test"]
---

New content that has changed"""
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=frontmatter_content.encode('utf-8')
        )
        
        result = pipeline._filter(note)
        assert result is True  # Should pass filter due to hash mismatch
    
    def test_filter_new_note(self, pipeline):
        """Test that new notes without frontmatter pass filter."""
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"# New Note\n\nThis is new content"
        )
        
        result = pipeline._filter(note)
        assert result is True
        assert note.text_content == "# New Note\n\nThis is new content"
        assert note.content_without_frontmatter == "# New Note\n\nThis is new content"
    
    def test_filter_unicode_decode_error(self, pipeline):
        """Test handling of non-UTF8 content."""
        note = Note(
            file_path="/path/binary.bin",
            name="binary.bin",
            content=b'\xff\xfe\x00\x00'  # Invalid UTF-8
        )
        
        result = pipeline._filter(note)
        assert result is False
    
    def test_filter_skips_ignore_parse_true(self, pipeline, sample_note):
        """Test that notes with ignoreParse: true are filtered out."""
        content = """---
ignoreParse: true
---

This note should be ignored."""
        note = sample_note("ignore_me.md", content)
        
        result = pipeline._filter(note)
        assert result is False
    
    def test_filter_skips_ignore_parse_string_true(self, pipeline, sample_note):
        """Test that notes with ignoreParse: 'true' (string) are filtered out."""
        content = """---
ignoreParse: 'true'
---

This note should also be ignored."""
        note = sample_note("ignore_string.md", content)
        
        result = pipeline._filter(note)
        assert result is False
    
    def test_filter_skips_ignore_parse_case_insensitive(self, pipeline, sample_note):
        """Test that ignoreParse: 'True' (mixed case) is filtered out."""
        content = """---
ignoreParse: 'True'
---

This note should be ignored too."""
        note = sample_note("ignore_case.md", content)
        
        result = pipeline._filter(note)
        assert result is False
    
    def test_filter_allows_ignore_parse_false(self, pipeline, sample_note):
        """Test that notes with ignoreParse: false are processed."""
        content = """---
ignoreParse: false
---

This note should be processed."""
        note = sample_note("process_me.md", content)
        
        result = pipeline._filter(note)
        assert result is True
    
    def test_filter_allows_ignore_parse_missing(self, pipeline, sample_note):
        """Test that notes without ignoreParse property are processed."""
        content = """---
other_property: "value"
---

This note should be processed."""
        note = sample_note("normal_note.md", content)
        
        result = pipeline._filter(note)
        assert result is True
    
    def test_filter_allows_ignore_parse_other_values(self, pipeline, sample_note):
        """Test that notes with ignoreParse set to other values are processed."""
        content = """---
ignoreParse: "not_true"
---

This note should be processed."""
        note = sample_note("other_value.md", content)
        
        result = pipeline._filter(note)
        assert result is True
    
    def test_filter_ignore_parse_without_frontmatter(self, pipeline, sample_note):
        """Test that notes without frontmatter are processed normally."""
        content = "This note has no frontmatter and should be processed."
        note = sample_note("no_frontmatter.md", content)
        
        result = pipeline._filter(note)
        assert result is True
    
    def test_validate_file_size_within_limit(self, pipeline, mock_config):
        """Test validation passes for files within size limit."""
        mock_config.max_note_size_kb = 10
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"Small content"  # Much less than 10KB
        )
        
        result = pipeline._validate(note)
        assert result is True
    
    def test_validate_file_size_exceeds_limit(self, pipeline, mock_config):
        """Test validation fails for files exceeding size limit."""
        mock_config.max_note_size_kb = 1  # 1KB limit
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"X" * 2000  # 2KB of content
        )
        
        result = pipeline._validate(note)
        assert result is False
    
    def test_mark_as_processing(self, pipeline, mock_file_client):
        """Test marking file as processing with underscore prefix."""
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"Content"
        )
        
        pipeline._mark_as_processing(note)
        
        # Check file was renamed
        mock_file_client.rename_file.assert_called_once_with(
            "/path/note.md",
            "_note.md"
        )
        
        # Check note properties were updated
        assert note.name == "_note.md"
        assert note.file_path == "/path/_note.md"
    
    def test_enhance_with_llm_success(self, pipeline, mock_claude_client):
        """Test successful LLM enhancement."""
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"Original content"
        )
        note.content_without_frontmatter = "Original content"
        
        # Configure mock response (Claude client returns JSON string)
        import json
        mock_claude_client.send_message.return_value = json.dumps({
            "content": "# Enhanced Content\n\nThis is better formatted.",
            "metadata": {
                "summary": "A test note",
                "tags": ["#test", "#enhanced"],
                "para_category": "resources"
            }
        })
        
        result = pipeline._enhance_with_llm(note)
        
        assert result is True
        assert note.enhanced_content == "# Enhanced Content\n\nThis is better formatted."
        assert note.metadata["summary"] == "A test note"
        assert note.metadata["tags"] == ["#test", "#enhanced"]
        assert note.metadata["para_category"] == "resources"
    
    def test_enhance_with_llm_failure(self, pipeline, mock_claude_client):
        """Test handling of LLM API failure."""
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"Content"
        )
        note.content_without_frontmatter = "Content"
        
        # Configure mock to raise exception
        mock_claude_client.send_message.side_effect = Exception("API Error")
        
        result = pipeline._enhance_with_llm(note)
        
        assert result is False
        assert note.enhanced_content == ""  # Should remain empty
    
    def test_generate_metadata(self, pipeline):
        """Test metadata generation."""
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"Content"
        )
        note.enhanced_content = "Enhanced content for testing"
        note.metadata = {
            "summary": "Test summary",
            "tags": ["#tag1", "#tag2"]
        }
        
        # Mock datetime to have consistent test
        test_time = datetime(2025, 1, 7, 12, 0, 0, tzinfo=timezone.utc)
        with patch('pipeline.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_time
            pipeline._generate_metadata(note)
        
        # Check required fields
        assert 'processed_datetime' in note.metadata
        assert note.metadata['processed_datetime'] == "Jan 07, 2025 12:00:00 UTC"
        # note_hash is now added in _save_to_file_system, not in _generate_metadata
        assert 'note_hash' not in note.metadata
        assert note.metadata['summary'] == "Test summary"
        assert note.metadata['tags'] == ["#tag1", "#tag2"]
    
    def test_generate_metadata_defaults(self, pipeline):
        """Test metadata generation with missing fields."""
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"Content"
        )
        note.enhanced_content = "Content"
        note.metadata = {}  # No metadata from Claude
        
        pipeline._generate_metadata(note)
        
        # Check defaults are applied
        assert note.metadata['summary'] == 'No summary generated'
        assert note.metadata['tags'] == []
    
    def test_save_to_file_system(self, pipeline, mock_file_client):
        """Test saving processed note back to file system."""
        note = Note(
            file_path="/path/_note.md",
            name="_note.md",
            content=b"Original"
        )
        note.enhanced_content = "# Enhanced Note\n\nProcessed content"
        note.metadata = {
            'processed_datetime': 'Jan 07, 2025 12:00:00 UTC',
            'note_hash': 'sha256:test_hash',
            'summary': 'Test note',
            'tags': ['#test']
        }
        
        pipeline._save_to_file_system(note)
        
        # Check update_file was called correctly
        mock_file_client.update_file.assert_called_once()
        
        call_args = mock_file_client.update_file.call_args
        args, kwargs = call_args
        assert kwargs['file_path'] == "/path/_note.md"  # file_path
        assert kwargs['new_name'] == "note.md"  # new_name (underscore removed)
        
        # Check content includes frontmatter
        saved_content = kwargs['content'].decode('utf-8')
        assert saved_content.startswith("---\n")
        assert "processed_datetime: Jan 07, 2025 12:00:00 UTC" in saved_content
        assert "# Enhanced Note\n\nProcessed content" in saved_content
    
    def test_process_note_full_success(self, pipeline, mock_file_client, mock_claude_client):
        """Test full successful note processing."""
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"# Original Note\n\nOriginal content"
        )
        
        # Configure mocks (Claude client returns JSON string)
        import json
        mock_claude_client.send_message.return_value = json.dumps({
            "content": "# Enhanced Note\n\nEnhanced content",
            "metadata": {
                "summary": "An enhanced note",
                "tags": ["#enhanced"]
            }
        })
        
        success, result = pipeline.process_note(note)
        
        assert success is True
        assert result == ProcessingResult.SUCCESS
        
        # Verify all steps were called
        mock_file_client.rename_file.assert_called_once()  # mark_as_processing
        mock_claude_client.send_message.assert_called_once()  # enhance_with_claude
        mock_file_client.update_file.assert_called_once()  # save_to_file_system
    
    def test_process_note_filter_failure(self, pipeline, mock_file_client):
        """Test processing stops when filter fails."""
        note = Note(
            file_path="/path/_already_processed.md",
            name="_already_processed.md",
            content=b"Content"
        )
        
        success, result = pipeline.process_note(note)
        
        assert success is False
        assert result == ProcessingResult.FILTERED
        
        # Verify no processing occurred
        mock_file_client.rename_file.assert_not_called()
        mock_file_client.update_file.assert_not_called()
    
    def test_process_note_validation_failure(self, pipeline, mock_file_client, mock_config):
        """Test processing stops when validation fails."""
        mock_config.max_note_size_kb = 0.001  # Very small limit
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"This content is too large for the configured limit"
        )
        
        success, result = pipeline.process_note(note)
        
        assert success is False
        assert result == ProcessingResult.VALIDATION_FAILED
        
        # Verify no processing occurred
        mock_file_client.rename_file.assert_not_called()
        mock_file_client.update_file.assert_not_called()
    
    def test_process_note_exception_handling(self, pipeline, mock_file_client):
        """Test exception handling during processing."""
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"Content"
        )
        
        # Make rename_file raise exception
        mock_file_client.rename_file.side_effect = Exception("File system error")
        
        success, result = pipeline.process_note(note)
        
        assert success is False  # Should return False on exception
        assert result == ProcessingResult.ERROR
    
    def test_process_note_llm_failure(self, pipeline, mock_file_client, mock_claude_client):
        """Test processing when LLM enhancement fails."""
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=b"# Test Note\n\nContent"
        )
        
        # Configure mock to fail during LLM enhancement
        mock_claude_client.send_message.side_effect = Exception("API Error")
        
        success, result = pipeline.process_note(note)
        
        assert success is False
        assert result == ProcessingResult.LLM_FAILED
        
        # Verify file was marked as processing
        mock_file_client.rename_file.assert_called_once()
    
    def test_process_note_ignore_parse_returns_filtered(self, pipeline):
        """Test that notes with ignoreParse return FILTERED result."""
        content = """---
ignoreParse: true
---

This note should be ignored."""
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=content.encode('utf-8')
        )
        
        success, result = pipeline.process_note(note)
        
        assert success is False
        assert result == ProcessingResult.FILTERED
    
    def test_process_note_unchanged_hash_returns_filtered(self, pipeline):
        """Test that unchanged notes return FILTERED result."""
        # Content as it would appear after frontmatter extraction
        content_after_extraction = "\nUnchanged content"
        existing_hash = calculate_file_hash(content_after_extraction)
        
        frontmatter_content = f"""---
processed_datetime: "2025-01-01T12:00:00Z"
note_hash: "{existing_hash}"
summary: "Test"
tags: ["#test"]
---

Unchanged content"""
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=frontmatter_content.encode('utf-8')
        )
        
        success, result = pipeline.process_note(note)
        
        assert success is False
        assert result == ProcessingResult.FILTERED
    
    def test_original_content_preservation(self, pipeline, mock_file_client, mock_claude_client):
        """Test that original content is preserved at the end of processed note."""
        original_content = "# My Raw Note\n\nThis is my original unprocessed text with typos and bad formating."
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=original_content.encode('utf-8')
        )
        
        # Configure mock LLM response
        import json
        mock_claude_client.send_message.return_value = json.dumps({
            "content": "# My Processed Note\n\nThis is the cleaned and formatted text.",
            "metadata": {
                "summary": "A cleaned note",
                "tags": ["#cleaned"]
            }
        })
        
        success, result = pipeline.process_note(note)
        
        assert success is True
        assert result == ProcessingResult.SUCCESS
        
        # Get the saved content
        call_args = mock_file_client.update_file.call_args
        saved_content = call_args[1]['content'].decode('utf-8')
        
        # Verify structure
        assert "# My Processed Note" in saved_content
        assert "This is the cleaned and formatted text." in saved_content
        assert "---\n## Original Note\n---\n" in saved_content
        assert original_content in saved_content
        
        # Verify the order: enhanced content comes before original
        enhanced_pos = saved_content.index("# My Processed Note")
        separator_pos = saved_content.index("---\n## Original Note\n---\n")
        original_pos = saved_content.index(original_content)
        
        assert enhanced_pos < separator_pos < original_pos
    
    def test_hash_includes_original_content(self, pipeline, mock_file_client, mock_claude_client):
        """Test that the note hash includes both enhanced and original content."""
        original = "Original content here"
        enhanced = "Enhanced content here"
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=original.encode('utf-8')
        )
        
        # Configure mock
        import json
        mock_claude_client.send_message.return_value = json.dumps({
            "content": enhanced,
            "metadata": {"summary": "Test", "tags": []}
        })
        
        success, result = pipeline.process_note(note)
        assert success is True
        
        # Get saved content and extract hash
        call_args = mock_file_client.update_file.call_args
        saved_content = call_args[1]['content'].decode('utf-8')
        
        # Extract the hash from frontmatter
        import re
        hash_match = re.search(r'note_hash: ([^\n]+)', saved_content)
        assert hash_match is not None
        saved_hash = hash_match.group(1)
        
        # Calculate expected hash
        combined_content = enhanced + "\n\n---\n## Original Note\n---\n\n" + original
        expected_hash = calculate_file_hash(combined_content)
        
        assert saved_hash == expected_hash
    
    def test_original_content_with_existing_frontmatter(self, pipeline, mock_file_client, mock_claude_client):
        """Test preservation when original note had frontmatter."""
        original_with_fm = """---
old_field: value
---

Original content with frontmatter"""
        
        note = Note(
            file_path="/path/note.md",
            name="note.md",
            content=original_with_fm.encode('utf-8')
        )
        
        # Configure mock
        import json
        mock_claude_client.send_message.return_value = json.dumps({
            "content": "Enhanced version",
            "metadata": {"summary": "Test", "tags": []}
        })
        
        success, result = pipeline.process_note(note)
        assert success is True
        
        # Get saved content
        call_args = mock_file_client.update_file.call_args
        saved_content = call_args[1]['content'].decode('utf-8')
        
        # Original content (without old frontmatter) should be preserved
        assert "---\n## Original Note\n---\n" in saved_content
        assert "Original content with frontmatter" in saved_content
        # Old frontmatter should NOT be in the preserved section
        assert saved_content.count("old_field: value") == 0