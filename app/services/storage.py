"""
File Storage Service
Handles saving uploaded images, organizing files by date, 
saving inference result images, and generating batch ZIP archives.
"""

from pathlib import Path
from datetime import datetime
import zipfile
import shutil
from typing import Dict, BinaryIO, Optional
from fastapi import UploadFile

from app.config import settings

# Temporary placeholders for utils (Stream B is implementing these in parallel)
# These will be replaced with proper imports once Stream B completes
try:
    from app.utils.validators import validate_file_type, validate_file_size
    from app.utils.helpers import generate_unique_id, get_timestamp
except ImportError:
    # Temporary fallback implementations until Stream B completes
    import uuid
    
    def validate_file_type(filename: str) -> None:
        """Temporary placeholder - validates file extension"""
        ext = Path(filename).suffix.lower()
        if ext not in settings.allowed_extensions:
            raise ValueError(f"File type {ext} not allowed. Allowed types: {settings.allowed_extensions}")
    
    def validate_file_size(file: BinaryIO, max_size: int) -> None:
        """Temporary placeholder - validates file size"""
        # This is a simplified version; Stream B will implement proper validation
        pass
    
    def generate_unique_id() -> str:
        """Temporary placeholder - generates UUID"""
        return str(uuid.uuid4())[:8]
    
    def get_timestamp() -> str:
        """Temporary placeholder - gets formatted timestamp"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")


class StorageService:
    """
    Service for managing file storage operations.
    
    Handles:
    - Saving uploaded files to date-organized directories
    - Saving inference result images
    - Generating ZIP archives for batch downloads
    - Path resolution for file access
    """
    
    def __init__(self):
        """Initialize storage service with configured directories."""
        self.upload_dir = Path(settings.upload_dir)
        self.result_dir = Path(settings.result_dir)
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure base upload and result directories exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_uploaded_file(self, file: UploadFile, filename: str) -> str:
        """
        Save uploaded file to date-organized directory.
        
        Args:
            file: FastAPI UploadFile object
            filename: Original filename
            
        Returns:
            str: Full path to saved file
            
        Raises:
            ValueError: If file validation fails
            IOError: If file save operation fails
        """
        # Validate file
        validate_file_type(filename)
        # Note: file size validation will be added once Stream B completes
        # For now, FastAPI's request size limits provide basic protection
        
        # Create date folder (YYYYMMDD format)
        date_str = datetime.now().strftime("%Y%m%d")
        date_dir = self.upload_dir / date_str
        date_dir.mkdir(exist_ok=True)
        
        # Generate unique filename: {timestamp}_{unique_id}_{original_name}
        unique_id = generate_unique_id()
        timestamp = get_timestamp()
        new_filename = f"{timestamp}_{unique_id}_{filename}"
        
        # Save file
        file_path = date_dir / new_filename
        try:
            contents = await file.read()
            with open(file_path, 'wb') as f:
                f.write(contents)
        except Exception as e:
            raise IOError(f"Failed to save file {filename}: {str(e)}")
        
        return str(file_path)
    
    async def save_result_images(
        self, 
        images: Dict[str, bytes], 
        img_unique_id: str
    ) -> Dict[str, str]:
        """
        Save inference result images to date-organized directory.
        
        Args:
            images: Dictionary with image types as keys ('combined', 'mask', 'overlay')
                   and image bytes as values
            img_unique_id: Unique identifier for this inference result
            
        Returns:
            Dict[str, str]: Dictionary mapping image types to their saved file paths
            
        Raises:
            IOError: If image save operation fails
        """
        # Create date and result-specific folder: data/results/YYYYMMDD/{img_unique_id}/
        date_str = datetime.now().strftime("%Y%m%d")
        date_dir = self.result_dir / date_str / img_unique_id
        date_dir.mkdir(parents=True, exist_ok=True)
        
        paths = {}
        try:
            for img_type, img_data in images.items():
                # Save with format: {img_unique_id}_{img_type}.png
                file_path = date_dir / f"{img_unique_id}_{img_type}.png"
                with open(file_path, 'wb') as f:
                    f.write(img_data)
                paths[img_type] = str(file_path)
        except Exception as e:
            raise IOError(f"Failed to save result images for {img_unique_id}: {str(e)}")
        
        return paths
    
    async def generate_batch_zip(self, batch_id: str) -> str:
        """
        Create ZIP archive of all results for a specific batch.
        
        Args:
            batch_id: Unique identifier for the batch
            
        Returns:
            str: Path to the generated ZIP file
            
        Raises:
            FileNotFoundError: If batch results directory doesn't exist
            IOError: If ZIP creation fails
        """
        # Search for batch results across all date folders
        zip_filename = f"batch_{batch_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = self.result_dir / zip_filename
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Iterate through all date folders in results directory
                for date_folder in self.result_dir.iterdir():
                    if not date_folder.is_dir() or date_folder.name == zip_filename:
                        continue
                    
                    # Look for result folders that match the batch_id
                    for result_folder in date_folder.iterdir():
                        if result_folder.is_dir() and batch_id in result_folder.name:
                            # Add all files from this result folder to the zip
                            for file_path in result_folder.iterdir():
                                if file_path.is_file():
                                    # Archive path preserves folder structure
                                    arcname = str(file_path.relative_to(self.result_dir))
                                    zipf.write(file_path, arcname=arcname)
            
            if zip_path.exists() and zip_path.stat().st_size > 0:
                return str(zip_path)
            else:
                raise FileNotFoundError(f"No results found for batch {batch_id}")
                
        except Exception as e:
            # Clean up partial zip file if it exists
            if zip_path.exists():
                zip_path.unlink()
            raise IOError(f"Failed to create ZIP archive for batch {batch_id}: {str(e)}")
    
    def get_file_path(self, relative_path: str) -> Path:
        """
        Resolve relative path to absolute path within storage directories.
        
        Args:
            relative_path: Path relative to either upload_dir or result_dir
            
        Returns:
            Path: Resolved absolute path
            
        Raises:
            ValueError: If path is outside storage directories (security check)
            FileNotFoundError: If resolved path doesn't exist
        """
        # Try to resolve relative to result_dir first, then upload_dir
        for base_dir in [self.result_dir, self.upload_dir]:
            potential_path = (base_dir / relative_path).resolve()
            
            # Security check: ensure resolved path is within base directory
            try:
                potential_path.relative_to(base_dir.resolve())
            except ValueError:
                continue
            
            if potential_path.exists():
                return potential_path
        
        # If not found in either directory, raise error
        raise FileNotFoundError(f"File not found: {relative_path}")
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """
        Clean up files older than specified number of days.
        
        Args:
            days: Number of days to retain files (default: 30)
            
        Returns:
            int: Number of files deleted
            
        Note:
            This is a utility method for maintenance operations.
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for base_dir in [self.upload_dir, self.result_dir]:
            for date_folder in base_dir.iterdir():
                if not date_folder.is_dir():
                    continue
                
                try:
                    # Parse folder name as date (YYYYMMDD format)
                    folder_date = datetime.strptime(date_folder.name, "%Y%m%d")
                    
                    if folder_date < cutoff_date:
                        # Delete entire date folder
                        shutil.rmtree(date_folder)
                        deleted_count += sum(1 for _ in date_folder.rglob('*') if _.is_file())
                except (ValueError, OSError):
                    # Skip folders that don't match date format or can't be deleted
                    continue
        
        return deleted_count


# Global storage service instance
storage_service = StorageService()
