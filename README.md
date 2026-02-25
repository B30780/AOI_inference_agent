# AOI Inference Agent

A FastAPI-based web service for Automated Optical Inspection (AOI) defect detection and analysis using Segformer models. This service provides a complete pipeline for image upload, defect segmentation, region analysis, and result storage in a PostgreSQL database.

## Features

- **Image Upload & Processing**: Upload images for defect detection analysis
- **Segformer Integration**: Connects to external Segformer service for AI-based defect segmentation
- **Database Storage**: Stores analysis results in PostgreSQL with three-table schema (Images, Classes, Regions)
- **RESTful API**: FastAPI-based endpoints with automatic OpenAPI documentation
- **Geometric Analysis**: Calculates centroid, bounding box, area, perimeter, and shape metrics for each defect
- **Four Defect Classes**: PI_Particle, PR_Peeling, Copper_Nodule, Env_Particle

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9 or higher** - [Download Python](https://www.python.org/downloads/)
- **PostgreSQL 12 or higher** - [Download PostgreSQL](https://www.postgresql.org/download/)
- **Git** (optional) - For cloning the repository

## Project Structure

```
AOI_inference_agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── api/                 # API endpoints (future)
│   ├── models/
│   │   ├── database.py      # Database connection setup
│   │   └── schemas.py       # SQLAlchemy ORM models
│   ├── services/            # Business logic (future)
│   └── utils/               # Utility functions (future)
├── alembic/                 # Database migrations
│   ├── versions/            # Migration scripts
│   └── env.py               # Alembic configuration
├── data/
│   ├── uploads/             # Uploaded images
│   └── results/             # Processing results
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
├── alembic.ini              # Alembic configuration
├── .env                     # Environment variables (create this)
└── README.md                # This file
```

## Installation & Setup

### 1. Clone or Download the Repository

```bash
cd d:\Anson_Project\AOI\AOI_inference_agent
```

### 2. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/MacOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

The `.env` file already exists in the project root. Update it with your database credentials:

```dotenv
# Database Configuration
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/aoi_inference_db

# External Service Configuration
SEGFORMER_SERVICE_URL=http://140.96.77.124:8080/

# Storage Paths
UPLOAD_DIR=data/uploads
RESULT_DIR=data/results

# Application Settings
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=50

# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=False
```

**Important:** Replace `your_password` with your actual PostgreSQL password.

### 5. Create PostgreSQL Database

Open PostgreSQL command line (psql) or pgAdmin and create the database:

```sql
CREATE DATABASE aoi_inference_db;
```

Alternatively, using PowerShell/Command Prompt:

```bash
psql -U postgres -c "CREATE DATABASE aoi_inference_db;"
```

### 6. Verify Database Connection

You can test the connection using psql:

```bash
psql -U postgres -d aoi_inference_db
```

Type `\q` to exit psql.

## Running the Application

### Start the Server

From the project root directory (with virtual environment activated):

```bash
python run.py
```

The application will:
1. Load environment variables from `.env`
2. Validate configuration
3. Connect to the PostgreSQL database
4. Run Alembic migrations to create/update tables
5. Start the Uvicorn server

### Expected Output

```
================================================================================
  AOI Inference Agent - Starting Application
================================================================================

2026-02-25 14:00:00 - __main__ - INFO - Validating configuration...
2026-02-25 14:00:00 - __main__ - INFO - Upload directory exists: data\uploads
2026-02-25 14:00:00 - __main__ - INFO - Result directory exists: data\results
2026-02-25 14:00:00 - __main__ - INFO - Configuration validation passed
2026-02-25 14:00:00 - __main__ - INFO - Initializing database connection...
2026-02-25 14:00:00 - app.models.database - INFO - Database connection check: SUCCESS
2026-02-25 14:00:00 - __main__ - INFO - Running Alembic database migrations...
2026-02-25 14:00:01 - __main__ - INFO - Alembic migrations completed successfully
2026-02-25 14:00:01 - __main__ - INFO - Database initialization completed successfully
================================================================================
Starting AOI Inference Agent v1.0.0
================================================================================
Server will be available at: http://0.0.0.0:8000
API Documentation (Swagger UI): http://0.0.0.0:8000/docs
API Documentation (ReDoc): http://0.0.0.0:8000/redoc
================================================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Accessing the API

Once the server is running, you can access:

### Interactive API Documentation (Swagger UI)

Open your browser and navigate to:
```
http://localhost:8000/docs
```

This provides an interactive interface to:
- View all available endpoints
- Test API calls directly from the browser
- See request/response schemas
- Download OpenAPI specification

### Alternative Documentation (ReDoc)

```
http://localhost:8000/redoc
```

### Root Endpoint

```
http://localhost:8000/
```

Returns basic application information:
```json
{
  "message": "Welcome to AOI Inference Agent",
  "version": "1.0.0",
  "status": "running",
  "timestamp": "2026-02-25T14:00:00.000000"
}
```

### Health Check

```
http://localhost:8000/health
```

Returns service health status:
```json
{
  "status": "healthy",
  "service": "AOI Inference Agent",
  "version": "1.0.0",
  "timestamp": "2026-02-25T14:00:00.000000"
}
```

### API Information

```
http://localhost:8000/api/info
```

Returns configuration details:
```json
{
  "app_name": "AOI Inference Agent",
  "version": "1.0.0",
  "upload_dir": "data/uploads",
  "result_dir": "data/results",
  "max_file_size_mb": 50,
  "allowed_extensions": [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"],
  "segformer_service": "http://140.96.77.124:8080/",
  "timestamp": "2026-02-25T14:00:00.000000"
}
```

## Database Schema

The application uses a three-table schema:

### Images Table
- `img_unique_id` (PK): Unique identifier for each image
- `image_height`, `image_width`: Image dimensions
- `processing_time_seconds`: Time taken for processing
- `timestamp`: When the analysis was performed
- `input_image_path`: Path to original image
- `result_image_1_path`, `result_image_2_path`, `result_image_3_path`: Paths to result images
- `created_at`: Record creation timestamp

### Classes Table
- `class_unique_id` (PK): Unique identifier for each class instance
- `img_unique_id` (FK): Reference to Images table (CASCADE delete)
- `class_id`: Class number (1-4)
- `class_name`: Class name (PI_Particle, PR_Peeling, Copper_Nodule, Env_Particle)
- `total_regions`: Number of regions in this class
- `total_area_pixels`: Total pixel area for this class
- `created_at`: Record creation timestamp

### Regions Table
- `region_unique_id` (PK): Unique identifier for each region
- `class_unique_id` (FK): Reference to Classes table (CASCADE delete)
- `img_unique_id` (FK): Reference to Images table (CASCADE delete)
- `region_id`: Region number within the class
- `centroid_x`, `centroid_y`: Centroid coordinates
- `bbox_x`, `bbox_y`, `bbox_width`, `bbox_height`: Bounding box
- `area_pixels`: Region area in pixels
- `perimeter`: Region perimeter
- `major_axis`, `minor_axis`: Ellipse fit axes
- `circularity`: Shape circularity metric (0-1)
- `aspect_ratio`: Width/height ratio
- `created_at`: Record creation timestamp

## Database Migrations

### View Migration Status

```bash
alembic current
```

### View Migration History

```bash
alembic history
```

### Create New Migration (after model changes)

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migrations

```bash
alembic downgrade -1  # Rollback one migration
alembic downgrade base  # Rollback all migrations
```

## Development

### Enable Auto-Reload

For development, you can enable auto-reload when code changes:

1. Edit `.env` file:
```dotenv
RELOAD=True
```

2. Or set environment variable before running:
```bash
$env:RELOAD="True"
python run.py
```

### Check Database Tables

Using psql:
```bash
psql -U postgres -d aoi_inference_db
\dt  # List all tables
\d images  # Describe images table
\d classes  # Describe classes table
\d regions  # Describe regions table
```

### View Application Logs

The application logs to stdout with the following format:
```
timestamp - logger_name - level - message
```

Adjust log level in `.env`:
```dotenv
LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Troubleshooting

### Database Connection Error

**Error:** `Failed to connect to database`

**Solutions:**
1. Verify PostgreSQL is running:
   ```bash
   # Windows (Services)
   Get-Service postgresql*
   
   # Or check if port 5432 is listening
   netstat -an | findstr 5432
   ```

2. Check database exists:
   ```bash
   psql -U postgres -l
   ```

3. Verify credentials in `.env` file

4. Test connection:
   ```bash
   psql -U postgres -d aoi_inference_db
   ```

### Alembic Migration Error

**Error:** `Alembic migration failed`

**Solutions:**
1. Check alembic.ini configuration
2. Verify database connection
3. Run migrations manually:
   ```bash
   alembic upgrade head
   ```
4. Check migration version:
   ```bash
   alembic current
   ```

### Port Already in Use

**Error:** `Address already in use`

**Solutions:**
1. Change port in `.env`:
   ```dotenv
   PORT=8001
   ```

2. Or kill process using port 8000:
   ```powershell
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <process_id> /F
   ```

### Module Import Error

**Error:** `ModuleNotFoundError`

**Solutions:**
1. Ensure virtual environment is activated
2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Permission Error for Directories

**Error:** `Permission denied` when creating directories

**Solutions:**
1. Run as administrator (Windows)
2. Check directory permissions
3. Create directories manually:
   ```bash
   mkdir -p data/uploads data/results
   ```

## Testing

### Manual API Testing with curl

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Get API Info:**
```bash
curl http://localhost:8000/api/info
```

### Using Swagger UI

1. Navigate to http://localhost:8000/docs
2. Click on any endpoint to expand
3. Click "Try it out"
4. Fill in parameters (if any)
5. Click "Execute"
6. View response

## Production Deployment

### Environment Variables for Production

```dotenv
RELOAD=False
LOG_LEVEL=WARNING
HOST=0.0.0.0
PORT=8000
```

### Run with Gunicorn (Linux)

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Run as Windows Service

Use NSSM (Non-Sucking Service Manager) to run as a Windows service:
1. Download NSSM from https://nssm.cc/
2. Install service:
   ```bash
   nssm install AOIInferenceAgent "C:\path\to\venv\Scripts\python.exe" "C:\path\to\run.py"
   ```

### Docker Deployment (Future)

Docker support can be added with a Dockerfile:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

## API Endpoints (Future Implementation)

The following endpoints will be implemented in future iterations:

- `POST /api/images/upload` - Upload image for analysis
- `GET /api/images/{img_id}` - Get image details
- `GET /api/images/{img_id}/classes` - Get classes for an image
- `GET /api/images/{img_id}/regions` - Get all regions for an image
- `GET /api/classes/{class_id}/regions` - Get regions for a specific class
- `DELETE /api/images/{img_id}` - Delete image and all related data

## Contributing

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Update documentation
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues, questions, or contributions, please contact the development team.

## Version History

- **v1.0.0** (2026-02-25) - Initial release
  - Project structure and configuration
  - Database models and migrations
  - FastAPI application setup
  - Basic API endpoints

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
