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
    
    def list_files(self, folder_name: str = "") -> List[Dict[str, Any]]:
        """
        List files in the specified folder.
        
        Args:
            folder_name: Name of subfolder to list (e.g., "0-QuickNotes")
                        If empty string, lists files in the vault root
        
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
            for file_path in target_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'size': stat.st_size,
                        'modified_time': stat.st_mtime
                    })
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x['modified_time'], reverse=True)
            
            logger.info(f"Found {len(files)} files in {target_dir}")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files in {folder_name}: {e}")
            return []
    
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