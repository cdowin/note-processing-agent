"""Tests for the file system module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import os

from file_system import FileSystemClient


class TestFileSystemClient:
    """Test the FileSystemClient class."""
    
    def test_init_valid_path(self, temp_vault_dir):
        """Test initialization with a valid vault path."""
        client = FileSystemClient(str(temp_vault_dir))
        # Compare resolved paths since macOS may add /private prefix
        assert client.vault_path.resolve() == temp_vault_dir.resolve()
    
    def test_init_invalid_path(self):
        """Test initialization with non-existent path."""
        with pytest.raises(ValueError, match="Vault path does not exist"):
            FileSystemClient("/non/existent/path")
    
    def test_init_file_not_directory(self, temp_vault_dir):
        """Test initialization with a file instead of directory."""
        test_file = temp_vault_dir / "test.txt"
        test_file.write_text("test")
        
        with pytest.raises(ValueError, match="Vault path is not a directory"):
            FileSystemClient(str(test_file))
    
    def test_list_files_non_recursive(self, temp_vault_dir, create_test_files):
        """Test listing files without recursion."""
        # Create test files
        create_test_files("0-QuickNotes", {
            "note1.md": "Content 1",
            "note2.txt": "Content 2",
            "document.pdf": "PDF content"
        })
        
        # Also create files in subdirectory (should not be included)
        create_test_files("0-QuickNotes/meetings", {
            "meeting1.md": "Meeting notes"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        files = client.list_files("0-QuickNotes", recursive=False)
        
        # Should only get files in root, not subdirectories
        assert len(files) == 3
        filenames = [f['name'] for f in files]
        assert "note1.md" in filenames
        assert "note2.txt" in filenames
        assert "document.pdf" in filenames
        assert "meeting1.md" not in filenames
    
    def test_list_files_recursive(self, temp_vault_dir, create_test_files):
        """Test listing files with recursion."""
        # Create test files in root and subdirectories
        create_test_files("0-QuickNotes", {
            "root_note.md": "Root content"
        })
        create_test_files("0-QuickNotes/meetings", {
            "meeting1.md": "Meeting 1",
            "meeting2.md": "Meeting 2"
        })
        create_test_files("0-QuickNotes/ideas", {
            "idea1.txt": "Idea 1"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        files = client.list_files("0-QuickNotes", recursive=True)
        
        # Should get all files including subdirectories
        assert len(files) == 4
        filenames = [f['name'] for f in files]
        assert "root_note.md" in filenames
        assert "meeting1.md" in filenames
        assert "meeting2.md" in filenames
        assert "idea1.txt" in filenames
        
        # Check relative paths
        relative_paths = [f['relative_path'] for f in files]
        assert "root_note.md" in relative_paths
        assert str(Path("meetings/meeting1.md")) in relative_paths or "meetings\\meeting1.md" in relative_paths
    
    def test_exclude_folders_filtering(self, temp_vault_dir, create_test_files):
        """Test that excluded folders are properly filtered."""
        # Create directories first
        (temp_vault_dir / "0-QuickNotes" / "templates").mkdir(exist_ok=True)
        
        # Create files in regular and excluded folders
        create_test_files("0-QuickNotes", {
            "visible.md": "Visible"
        })
        create_test_files("0-QuickNotes/.trash", {
            "deleted.md": "Should be excluded"
        })
        create_test_files("0-QuickNotes/templates", {
            "template.md": "Should be excluded"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        files = client.list_files(
            "0-QuickNotes", 
            recursive=True,
            exclude_folders=[".trash", "templates"]
        )
        
        # Should only get the visible file
        assert len(files) == 1
        assert files[0]['name'] == "visible.md"
    
    def test_file_pattern_matching(self, temp_vault_dir, create_test_files):
        """Test file pattern matching."""
        create_test_files("0-QuickNotes", {
            "note.md": "Markdown",
            "text.txt": "Text",
            "data.json": "JSON",
            "script.py": "Python"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        
        # Test with markdown pattern only
        files = client.list_files(
            "0-QuickNotes",
            file_patterns=["*.md"]
        )
        assert len(files) == 1
        assert files[0]['name'] == "note.md"
        
        # Test with multiple patterns
        files = client.list_files(
            "0-QuickNotes",
            file_patterns=["*.md", "*.txt"]
        )
        assert len(files) == 2
        filenames = [f['name'] for f in files]
        assert "note.md" in filenames
        assert "text.txt" in filenames
    
    def test_read_file_success(self, temp_vault_dir, create_test_files):
        """Test successful file reading."""
        files = create_test_files("0-QuickNotes", {
            "test.md": "Test content 测试"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        content = client.read_file(str(files[0]))
        
        assert content == b"Test content \xe6\xb5\x8b\xe8\xaf\x95"
        assert content.decode('utf-8') == "Test content 测试"
    
    def test_read_file_not_found(self, temp_vault_dir):
        """Test reading non-existent file."""
        client = FileSystemClient(str(temp_vault_dir))
        
        with pytest.raises(FileNotFoundError):
            client.read_file(str(temp_vault_dir / "nonexistent.md"))
    
    def test_rename_file_success(self, temp_vault_dir, create_test_files):
        """Test successful file renaming."""
        files = create_test_files("0-QuickNotes", {
            "original.md": "Content"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        client.rename_file(str(files[0]), "renamed.md")
        
        # Check old file doesn't exist
        assert not files[0].exists()
        
        # Check new file exists with same content
        new_file = temp_vault_dir / "0-QuickNotes" / "renamed.md"
        assert new_file.exists()
        assert new_file.read_text() == "Content"
    
    def test_write_file_success(self, temp_vault_dir):
        """Test successful file writing."""
        client = FileSystemClient(str(temp_vault_dir))
        
        file_path = temp_vault_dir / "0-QuickNotes" / "new_note.md"
        content = "# New Note\n\nContent"
        
        client.write_file(str(file_path), content.encode('utf-8'))
        
        assert file_path.exists()
        assert file_path.read_text(encoding='utf-8') == content
    
    def test_update_file_with_rename(self, temp_vault_dir, create_test_files):
        """Test updating file content and name."""
        files = create_test_files("0-QuickNotes", {
            "old_note.md": "Old content"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        new_content = "# Updated\n\nNew content"
        
        client.update_file(
            str(files[0]),
            "new_note.md",
            new_content.encode('utf-8')
        )
        
        # Old file should be gone
        assert not files[0].exists()
        
        # New file should exist with new content
        new_file = temp_vault_dir / "0-QuickNotes" / "new_note.md"
        assert new_file.exists()
        assert new_file.read_text(encoding='utf-8') == new_content
    
    def test_update_file_same_name(self, temp_vault_dir, create_test_files):
        """Test updating file content without changing name."""
        files = create_test_files("0-QuickNotes", {
            "note.md": "Old content"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        new_content = "Updated content"
        
        client.update_file(
            str(files[0]),
            "note.md",
            new_content.encode('utf-8')
        )
        
        # File should still exist with new content
        assert files[0].exists()
        assert files[0].read_text(encoding='utf-8') == new_content
    
    def test_backup_file(self, temp_vault_dir, create_test_files):
        """Test creating file backup."""
        files = create_test_files("0-QuickNotes", {
            "important.md": "Important content"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        backup_path = client.backup_file(str(files[0]))
        
        # Both files should exist
        assert files[0].exists()
        assert Path(backup_path).exists()
        
        # Backup should have correct name and content
        assert backup_path.endswith(".backup.md")
        assert Path(backup_path).read_text() == "Important content"
    
    def test_get_vault_folders(self, temp_vault_dir):
        """Test getting list of vault folders."""
        # Create additional test folders
        (temp_vault_dir / "TestFolder").mkdir()
        (temp_vault_dir / ".hidden").mkdir()  # Should be excluded
        
        client = FileSystemClient(str(temp_vault_dir))
        folders = client.get_vault_folders()
        
        # Should include all non-hidden folders
        assert "0-QuickNotes" in folders
        assert "1-Projects" in folders
        assert "2-Areas" in folders
        assert "3-Resources" in folders
        assert "4-Archive" in folders
        assert "TestFolder" in folders
        assert ".hidden" not in folders
        
        # Should be sorted
        assert folders == sorted(folders)
    
    def test_list_files_empty_folder(self, temp_vault_dir):
        """Test listing files in empty folder."""
        client = FileSystemClient(str(temp_vault_dir))
        files = client.list_files("1-Projects")  # Empty folder
        
        assert files == []
    
    def test_list_files_nonexistent_folder(self, temp_vault_dir):
        """Test listing files in non-existent folder."""
        client = FileSystemClient(str(temp_vault_dir))
        files = client.list_files("NonExistentFolder")
        
        assert files == []
    
    def test_file_metadata_structure(self, temp_vault_dir, create_test_files):
        """Test that file metadata has correct structure."""
        create_test_files("0-QuickNotes", {
            "test.md": "Content"
        })
        
        client = FileSystemClient(str(temp_vault_dir))
        files = client.list_files("0-QuickNotes")
        
        assert len(files) == 1
        file_info = files[0]
        
        # Check all required fields are present
        assert 'path' in file_info
        assert 'name' in file_info
        assert 'relative_path' in file_info
        assert 'subfolder' in file_info
        assert 'size' in file_info
        assert 'modified_time' in file_info
        
        # Check types
        assert isinstance(file_info['path'], str)
        assert isinstance(file_info['name'], str)
        assert isinstance(file_info['size'], int)
        assert isinstance(file_info['modified_time'], float)
    
    def test_permission_error_handling(self, temp_vault_dir, create_test_files):
        """Test handling of permission errors."""
        if os.name == 'nt':  # Windows
            pytest.skip("Permission testing is complex on Windows")
        
        files = create_test_files("0-QuickNotes", {
            "protected.md": "Content"
        })
        
        # Make file read-only
        os.chmod(files[0], 0o444)
        
        client = FileSystemClient(str(temp_vault_dir))
        
        try:
            # Should raise exception when trying to write
            with pytest.raises(PermissionError):
                client.write_file(str(files[0]), b"New content")
        finally:
            # Restore permissions for cleanup
            os.chmod(files[0], 0o644)