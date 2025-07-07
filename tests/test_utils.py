"""Tests for utils module."""

from utils import calculate_file_hash, parse_frontmatter, generate_frontmatter

# Test constants
SHA256_HASH_STRING_LENGTH = 71  # "sha256:" (7) + 64 hex chars


class TestCalculateFileHash:
    """Test the calculate_file_hash function."""
    
    def test_empty_content(self):
        """Test hashing empty content."""
        result = calculate_file_hash("")
        assert result.startswith("sha256:")
        assert len(result) == SHA256_HASH_STRING_LENGTH  # "sha256:" (7) + 64 hex chars
    
    def test_simple_content(self):
        """Test hashing simple content."""
        content = "Hello, world!"
        result = calculate_file_hash(content)
        expected_hash = "sha256:315f5bdb76d078c43b8ac0064e4a0164612b1fce77c869345bfc94c75894edd3"
        assert result == expected_hash
    
    def test_unicode_content(self):
        """Test hashing unicode content."""
        content = "Hello, 世界! 🌍"
        result = calculate_file_hash(content)
        assert result.startswith("sha256:")
        assert len(result) == SHA256_HASH_STRING_LENGTH
    
    def test_consistent_hashing(self):
        """Test that same content produces same hash."""
        content = "This is a test note with some content."
        hash1 = calculate_file_hash(content)
        hash2 = calculate_file_hash(content)
        assert hash1 == hash2
    
    def test_different_content_different_hash(self):
        """Test that different content produces different hashes."""
        content1 = "First note content"
        content2 = "Second note content"
        hash1 = calculate_file_hash(content1)
        hash2 = calculate_file_hash(content2)
        assert hash1 != hash2
    
    def test_multiline_content(self):
        """Test hashing multiline content."""
        content = """This is a multiline note.
        
It has several paragraphs.

- And some bullet points
- With different items
        
Final paragraph here."""
        result = calculate_file_hash(content)
        assert result.startswith("sha256:")
        assert len(result) == SHA256_HASH_STRING_LENGTH


class TestParseFrontmatter:
    """Test the parse_frontmatter function."""
    
    def test_no_frontmatter(self):
        """Test content without frontmatter."""
        content = "This is just regular content without frontmatter."
        content_without_fm, frontmatter = parse_frontmatter(content)
        
        assert content_without_fm == content
        assert frontmatter == {}
    
    def test_valid_frontmatter(self):
        """Test content with valid YAML frontmatter."""
        content = """---
title: Test Note
tags: ["#test", "#example"]
created: 2025-01-07
---
This is the actual note content after the frontmatter."""
        
        content_without_fm, frontmatter = parse_frontmatter(content)
        
        assert content_without_fm == "This is the actual note content after the frontmatter."
        assert frontmatter["title"] == "Test Note"
        assert frontmatter["tags"] == ["#test", "#example"]
        assert str(frontmatter["created"]) == "2025-01-07"
    
    def test_empty_frontmatter(self):
        """Test content with empty frontmatter section."""
        content = """---

---
Content after empty frontmatter."""
        
        content_without_fm, frontmatter = parse_frontmatter(content)
        
        assert content_without_fm == "Content after empty frontmatter."
        assert frontmatter == {}
    
    def test_malformed_frontmatter(self):
        """Test content with malformed YAML frontmatter."""
        content = """---
title: Test Note
invalid: yaml: content: here
tags: [unclosed list
---
Content after malformed frontmatter."""
        
        content_without_fm, frontmatter = parse_frontmatter(content)
        
        # Should return original content if YAML parsing fails
        assert content_without_fm == content
        assert frontmatter == {}
    
    def test_no_closing_delimiter(self):
        """Test content that starts like frontmatter but has no closing ---."""
        content = """---
title: Test Note
tags: ["#test"]
This content never closes the frontmatter properly."""
        
        content_without_fm, frontmatter = parse_frontmatter(content)
        
        assert content_without_fm == content
        assert frontmatter == {}
    
    def test_frontmatter_with_complex_data(self):
        """Test frontmatter with complex nested data structures."""
        content = """---
processed_datetime: "Jan 07, 2025 14:30:00 UTC"
note_hash: "sha256:abc123def456"
summary: "Meeting notes about project timeline"
tags: ["#meeting", "#project-alpha", "#deadlines"]
---
# Meeting Notes

Today we discussed the project timeline and deliverables."""
        
        content_without_fm, frontmatter = parse_frontmatter(content)
        
        expected_content = """# Meeting Notes

Today we discussed the project timeline and deliverables."""
        
        assert content_without_fm == expected_content
        assert frontmatter["processed_datetime"] == "Jan 07, 2025 14:30:00 UTC"
        assert frontmatter["summary"] == "Meeting notes about project timeline"
        assert frontmatter["tags"] == ["#meeting", "#project-alpha", "#deadlines"]
        assert frontmatter["note_hash"] == "sha256:abc123def456"
    
    def test_content_starting_with_dashes_but_not_frontmatter(self):
        """Test content that starts with --- but isn't frontmatter."""
        content = """--- This is just a line starting with dashes
Not actually frontmatter.
Just regular content."""
        
        content_without_fm, frontmatter = parse_frontmatter(content)
        
        assert content_without_fm == content
        assert frontmatter == {}


class TestGenerateFrontmatter:
    """Test the generate_frontmatter function."""
    
    def test_empty_metadata(self):
        """Test generating frontmatter from empty metadata."""
        metadata = {}
        result = generate_frontmatter(metadata)
        
        assert result.startswith("---\n")
        assert result.endswith("---\n")
        assert result == "---\n{}\n---\n"
    
    def test_simple_metadata(self):
        """Test generating frontmatter from simple metadata."""
        metadata = {
            "summary": "Test Note",
            "tags": ["#test", "#example"]
        }
        result = generate_frontmatter(metadata)
        
        assert result.startswith("---\n")
        assert result.endswith("---\n")
        assert "summary: Test Note" in result
        assert "tags:" in result
        assert "#test" in result
        assert "#example" in result
    
    def test_ordered_fields(self):
        """Test that fields are ordered correctly in output."""
        metadata = {
            "tags": ["#test"],
            "processed_datetime": "Jan 07, 2025 14:30:00 UTC",
            "note_hash": "sha256:abc123",
            "summary": "Test summary"
        }
        result = generate_frontmatter(metadata)
        
        lines = result.split('\n')
        
        # Find the order of key fields in the output
        processed_idx = next(i for i, line in enumerate(lines) if 'processed_datetime' in line)
        hash_idx = next(i for i, line in enumerate(lines) if 'note_hash' in line)
        summary_idx = next(i for i, line in enumerate(lines) if 'summary' in line)
        
        # Verify the expected order
        assert processed_idx < hash_idx < summary_idx
    
    def test_complete_note_metadata(self):
        """Test generating frontmatter with complete note metadata."""
        metadata = {
            "processed_datetime": "Jan 07, 2025 14:30:00 UTC",
            "note_hash": "sha256:a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            "summary": "Meeting notes about Project Alpha timeline and deliverables",
            "tags": ["#meeting", "#project-alpha", "#deadlines"]
        }
        result = generate_frontmatter(metadata)
        
        assert result.startswith("---\n")
        assert result.endswith("---\n")
        
        # Check all fields are present
        assert "processed_datetime: Jan 07, 2025 14:30:00 UTC" in result
        assert "note_hash: sha256:" in result
        assert "summary: Meeting notes about Project Alpha" in result
        
        # Check tags array format
        assert "tags:" in result
        assert "- '#meeting'" in result
        assert "- '#project-alpha'" in result
        assert "- '#deadlines'" in result
        
        # Ensure removed fields are NOT present
        assert "para_suggestion" not in result
        assert "confidence_score" not in result
        assert "processing_version" not in result
        assert "original_length" not in result
    
    def test_extra_fields_included(self):
        """Test that extra fields are included in the frontmatter."""
        metadata = {
            "processed_datetime": "Jan 07, 2025 14:30:00 UTC",
            "summary": "Test summary", 
            "tags": ["#test"],
            "custom_field": "custom_value",
            "another_field": 42,
            "para_suggestion": "projects",
            "confidence_score": 0.9
        }
        result = generate_frontmatter(metadata)
        
        assert "processed_datetime: Jan 07, 2025 14:30:00 UTC" in result
        assert "summary: Test summary" in result
        assert "tags:" in result
        
        # Extra fields should be included
        assert "custom_field: custom_value" in result
        assert "another_field: 42" in result
        assert "para_suggestion: projects" in result
        assert "confidence_score: 0.9" in result
    
    def test_unicode_in_metadata(self):
        """Test handling unicode characters in metadata."""
        metadata = {
            "summary": "Notes with unicode: 世界 🌍",
            "tags": ["#unicode", "#test", "#世界"]
        }
        result = generate_frontmatter(metadata)
        
        assert "世界" in result
        assert "🌍" in result
        assert "#世界" in result


class TestIntegration:
    """Integration tests combining multiple utils functions."""
    
    def test_roundtrip_frontmatter(self):
        """Test that generate_frontmatter -> parse_frontmatter is consistent."""
        original_metadata = {
            "processed_datetime": "Jan 07, 2025 14:30:00 UTC",
            "note_hash": "sha256:abc123",
            "summary": "Test summary",
            "tags": ["#test", "#example"]
        }
        
        # Generate frontmatter
        frontmatter_text = generate_frontmatter(original_metadata)
        
        # Add some content after frontmatter
        full_content = frontmatter_text + "This is the note content."
        
        # Parse it back
        content_without_fm, parsed_metadata = parse_frontmatter(full_content)
        
        assert content_without_fm == "This is the note content."
        assert parsed_metadata["processed_datetime"] == original_metadata["processed_datetime"]
        assert parsed_metadata["summary"] == original_metadata["summary"]
        assert parsed_metadata["tags"] == original_metadata["tags"]
        assert parsed_metadata["note_hash"] == original_metadata["note_hash"]
    
    def test_hash_consistency_with_frontmatter(self):
        """Test that content hash is consistent after adding/removing frontmatter."""
        original_content = "This is the main note content that should be hashed."
        
        # Calculate hash of original content
        original_hash = calculate_file_hash(original_content)
        
        # Add frontmatter
        metadata = {
            "note_hash": original_hash,
            "summary": "Test note"
        }
        frontmatter_text = generate_frontmatter(metadata)
        full_content = frontmatter_text + original_content
        
        # Parse frontmatter to extract content
        content_without_fm, parsed_metadata = parse_frontmatter(full_content)
        
        # Calculate hash of extracted content
        extracted_hash = calculate_file_hash(content_without_fm)
        
        # Hashes should match
        assert extracted_hash == original_hash
        assert parsed_metadata["note_hash"] == original_hash