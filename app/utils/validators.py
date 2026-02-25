"""
File validation utilities
Provides validation for file types and sizes
"""

from pathlib import Path
from typing import BinaryIO, Union
from fastapi import UploadFile, HTTPException


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_file_type(filename: str) -> None:
    """
    Validate file extension against allowed types.
    
    Args:
        filename: Name of the file to validate
        
    Raises:
        ValidationError: If file type is not allowed
    """
    # Allowed image file extensions
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    
    file_path = Path(filename)
    file_extension = file_path.suffix.lower()
    
    if not file_extension:
        raise ValidationError(
            f"File '{filename}' has no extension. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    
    if file_extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type '{file_extension}' is not allowed. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def validate_file_size(file: Union[BinaryIO, UploadFile], max_size_mb: int = 50) -> None:
    """
    Validate file size does not exceed maximum limit.
    
    Args:
        file: File object to validate (BinaryIO or FastAPI UploadFile)
        max_size_mb: Maximum file size in megabytes (default: 50MB)
        
    Raises:
        ValidationError: If file size exceeds the limit
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Handle FastAPI UploadFile
    if isinstance(file, UploadFile):
        # Get current position
        current_pos = file.file.tell()
        
        # Seek to end to get file size
        file.file.seek(0, 2)  # SEEK_END
        file_size = file.file.tell()
        
        # Reset to original position
        file.file.seek(current_pos)
        
    # Handle standard file objects with seek
    elif hasattr(file, 'seek') and hasattr(file, 'tell'):
        # Get current position
        current_pos = file.tell()
        
        # Seek to end to get file size
        file.seek(0, 2)  # SEEK_END
        file_size = file.tell()
        
        # Reset to original position
        file.seek(current_pos)
        
    # Handle file-like objects with size attribute
    elif hasattr(file, 'size'):
        file_size = file.size
        
    else:
        # If we can't determine size, try to read and check
        try:
            content = file.read()
            file_size = len(content)
            # Try to reset position if possible
            if hasattr(file, 'seek'):
                file.seek(0)
        except Exception as e:
            raise ValidationError(f"Unable to determine file size: {str(e)}")
    
    if file_size > max_size_bytes:
        size_mb = file_size / (1024 * 1024)
        raise ValidationError(
            f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
        )


def validate_file(file: Union[BinaryIO, UploadFile], filename: str, max_size_mb: int = 50) -> None:
    """
    Perform comprehensive file validation (type and size).
    
    Args:
        file: File object to validate
        filename: Name of the file
        max_size_mb: Maximum file size in megabytes (default: 50MB)
        
    Raises:
        ValidationError: If validation fails
    """
    validate_file_type(filename)
    validate_file_size(file, max_size_mb)
