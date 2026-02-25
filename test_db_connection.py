"""
Quick test script to diagnose PostgreSQL connection issues
"""
import sys
import traceback

print("=" * 60)
print("PostgreSQL Connection Diagnostic Tool")
print("=" * 60)

# Test 1: Check if required packages are installed
print("\n1. Checking required packages...")
try:
    import sqlalchemy
    print(f"   ✓ SQLAlchemy version: {sqlalchemy.__version__}")
except ImportError as e:
    print(f"   ✗ SQLAlchemy not installed: {e}")
    sys.exit(1)

try:
    import psycopg2
    print(f"   ✓ psycopg2 version: {psycopg2.__version__}")
except ImportError:
    try:
        import psycopg
        print(f"   ✓ psycopg version: {psycopg.__version__}")
    except ImportError as e:
        print(f"   ✗ No PostgreSQL driver installed (psycopg2 or psycopg3): {e}")
        sys.exit(1)

# Test 2: Load configuration
print("\n2. Loading configuration...")
try:
    from app.config import settings
    print(f"   ✓ Database URL: {settings.database_url}")
    print(f"   ✓ Pool size: {settings.db_pool_size}")
    print(f"   ✓ Max overflow: {settings.db_max_overflow}")
except Exception as e:
    print(f"   ✗ Failed to load config: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test raw SQLAlchemy connection
print("\n3. Testing raw SQLAlchemy engine connection...")
try:
    from sqlalchemy import create_engine
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        result = conn.execute(sqlalchemy.text("SELECT version()"))
        version = result.scalar()
        print(f"   ✓ Connected to PostgreSQL!")
        print(f"   ✓ PostgreSQL version: {version}")
except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    traceback.print_exc()
    print("\n   Common issues:")
    print("   - PostgreSQL service not running")
    print("   - Wrong username/password")
    print("   - Database 'aoi_inference_db' doesn't exist")
    print("   - PostgreSQL not accepting connections on localhost:5432")
    sys.exit(1)

# Test 4: Test database exists
print("\n4. Checking if database exists...")
try:
    from sqlalchemy import create_engine, text
    # Connect to postgres database to check if our DB exists
    base_url = settings.database_url.rsplit('/', 1)[0] + '/postgres'
    engine = create_engine(base_url)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT 1 FROM pg_database WHERE datname = 'aoi_inference_db'"
        ))
        if result.scalar():
            print("   ✓ Database 'aoi_inference_db' exists")
        else:
            print("   ✗ Database 'aoi_inference_db' does NOT exist")
            print("   Run: CREATE DATABASE aoi_inference_db;")
except Exception as e:
    print(f"   ✗ Failed to check database: {e}")

# Test 5: Test application database connection
print("\n5. Testing application database module...")
try:
    from app.models.database import check_connection
    if check_connection():
        print("   ✓ Application database connection: SUCCESS")
    else:
        print("   ✗ Application database connection: FAILED")
except Exception as e:
    print(f"   ✗ Failed to test application database: {e}")
    traceback.print_exc()

# Test 6: Test session creation
print("\n6. Testing session creation...")
try:
    from app.models.database import get_db_context
    with get_db_context() as db:
        print("   ✓ Database session created successfully")
except Exception as e:
    print(f"   ✗ Failed to create session: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnostic complete!")
print("=" * 60)
