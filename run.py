"""
AOI Inference Agent - Application Entry Point
Initializes database, runs migrations, and starts the Uvicorn server
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import app components after environment is loaded
from app.config import settings
from app.models.database import engine, Base, check_connection, create_tables


def run_alembic_migrations():
    """
    Run Alembic database migrations to ensure schema is up to date
    
    Returns:
        bool: True if migrations successful, False otherwise
    """
    logger.info("Running Alembic database migrations...")
    try:
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Alembic migrations completed successfully")
        if result.stdout:
            logger.debug(f"Alembic output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Alembic migration failed: {e}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("Alembic not found. Please ensure Alembic is installed.")
        return False


def initialize_database():
    """
    Initialize database connection and create tables if they don't exist
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    logger.info("Initializing database connection...")
    
    # Check database connection
    if not check_connection():
        logger.error("Failed to connect to database. Please check your DATABASE_URL configuration.")
        return False
    
    # Run migrations
    if not run_alembic_migrations():
        logger.warning("Alembic migrations failed. Attempting to create tables manually...")
        try:
            create_tables()
            logger.info("Tables created successfully via SQLAlchemy")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            return False
    
    logger.info("Database initialization completed successfully")
    return True


def ensure_directories():
    """
    Ensure required directories exist for uploads and results
    """
    logger.info("Checking required directories...")
    
    # Upload directory
    if not settings.upload_dir.exists():
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created upload directory: {settings.upload_dir}")
    else:
        logger.info(f"Upload directory exists: {settings.upload_dir}")
    
    # Result directory
    if not settings.result_dir.exists():
        settings.result_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created result directory: {settings.result_dir}")
    else:
        logger.info(f"Result directory exists: {settings.result_dir}")


def validate_configuration():
    """
    Validate critical configuration settings
    
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    logger.info("Validating configuration...")
    
    errors = []
    
    # Check database URL
    if not settings.database_url:
        errors.append("DATABASE_URL is not configured")
    
    # Check segformer service URL
    if not settings.segformer_service_url:
        errors.append("SEGFORMER_SERVICE_URL is not configured")
    
    # Check storage directories
    try:
        ensure_directories()
    except Exception as e:
        errors.append(f"Failed to create directories: {e}")
    
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    logger.info("Configuration validation passed")
    return True


def start_server():
    """
    Start the Uvicorn server with the FastAPI application
    """
    import uvicorn
    
    logger.info("="*80)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("="*80)
    logger.info(f"Server will be available at: http://{settings.host}:{settings.port}")
    logger.info(f"API Documentation (Swagger UI): http://{settings.host}:{settings.port}/docs")
    logger.info(f"API Documentation (ReDoc): http://{settings.host}:{settings.port}/redoc")
    logger.info("="*80)
    
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
            log_level=settings.log_level.lower(),
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


def main():
    """
    Main entry point for the application
    Orchestrates initialization and server startup
    """
    try:
        # Print banner
        logger.info("")
        logger.info("="*80)
        logger.info(f"  {settings.app_name} - Starting Application")
        logger.info("="*80)
        logger.info("")
        
        # Step 1: Validate configuration
        if not validate_configuration():
            logger.error("Configuration validation failed. Please check your .env file.")
            sys.exit(1)
        
        # Step 2: Initialize database
        if not initialize_database():
            logger.error("Database initialization failed. Please check your database connection.")
            sys.exit(1)
        
        # Step 3: Start server
        start_server()
        
    except KeyboardInterrupt:
        logger.info("")
        logger.info("="*80)
        logger.info("Application shutdown requested by user (Ctrl+C)")
        logger.info("="*80)
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error during startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
