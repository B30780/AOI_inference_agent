---
name: aoi-inference-agent
status: backlog
created: 2026-02-25T02:26:02Z
progress: 0%
prd: .claude/prds/aoi-inference-agent.md
github: https://github.com/B30780/AOI_inference_agent/issues/1
---

# Epic: AOI Inference Agent

## Overview

Build a FastAPI-based middleware service that orchestrates AOI (Automated Optical Inspection) workflows by integrating with an external SegFormer model service, managing image uploads (single/batch), persisting results to a relational database, and providing RESTful APIs with Swagger UI for result retrieval, visualization, and download.

**Technical Summary**: Create a clean, modular FastAPI application with SQLAlchemy ORM for database operations, httpx for external service integration, and a simple web UI for user interaction. The system will accept image uploads, forward them to http://140.96.77.124:8080/ for inference, store the returned results (JSON + 3 images) in aoi_db following the specified schema (images/classes/regions tables), and expose comprehensive APIs for querying and downloading historical data.

## Architecture Decisions

### 1. Framework Choice: FastAPI
**Decision**: Use FastAPI as the core web framework
**Rationale**: 
- Native async support for concurrent uploads
- Automatic OpenAPI/Swagger generation
- Built-in request validation with Pydantic
- High performance with Uvicorn ASGI server
- Modern Python type hints

### 2. Database: PostgreSQL
**Decision**: Use PostgreSQL as primary database
**Rationale**:
- Robust relational model for images/classes/regions schema
- Excellent JSON support for storing analysis results
- Strong ACID guarantees for data integrity
- Good performance for complex queries with foreign keys
- Wide adoption and tooling support

### 3. ORM: SQLAlchemy 2.0
**Decision**: Use SQLAlchemy for database abstraction
**Rationale**:
- Type-safe ORM with modern Python syntax
- Alembic integration for schema migrations
- Connection pooling and transaction management
- Prevents SQL injection with parameterized queries
- Supports both sync and async operations

### 4. External Service Integration: httpx
**Decision**: Use httpx for HTTP client operations
**Rationale**:
- Native async/await support
- Timeout and retry capabilities
- Compatible with FastAPI's async model
- Clean API for multipart file uploads
- Better than requests for modern async apps

### 5. File Storage Strategy: Local Filesystem
**Decision**: Store images on local filesystem with date-based organization
**Rationale**:
- Simple implementation (no cloud service dependency)
- Direct file access for downloads
- Organized by date (YYYYMMDD) for easy management
- Can migrate to S3 later if needed
- Sufficient for Phase 1 requirements

### 6. Startup Approach: run.py
**Decision**: Single run.py entry point (no Docker for Phase 1)
**Rationale**:
- Simplifies initial deployment
- Easy debugging and development
- Handles database initialization and app startup
- Can migrate to Docker later as needed
- Meets immediate project requirements

## Technical Approach

### Backend Services

#### 1. FastAPI Application Structure
```
app/
??? main.py              # FastAPI app initialization, middleware, startup/shutdown
??? config.py            # Configuration from environment variables
??? api/                 # Route handlers
??  ??? upload.py        # POST /upload, POST /upload/batch
??  ??? query.py         # GET /images, GET /images/{id}, GET /images/{id}/classes, GET /images/{id}/regions
??  ??? download.py      # GET /download/image, GET /download/batch, GET /download/json
??  ??? health.py        # GET /health, GET /stats
??? models/
??  ??? database.py      # SQLAlchemy models (Image, Class, Region)
??  ??? schemas.py       # Pydantic request/response models
??? services/
??  ??? segformer_client.py  # HTTP client for external SegFormer service
??  ??? storage.py           # File storage operations
??  ??? db_service.py        # Database operations (CRUD)
??? utils/
    ??? validators.py    # File validation (type, size)
    ??? helpers.py       # UUID generation, timestamp formatting
```

#### 2. Database Models (SQLAlchemy)
Implement three models matching database_schema.md:
- **Image**: img_unique_id, image_height, image_width, processing_time_seconds, timestamp, input_image_path, result_image_1_path, result_image_2_path, result_image_3_path
- **Class**: class_unique_id, img_unique_id (FK), class_id, class_name, total_regions, total_area_pixels
- **Region**: region_unique_id, class_unique_id (FK), img_unique_id (FK), region_id, centroid_x, centroid_y, bbox_x, bbox_y, bbox_width, bbox_height, area_pixels, perimeter, major_axis, minor_axis, circularity, aspect_ratio

Foreign keys with CASCADE delete to maintain referential integrity.

#### 3. External Service Integration
**SegFormer Client Service**:
- `async def infer_image(image_path: str) -> dict`: Send image to http://140.96.77.124:8080/
- Parse response to extract JSON analysis and 3 image files
- Implement retry logic (3 attempts with exponential backoff)
- Timeout handling (30s per request)
- Error parsing and meaningful error messages

#### 4. Storage Service
- `save_uploaded_file(file, date_folder) -> str`: Save to data/uploads/YYYYMMDD/
- `save_result_images(images_dict, output_folder) -> dict`: Save combined/mask/overlay to data/results/YYYYMMDD/
- `generate_batch_zip(batch_id) -> str`: Create ZIP archive of batch results
- File naming: `{timestamp}_{unique_id}_{original_name}`

#### 5. Database Service
- `create_image_record(data: dict) -> Image`: Insert into images table
- `create_class_records(img_id: str, classes_data: dict) -> list[Class]`: Bulk insert classes
- `create_region_records(class_id: str, regions_data: list) -> list[Region]`: Bulk insert regions
- `get_images(filters: dict, pagination: dict) -> list[Image]`: Query with filters
- `get_image_by_id(img_id: str) -> Image | None`: Retrieve single record
- All operations use SQLAlchemy sessions with proper transaction management

### Frontend Components (Web UI)

#### 1. Upload Interface (templates/index.html)
- Single file input with drag-and-drop support
- File format validation (client-side)
- Upload progress indicator
- Display results inline after upload
- Based on reference_doc/UI/templates/index.html

#### 2. Batch Upload Interface (templates/batch.html)
- Multiple file selector
- Upload queue visualization
- Progress bar per image
- Summary statistics after completion
- Based on reference_doc/UI/templates/batch_test.html

#### 3. Results Display
- Image viewer with tabs (input, combined, mask, overlay)
- JSON data table with formatted display
- Download buttons for images and JSON
- Defect count summary with color coding

#### 4. Static Assets
- CSS: Bootstrap 5 for responsive layout
- JavaScript: Vanilla JS (no framework needed for Phase 1)
- Fetch API for AJAX requests
- Local image preview before upload

### Infrastructure

#### Database Setup
- PostgreSQL database: `aoi_db`
- User/password from environment variables
- Connection pooling: min=5, max=20 connections
- Alembic migrations for schema versioning
- Initial migration creates tables with indexes

#### File Storage
- Base directory: `data/`
- Uploads: `data/uploads/YYYYMMDD/`
- Results: `data/results/YYYYMMDD/`
- Automatic directory creation on startup
- Disk space monitoring (log warnings at 80% capacity)

#### Configuration Management
- Environment variables via `.env` file
- Database URL, external service URL, storage paths
- Configurable timeouts, retry limits, batch size limits
- Development vs production settings

#### Logging
- Python logging module with JSON formatter
- Log levels: DEBUG (dev), INFO (prod)
- Log requests: method, path, status, duration
- Log external service calls: URL, status, response time
- Log database operations: query type, duration
- Separate log files: app.log, error.log

## Implementation Strategy

### Development Phases

**Phase 1: Core Infrastructure (Days 1-3)**
- Set up FastAPI project structure
- Configure database connection and SQLAlchemy models
- Create Alembic migrations
- Implement run.py startup script
- Basic logging and configuration

**Phase 2: External Service Integration (Days 4-5)**
- Implement SegFormer client with httpx
- Add retry logic and error handling
- Test connection to http://140.96.77.124:8080/
- Parse and validate response format

**Phase 3: Upload and Storage (Days 6-8)**
- POST /upload endpoint implementation
- File validation and storage
- Database record creation (images, classes, regions)
- POST /upload/batch with progress tracking

**Phase 4: Query and Download APIs (Days 9-11)**
- GET /images endpoints with pagination
- GET /images/{id}/classes and /regions
- Download endpoints for images and JSON
- Batch ZIP download

**Phase 5: Swagger and Testing (Days 12-13)**
- Integrate Swagger UI
- Document all endpoints
- Write unit tests for services
- Integration tests for API endpoints

**Phase 6: Web UI (Days 14-16)**
- HTML templates for upload and results
- JavaScript for file upload and display
- CSS styling and responsive design
- Integration with backend APIs

**Phase 7: Polish and Deploy (Days 17-18)**
- Performance optimization
- Error handling improvements
- Documentation (README, API guide)
- Final testing and bug fixes

### Risk Mitigation

**Risk: External service unavailable**
- Mitigation: Implement comprehensive error handling, retry logic, clear error messages to user
- Fallback: Queue failed uploads for manual retry

**Risk: Database performance issues**
- Mitigation: Proper indexing on foreign keys and query fields, connection pooling
- Monitoring: Log slow queries, add DB query profiling in development

**Risk: File storage exhaustion**
- Mitigation: Implement storage monitoring, log warnings, document cleanup procedures
- Future: Add automated cleanup policy for old files

**Risk: Concurrent upload conflicts**
- Mitigation: Use unique identifiers (UUID + timestamp), database transactions
- Testing: Load test with multiple concurrent users

### Testing Approach

**Unit Tests (pytest)**
- Database models and CRUD operations
- SegFormer client with mocked responses
- File storage operations
- Validation functions

**Integration Tests**
- API endpoints with test database
- Full upload ??store ??retrieve flow
- Batch upload scenarios
- Error cases and edge conditions

**Manual Testing**
- Upload various image formats and sizes
- Test with external service (requires access to http://140.96.77.124:8080/)
- UI functionality in different browsers
- Performance with large batches

## Task Breakdown Preview

High-level implementation tasks (target: ??0 tasks):

- [ ] **Task 1: Project Setup and Database Foundation**
  - Initialize FastAPI project structure
  - Configure SQLAlchemy models (Image, Class, Region)
  - Set up Alembic migrations
  - Create run.py entry point
  - Implement config.py with environment variables

- [ ] **Task 2: External Service Integration**
  - Implement SegFormer HTTP client (httpx)
  - Add retry logic and timeout handling
  - Parse and validate response (JSON + 3 images)
  - Error handling for connection failures

- [ ] **Task 3: File Storage Service**
  - Implement file upload handler with validation
  - Date-based directory organization
  - Save uploaded images and result images
  - Generate unique identifiers and file paths

- [ ] **Task 4: Upload API Endpoints**
  - POST /upload (single image)
  - POST /upload/batch (multiple images)
  - Integrate SegFormer client, storage, and database services
  - Transaction management and error handling

- [ ] **Task 5: Query API Endpoints**
  - GET /images (list with pagination and filters)
  - GET /images/{id} (retrieve single image data)
  - GET /images/{id}/classes (defect classes for image)
  - GET /images/{id}/regions (defect regions for image)
  - GET /health and GET /stats

- [ ] **Task 6: Download API Endpoints**
  - GET /download/image/{id}/{type} (download specific image)
  - GET /download/json/{id} (download analysis JSON)
  - GET /download/batch/{batch_id} (ZIP archive)

- [ ] **Task 7: Swagger UI Integration**
  - Configure FastAPI Swagger UI at /docs
  - Add endpoint descriptions and schemas
  - Include example requests/responses
  - Test interactive API documentation

- [ ] **Task 8: Web UI Implementation**
  - Create HTML templates (index.html, batch.html)
  - Implement upload forms (single and batch)
  - Build result display page with image viewer
  - Add CSS styling and responsive layout
  - JavaScript for AJAX upload and result display

- [ ] **Task 9: Testing Suite**
  - Unit tests for services (database, storage, client)
  - Integration tests for API endpoints
  - Test data fixtures and mocks
  - Achieve >70% test coverage

- [ ] **Task 10: Documentation and Deployment**
  - Write README with setup instructions
  - Create .env.example with all required variables
  - Database setup guide (create database, run migrations)
  - API usage examples
  - Troubleshooting guide

## Dependencies

### External Dependencies
- **SegFormer Service**: http://140.96.77.124:8080/ must be operational and accessible
- **PostgreSQL Database**: Version 14+ installed and configured
- **Python 3.9+**: Runtime environment

### Internal Dependencies
- **Database Schema**: Implementation must match reference_doc/database_schema.md exactly
- **Reference Materials**: UI design from reference_doc/UI/templates/
- **Sample Data**: Test with reference_doc/segformer_result/ examples

### Development Prerequisites
- Network access to external SegFormer service
- PostgreSQL admin credentials for database creation
- Development machine with 8GB+ RAM, 50GB+ disk space

## Success Criteria (Technical)

### Functional Success
- Single image upload successfully calls external service, stores results, returns data
- Batch upload processes 50+ images without failure
- Database contains all expected records (images, classes, regions) with correct foreign keys
- Query endpoints return accurate data with pagination
- Download endpoints serve correct files (images and JSON)
- Swagger UI displays all endpoints with documentation
- Web UI uploads images and displays results correctly

### Performance Benchmarks
- API response time <200ms for non-upload endpoints (95th percentile)
- Single image processing completes within external service time + 500ms overhead
- Database queries execute in <500ms (99th percentile)
- System handles 10 concurrent uploads without errors
- Batch upload of 100 images completes within 10 minutes

### Quality Gates
- All unit tests pass (>70% code coverage)
- Integration tests pass for all API endpoints
- No SQL injection vulnerabilities (parameterized queries only)
- No critical security issues (input validation, error handling)
- All Python code follows PEP 8 style guidelines
- Database migrations run successfully forward and backward

### Deployment Success
- `python run.py` starts application without errors
- Database initializes with correct schema
- Application connects to external SegFormer service
- Health check endpoint returns 200 OK
- Swagger UI accessible at /docs
- Web UI accessible and functional

## Estimated Effort

**Overall Timeline**: 3-4 weeks (18-20 working days)

**Resource Requirements**:
- 1 Backend Developer (FastAPI, SQLAlchemy): Full-time
- 1 Frontend Developer (HTML/CSS/JavaScript): Part-time (1 week)
- Database Administrator: Part-time (setup and configuration)
- QA Engineer: Part-time (testing phase)

**Critical Path Items**:
1. Database setup and schema implementation (Days 1-3)
2. External service integration and testing (Days 4-5)
3. Core upload and storage functionality (Days 6-8)
4. API endpoints and testing (Days 9-13)
5. UI implementation (Days 14-16)
6. Final testing and deployment (Days 17-18)

**Risks to Timeline**:
- External service availability/stability
- Database performance tuning may require additional time
- UI complexity if advanced features are requested
- Integration testing with external service

**Recommended Approach**: Start with Tasks 1-4 to build core functionality, then parallelize Tasks 5-6 (APIs) with Task 8 (UI), followed by Tasks 7, 9, 10 for polish and completion.

## Tasks Created

The following tasks have been synced to GitHub as sub-issues:

- [ ] [#2 - Project Setup and Database Foundation](https://github.com/B30780/AOI_inference_agent/issues/2) (L, 12-16h, sequential)
- [ ] [#3 - External Service Integration](https://github.com/B30780/AOI_inference_agent/issues/3) (M, 8-10h, sequential)
- [ ] [#4 - File Storage Service](https://github.com/B30780/AOI_inference_agent/issues/4) (M, 6-8h, parallel)
- [ ] [#5 - Upload API Endpoints](https://github.com/B30780/AOI_inference_agent/issues/5) (L, 12-16h, sequential)
- [ ] [#6 - Query API Endpoints](https://github.com/B30780/AOI_inference_agent/issues/6) (M, 8-10h, parallel)
- [ ] [#7 - Download API Endpoints](https://github.com/B30780/AOI_inference_agent/issues/7) (M, 6-8h, parallel)
- [ ] [#8 - Swagger UI Integration](https://github.com/B30780/AOI_inference_agent/issues/8) (S, 4-6h, sequential)
- [ ] [#9 - Web UI Implementation](https://github.com/B30780/AOI_inference_agent/issues/9) (M, 10-12h, parallel)
- [ ] [#10 - Testing Suite](https://github.com/B30780/AOI_inference_agent/issues/10) (L, 12-16h, sequential)
- [ ] [#11 - Documentation and Deployment](https://github.com/B30780/AOI_inference_agent/issues/11) (M, 8-10h, sequential)

**Summary:**
- Total tasks: 10
- Parallel tasks: 4 (can be worked on simultaneously after dependencies met)
- Sequential tasks: 6 (have blocking dependencies)
- Total estimated effort: 86-112 hours (approximately 2-3 weeks for 1 developer)

**Parallelization Opportunities:**
- Tasks #3 and #4 can be developed in parallel (both depend only on #2)
- Tasks #6 and #7 can be developed in parallel (both depend on #2, #5)
- Task #9 can be developed in parallel with Tasks #6-#7

