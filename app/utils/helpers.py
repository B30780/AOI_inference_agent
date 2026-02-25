"""
Helper utility functions
Provides UUID generation, timestamp formatting, and other utilities
"""

import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path


def generate_unique_id() -> str:
    """
    Generate a unique identifier using UUID4.
    
    Returns:
        A UUID string (e.g., 'a1b2c3d4-e5f6-4789-abcd-ef0123456789')
    """
    return str(uuid.uuid4())


def get_timestamp(format: str = "%Y%m%d_%H%M%S") -> str:
    """
    Get current timestamp as formatted string.
    
    Args:
        format: strftime format string (default: '%Y%m%d_%H%M%S')
        
    Returns:
        Formatted timestamp string (e.g., '20260225_143022')
    """
    return datetime.now().strftime(format)


def get_date_folder() -> str:
    """
    Get current date in YYYYMMDD format for folder organization.
    
    Returns:
        Date string in YYYYMMDD format (e.g., '20260225')
    """
    return datetime.now().strftime("%Y%m%d")


def generate_filename(original_filename: str, prefix: Optional[str] = None) -> str:
    """
    Generate a unique filename with timestamp and UUID.
    
    Args:
        original_filename: Original name of the file
        prefix: Optional prefix to add before timestamp
        
    Returns:
        Generated filename: [prefix_]timestamp_uuid_originalname
    """
    timestamp = get_timestamp()
    unique_id = generate_unique_id()
    
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}_{original_filename}"
    else:
        return f"{timestamp}_{unique_id}_{original_filename}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing or replacing problematic characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for file systems
    """
    # Remove or replace characters that are problematic in filenames
    # Keep alphanumeric, dots, hyphens, and underscores
    import re
    
    # Get the file extension first
    path = Path(filename)
    name = path.stem
    ext = path.suffix
    
    # Replace problematic characters with underscore
    sanitized_name = re.sub(r'[^\w\-.]', '_', name)
    
    # Remove multiple consecutive underscores
    sanitized_name = re.sub(r'_+', '_', sanitized_name)
    
    # Remove leading/trailing underscores
    sanitized_name = sanitized_name.strip('_')
    
    return f"{sanitized_name}{ext}"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable string.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted string (e.g., '1.5 MB', '250 KB')
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Path to directory
        
    Returns:
        The path object (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_relative_path(full_path: Path, base_path: Path) -> Path:
    """
    Get relative path from base path to full path.
    
    Args:
        full_path: The full path
        base_path: The base path to calculate relative to
        
    Returns:
        Relative path
    """
    try:
        return full_path.relative_to(base_path)
    except ValueError:
        # If paths are not relative, return the full path
        return full_path
