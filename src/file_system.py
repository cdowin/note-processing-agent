"""Local file system operations for note processing."""

import shutil
from pathlib import Path
from typing import List, Dict, Any
import logging


logger = logging.getLogger(__name__)


class FileSystemClient:
    """Client for local file system operations in Obsidian vault."""
    
    def __init__(self, vault_path: str):
        """
        Initialize file system client.
        
        Args:
            vault_path: Path to the Obsidian vault directory
        """
        self.vault_path = Path(vault_path).resolve()
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")
        if not self.vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {vault_path}")
        
        logger.info(f"Initialized file system client for vault: {self.vault_path}")
    
    def list_files(self, folder_name: str = "", recursive: bool = False, 
                   file_patterns: List[str] = None, exclude_folders: List[str] = None) -> List[Dict[str, Any]]:
        """
        List files in the specified folder.
        
        Args:
            folder_name: Name of subfolder to list (e.g., "0-QuickNotes")
                        If empty string, lists files in the vault root
            recursive: Whether to search subdirectories recursively
            file_patterns: List of glob patterns to match files (e.g., ["*.md", "*.txt"])
            exclude_folders: List of folder names to exclude from traversal
        
        Returns:
            List of file metadata dictionaries
        """
        try:
            if folder_name:
                target_dir = self.vault_path / folder_name
                if not target_dir.exists():
                    logger.warning(f"Folder not found: {folder_name}")
                    return []
            else:
                target_dir = self.vault_path
            
            files = []
            
            if recursive:
                # Recursive search with pattern matching
                for pattern in (file_patterns or ['*']):
                    for file_path in target_dir.rglob(pattern):
                        if file_path.is_file() and self._should_include_file(file_path, target_dir, exclude_folders):
                            stat = file_path.stat()
                            relative_path = file_path.relative_to(target_dir)
                            files.append({
                                'path': str(file_path),
                                'name': file_path.name,
                                'relative_path': str(relative_path),
                                'subfolder': str(relative_path.parent) if relative_path.parent != Path('.') else '',
                                'size': stat.st_size,
                                'modified_time': stat.st_mtime
                            })
            else:
                # Non-recursive search (original behavior)
                for file_path in target_dir.iterdir():
                    if file_path.is_file():
                        # Match against patterns if provided
                        if file_patterns and not any(file_path.match(pattern) for pattern in file_patterns):
                            continue
                            
                        stat = file_path.stat()
                        files.append({
                            'path': str(file_path),
                            'name': file_path.name,
                            'relative_path': file_path.name,
                            'subfolder': '',
                            'size': stat.st_size,
                            'modified_time': stat.st_mtime
                        })
            
            # Remove duplicates (in case patterns overlap)
            seen_paths = set()
            unique_files = []
            for file_info in files:
                if file_info['path'] not in seen_paths:
                    seen_paths.add(file_info['path'])
                    unique_files.append(file_info)
            
            # Sort by modification time (newest first)
            unique_files.sort(key=lambda x: x['modified_time'], reverse=True)
            
            logger.info(f"Found {len(unique_files)} files in {target_dir} (recursive={recursive})")
            return unique_files
            
        except Exception as e:
            logger.error(f"Error listing files in {folder_name}: {e}")
            return []
    
    def _should_include_file(self, file_path: Path, base_dir: Path, exclude_folders: List[str]) -> bool:
        """
        Check if a file should be included based on exclude folder rules.
        
        Args:
            file_path: Path to the file
            base_dir: Base directory for relative path calculation
            exclude_folders: List of folder names to exclude
            
        Returns:
            True if file should be included, False otherwise
        """
        if not exclude_folders:
            return True
            
        # Check if any parent folder is in the exclude list
        try:
            relative_path = file_path.relative_to(base_dir)
            for part in relative_path.parts[:-1]:  # Exclude the filename itself
                if part in exclude_folders:
                    return False
            return True
        except ValueError:
            # File is not under base_dir
            return False
    
    def read_file(self, file_path: str) -> bytes:
        """
        Read file content from local file system.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content as bytes
        """
        try:
            path = Path(file_path)
            content = path.read_bytes()
            logger.debug(f"Read {len(content)} bytes from {file_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    def rename_file(self, file_path: str, new_name: str):
        """
        Rename a file in the file system.
        
        Args:
            file_path: Current path to the file
            new_name: New name for the file (just the filename, not full path)
        """
        try:
            old_path = Path(file_path)
            new_path = old_path.parent / new_name
            old_path.rename(new_path)
            logger.info(f"Renamed {old_path.name} to {new_name}")
        except Exception as e:
            logger.error(f"Error renaming file {file_path}: {e}")
            raise
    
    def write_file(self, file_path: str, content: bytes):
        """
        Write content to a file.
        
        Args:
            file_path: Path where to write the file
            content: Content to write as bytes
        """
        try:
            path = Path(file_path)
            path.write_bytes(content)
            logger.info(f"Wrote {len(content)} bytes to {file_path}")
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            raise
    
    def update_file(self, file_path: str, new_name: str, content: bytes):
        """
        Update file content and optionally rename.
        
        Args:
            file_path: Current path to the file
            new_name: New name for the file
            content: New content as bytes
        """
        try:
            old_path = Path(file_path)
            new_path = old_path.parent / new_name
            
            # Write new content
            new_path.write_bytes(content)
            
            # Remove old file if name changed
            if old_path != new_path and old_path.exists():
                old_path.unlink()
            
            logger.info(f"Updated file: {new_path}")
            
        except Exception as e:
            logger.error(f"Error updating file {file_path}: {e}")
            raise
    
    def backup_file(self, file_path: str) -> str:
        """
        Create a backup of a file before processing.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file
        """
        try:
            source_path = Path(file_path)
            backup_path = source_path.with_suffix(f".backup{source_path.suffix}")
            
            shutil.copy2(source_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error creating backup for {file_path}: {e}")
            raise
    
    def get_vault_folders(self) -> List[str]:
        """
        Get list of all folders in the vault.
        
        Returns:
            List of folder names
        """
        try:
            folders = []
            for item in self.vault_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    folders.append(item.name)
            
            folders.sort()
            return folders
            
        except Exception as e:
            logger.error(f"Error listing vault folders: {e}")
            return []