"""Utility functions for the note assistant."""

import hashlib
import yaml
from typing import Tuple, Dict, Any


def calculate_file_hash(content: str) -> str:
    """
    Calculate SHA-256 hash of content.
    
    Args:
        content: Text content to hash
        
    Returns:
        str: SHA-256 hash in format "sha256:hexdigest"
    """
    hash_obj = hashlib.sha256(content.encode('utf-8'))
    return f"sha256:{hash_obj.hexdigest()}"


def parse_frontmatter(content: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parse YAML frontmatter from content.
    
    Args:
        content: Full content including potential frontmatter
        
    Returns:
        Tuple of (content_without_frontmatter, frontmatter_dict)
    """
    if not content.startswith('---\n'):
        return content, {}
    
    try:
        # Find the closing ---
        end_index = content.find('\n---\n', 4)
        if end_index == -1:
            return content, {}
        
        # Extract frontmatter
        frontmatter_text = content[4:end_index]
        content_without_fm = content[end_index + 5:]  # Skip past \n---\n
        
        # Parse YAML
        frontmatter = yaml.safe_load(frontmatter_text) or {}
        
        return content_without_fm, frontmatter
        
    except yaml.YAMLError:
        # If YAML parsing fails, return original content
        return content, {}


def generate_frontmatter(metadata: Dict[str, Any]) -> str:
    """
    Generate YAML frontmatter from metadata.
    
    Args:
        metadata: Dictionary of metadata fields
        
    Returns:
        str: Formatted YAML frontmatter with --- delimiters
    """
    # Ensure consistent ordering
    ordered_keys = [
        'processed_datetime',
        'note_hash',
        'summary',
        'tags',
        'para_suggestion',
        'confidence_score',
        'processing_version',
        'original_length'
    ]
    
    # Build ordered dict
    ordered_metadata = {}
    for key in ordered_keys:
        if key in metadata:
            ordered_metadata[key] = metadata[key]
    
    # Add any extra keys
    for key, value in metadata.items():
        if key not in ordered_metadata:
            ordered_metadata[key] = value
    
    # Generate YAML
    yaml_content = yaml.dump(
        ordered_metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False
    )
    
    return f"---\n{yaml_content}---\n"