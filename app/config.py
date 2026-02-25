"""
Application configuration management
Loads settings from environment variables
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Info
    app_name: str = "AOI Inference Agent"
    app_version: str = "1.0.0"
    
    # Database Configuration
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/aoi_inference_db"
    )
    db_pool_size: int = 5
    db_max_overflow: int = 15  # Total max connections = pool_size + max_overflow = 20
    db_pool_pre_ping: bool = True
    db_echo: bool = False
    
    # External Service Configuration
    segformer_service_url: str = os.getenv(
        "SEGFORMER_SERVICE_URL",
        "http://140.96.77.124:8080/"
    )
    segformer_timeout: int = 300  # 5 minutes timeout for image processing
    
    # Storage Configuration
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
    result_dir: Path = Path(os.getenv("RESULT_DIR", "data/results"))
    
    # File Upload Settings
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    allowed_extensions: set = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
    
    # Server Configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    reload: bool = os.getenv("RELOAD", "False").lower() == "true"
    
    # Logging Configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS Configuration
    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL"""
        return self.database_url
    
    @property
    def database_url_async(self) -> str:
        """Get asynchronous database URL"""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024


# Global settings instance
settings = Settings()
