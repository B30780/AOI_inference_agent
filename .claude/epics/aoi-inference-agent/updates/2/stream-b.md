---
stream: B
issue: 2
title: Database Models & Schema
completed: 2026-02-25T11:05:00Z
status: completed
---

# Stream B: Database Models & Schema - Completion Report

## Summary
Successfully implemented SQLAlchemy ORM models for the AOI inference database, including Image, Class, and Region tables with proper foreign key relationships and CASCADE delete constraints.

## Files Created

### 1. app/models/database.py
**Purpose**: Database engine and session configuration
**Key Features**:
- SQLAlchemy engine with QueuePool configuration (min=5, max=20 connections)
- Session factory (SessionLocal) for creating database sessions
- `get_db()` dependency function for FastAPI route injection
- `get_db_context()` context manager for manual session management
- Connection pool monitoring with event listeners
- Utility functions: `create_tables()`, `drop_tables()`, `check_connection()`
- Proper error handling and logging

### 2. app/models/schemas.py
**Purpose**: ORM models for database tables
**Key Features**:

#### Image Model
- Primary key: `img_unique_id` (VARCHAR(255))
- Image dimensions: `image_height`, `image_width` (INTEGER)
- Processing metrics: `processing_time_seconds` (FLOAT), `timestamp` (DATETIME)
- File paths: `input_image_path`, `result_image_1_path`, `result_image_2_path`, `result_image_3_path` (VARCHAR(500))
- Metadata: `created_at` (DATETIME with server default)
- Relationships: One-to-many with Class and Region (CASCADE delete)
- Index on `timestamp` for efficient time-based queries

#### Class Model
- Primary key: `class_unique_id` (VARCHAR(255))
- Foreign key: `img_unique_id` → images.img_unique_id (CASCADE delete)
- Class info: `class_id` (INTEGER 1-4), `class_name` (VARCHAR(100))
- Statistics: `total_regions`, `total_area_pixels` (INTEGER)
- Metadata: `created_at` (DATETIME with server default)
- Relationships: Many-to-one with Image, one-to-many with Region (CASCADE delete)
- Indexes on `img_unique_id` and `class_id`

#### Region Model
- Primary key: `region_unique_id` (VARCHAR(255))
- Foreign keys: 
  - `class_unique_id` → classes.class_unique_id (CASCADE delete)
  - `img_unique_id` → images.img_unique_id (CASCADE delete)
- Region ID: `region_id` (INTEGER)
- Centroid: `centroid_x`, `centroid_y` (FLOAT)
- Bounding box: `bbox_x`, `bbox_y`, `bbox_width`, `bbox_height` (INTEGER)
- Geometric properties: `area_pixels` (INTEGER), `perimeter`, `major_axis`, `minor_axis` (FLOAT)
- Shape metrics: `circularity`, `aspect_ratio` (FLOAT)
- Metadata: `created_at` (DATETIME with server default)
- Relationships: Many-to-one with both Class and Image
- Indexes on `class_unique_id`, `img_unique_id`, and `region_id`

#### Composite Indexes
- `idx_classes_img_class`: (img_unique_id, class_id)
- `idx_regions_img_class`: (img_unique_id, class_unique_id)
- `idx_regions_class_region`: (class_unique_id, region_id)

#### Class Names Enum
```python
CLASS_NAMES = {
    1: "PI_Particle",
    2: "PR_Peeling",
    3: "Copper_Nodule",
    4: "Env_Particle"
}
```

### 3. app/models/__init__.py
**Purpose**: Package initialization and exports
**Exports**:
- Database setup: Base, engine, SessionLocal, get_db, get_db_context, create_tables, drop_tables, check_connection
- ORM Models: Image, Class, Region, CLASS_NAMES

## Implementation Details

### Foreign Key Relationships
All foreign key relationships are properly configured with `ondelete="CASCADE"`:
- Deleting an Image automatically deletes all associated Classes and Regions
- Deleting a Class automatically deletes all associated Regions
- SQLAlchemy relationships use `cascade="all, delete-orphan"` and `passive_deletes=True`

### Connection Pooling
- Pool size: 5 (base connections)
- Max overflow: 15 (additional connections)
- Total max connections: 20
- Pre-ping enabled: Ensures connections are alive before use
- QueuePool: Thread-safe connection management

### Schema Compliance
All models strictly follow the schema defined in `reference_doc/database_schema.md`:
- Column names match exactly
- Data types match specification (VARCHAR, INTEGER, FLOAT, DATETIME)
- Constraints implemented (PRIMARY KEY, FOREIGN KEY, NOT NULL, INDEX)
- Relationships configured with proper CASCADE behavior

## Testing Recommendations

To verify the implementation:

```python
# Test database connection
from app.models import check_connection
assert check_connection() == True

# Test table creation
from app.models import create_tables
create_tables()

# Test session management
from app.models import get_db_context, Image
with get_db_context() as db:
    # Create test image
    img = Image(
        img_unique_id="test_001",
        image_height=1792,
        image_width=1792,
        processing_time_seconds=0.5,
        timestamp=datetime.now(),
        input_image_path="/test/input.jpg"
    )
    db.add(img)
    db.commit()
    
    # Verify cascade delete
    db.delete(img)
    db.commit()
```

## Git Commits
- `233cfbd` - Issue #2: Implement database engine and session setup

## Dependencies
The implementation requires the following packages (already in requirements.txt):
- sqlalchemy
- psycopg2-binary (PostgreSQL driver)
- python-dotenv (for environment variables)

## Next Steps
This stream (Stream B) is now complete. The database models are ready for:
- Stream C: Alembic migrations setup (depends on these models)
- Stream D: Integration with run.py entry point
- Future development of API endpoints that use these models

## Verification
✅ All column types match database_schema.md
✅ Foreign key relationships configured with CASCADE delete
✅ Connection pooling configured (5-20 connections)
✅ Proper SQLAlchemy relationships defined
✅ Indexes created for common query patterns
✅ Session management utilities provided
✅ No linting or type errors
✅ Code follows PEP 8 style guidelines
✅ Proper logging configured

## Acceptance Criteria Status
- [x] SQLAlchemy models implemented for Image, Class, and Region tables matching database_schema.md exactly
- [x] Foreign key relationships configured with CASCADE delete
- [x] Database connection pooling configured (min=5, max=20)
- [x] Session management utilities provided
- [x] Code follows Python best practices

Stream B is **COMPLETE** and ready for integration with other streams.
