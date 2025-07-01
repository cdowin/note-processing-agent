"""Google Drive API client implementation."""

import logging
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from googleapiclient.errors import HttpError
import time


logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """Client for interacting with Google Drive API."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self, credentials_path: str, folder_id: str):
        """
        Initialize Google Drive client.
        
        Args:
            credentials_path: Path to service account JSON file
            folder_id: ID of the Google Drive folder to work with
        """
        self.folder_id = folder_id
        self.service = self._authenticate(credentials_path)
    
    def _authenticate(self, credentials_path: str):
        """Authenticate with Google Drive using service account."""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=self.SCOPES
            )
            service = build('drive', 'v3', credentials=credentials)
            logger.info("Successfully authenticated with Google Drive")
            return service
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Drive: {e}")
            raise
    
    def list_files(self, folder_name: str = None) -> List[Dict[str, Any]]:
        """
        List files in the specified folder.
        
        Args:
            folder_name: Name of subfolder to list (e.g., "0-QuickNotes")
                        If None, lists files in the root folder
        
        Returns:
            List of file metadata dictionaries
        """
        try:
            # Build query
            query_parts = [f"'{self.folder_id}' in parents"]
            
            # If folder_name specified, first find that folder
            if folder_name:
                folder_id = self._find_folder(folder_name)
                if folder_id:
                    query_parts = [f"'{folder_id}' in parents"]
                else:
                    logger.warning(f"Folder not found: {folder_name}")
                    return []
            
            # Only list files, not folders
            query_parts.append("mimeType != 'application/vnd.google-apps.folder'")
            query = " and ".join(query_parts)
            
            # Execute query
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, modifiedTime)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} files")
            return files
            
        except HttpError as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def _find_folder(self, folder_name: str) -> Optional[str]:
        """Find a folder by name within the root folder."""
        try:
            query = (
                f"'{self.folder_id}' in parents and "
                f"name = '{folder_name}' and "
                f"mimeType = 'application/vnd.google-apps.folder'"
            )
            
            results = self.service.files().list(
                q=query,
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            return None
            
        except HttpError as e:
            logger.error(f"Error finding folder: {e}")
            return None
    
    def read_file(self, file_id: str) -> bytes:
        """
        Read file content from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File content as bytes
        """
        try:
            file_content = self.service.files().get_media(fileId=file_id).execute()
            return file_content
        except HttpError as e:
            logger.error(f"Error reading file {file_id}: {e}")
            raise
    
    def rename_file(self, file_id: str, new_name: str):
        """
        Rename a file in Google Drive.
        
        Args:
            file_id: Google Drive file ID
            new_name: New name for the file
        """
        try:
            body = {'name': new_name}
            self.service.files().update(
                fileId=file_id,
                body=body
            ).execute()
            logger.info(f"Renamed file {file_id} to {new_name}")
        except HttpError as e:
            logger.error(f"Error renaming file {file_id}: {e}")
            raise
    
    def update_file(self, file_id: str, new_name: str, content: bytes):
        """
        Update file content and optionally rename.
        
        Args:
            file_id: Google Drive file ID
            new_name: New name for the file
            content: New content as bytes
        """
        try:
            # Prepare metadata
            body = {'name': new_name}
            
            # Prepare media upload
            media = MediaInMemoryUpload(
                content,
                mimetype='text/plain',
                resumable=True
            )
            
            # Update file
            self.service.files().update(
                fileId=file_id,
                body=body,
                media_body=media
            ).execute()
            
            logger.info(f"Updated file {file_id}")
            
        except HttpError as e:
            logger.error(f"Error updating file {file_id}: {e}")
            raise
    
    def handle_rate_limit(self, retry_count: int = 0):
        """Handle rate limiting with exponential backoff."""
        wait_time = (2 ** retry_count) * 1.0  # Exponential backoff
        logger.warning(f"Rate limited, waiting {wait_time} seconds...")
        time.sleep(wait_time)