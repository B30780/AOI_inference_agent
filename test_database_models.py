"""
Test script to verify database models implementation
Run this after setting up the database to ensure everything works
"""

import sys
from pathlib import Path
from datetime import datetime
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.models import (
    check_connection,
    create_tables,
    get_db_context,
    Image,
    Class,
    Region,
    CLASS_NAMES
)


def test_connection():
    """Test database connection"""
    print("Testing database connection...")
    if check_connection():
        print("✅ Database connection successful")
        return True
    else:
        print("❌ Database connection failed")
        return False


def test_table_creation():
    """Test creating database tables"""
    print("\nCreating database tables...")
    try:
        create_tables()
        print("✅ Tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False


def test_crud_operations():
    """Test Create, Read, Update, Delete operations"""
    print("\nTesting CRUD operations...")
    
    try:
        with get_db_context() as db:
            # Create test image
            img_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            test_image = Image(
                img_unique_id=img_id,
                image_height=1792,
                image_width=1792,
                processing_time_seconds=0.6743,
                timestamp=datetime.now(),
                input_image_path="/test/input.jpg",
                result_image_1_path="/test/result1.jpg",
                result_image_2_path="/test/result2.jpg",
                result_image_3_path="/test/result3.jpg"
            )
            db.add(test_image)
            db.commit()
            print(f"✅ Created test image: {img_id}")
            
            # Create test class
            class_id = str(uuid.uuid4())
            test_class = Class(
                class_unique_id=class_id,
                img_unique_id=img_id,
                class_id=1,
                class_name=CLASS_NAMES[1],
                total_regions=2,
                total_area_pixels=150
            )
            db.add(test_class)
            db.commit()
            print(f"✅ Created test class: {class_id}")
            
            # Create test regions
            for i in range(2):
                region_id = str(uuid.uuid4())
                test_region = Region(
                    region_unique_id=region_id,
                    class_unique_id=class_id,
                    img_unique_id=img_id,
                    region_id=i + 1,
                    centroid_x=100.5 + i * 10,
                    centroid_y=200.5 + i * 10,
                    bbox_x=100 + i * 10,
                    bbox_y=200 + i * 10,
                    bbox_width=50,
                    bbox_height=30,
                    area_pixels=75,
                    perimeter=160.0,
                    major_axis=50.0,
                    minor_axis=30.0,
                    circularity=0.75,
                    aspect_ratio=1.67
                )
                db.add(test_region)
            db.commit()
            print(f"✅ Created 2 test regions")
            
            # Read operations
            image = db.query(Image).filter_by(img_unique_id=img_id).first()
            assert image is not None
            assert len(image.classes) == 1
            assert len(image.regions) == 2
            print(f"✅ Read operations successful - Image has {len(image.classes)} class and {len(image.regions)} regions")
            
            # Test CASCADE delete
            db.delete(image)
            db.commit()
            
            # Verify cascade deletion
            remaining_classes = db.query(Class).filter_by(img_unique_id=img_id).count()
            remaining_regions = db.query(Region).filter_by(img_unique_id=img_id).count()
            
            assert remaining_classes == 0
            assert remaining_regions == 0
            print(f"✅ CASCADE delete successful - All related records deleted")
            
            return True
            
    except Exception as e:
        print(f"❌ CRUD operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_relationships():
    """Test SQLAlchemy relationships"""
    print("\nTesting relationships...")
    
    try:
        with get_db_context() as db:
            # Create test data
            img_id = f"test_rel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            image = Image(
                img_unique_id=img_id,
                image_height=1792,
                image_width=1792,
                processing_time_seconds=0.5,
                timestamp=datetime.now(),
                input_image_path="/test/input.jpg"
            )
            db.add(image)
            db.flush()
            
            class_id = str(uuid.uuid4())
            class_obj = Class(
                class_unique_id=class_id,
                img_unique_id=img_id,
                class_id=2,
                class_name=CLASS_NAMES[2],
                total_regions=1,
                total_area_pixels=100
            )
            db.add(class_obj)
            db.flush()
            
            region_id = str(uuid.uuid4())
            region = Region(
                region_unique_id=region_id,
                class_unique_id=class_id,
                img_unique_id=img_id,
                region_id=1,
                centroid_x=100.0,
                centroid_y=200.0,
                bbox_x=100,
                bbox_y=200,
                bbox_width=50,
                bbox_height=50,
                area_pixels=100,
                perimeter=200.0,
                major_axis=50.0,
                minor_axis=50.0,
                circularity=0.8,
                aspect_ratio=1.0
            )
            db.add(region)
            db.commit()
            
            # Test relationships
            assert image.classes[0].class_name == CLASS_NAMES[2]
            assert image.regions[0].region_id == 1
            assert class_obj.image.img_unique_id == img_id
            assert region.class_obj.class_name == CLASS_NAMES[2]
            assert region.image.img_unique_id == img_id
            
            print("✅ All relationships working correctly")
            
            # Cleanup
            db.delete(image)
            db.commit()
            
            return True
            
    except Exception as e:
        print(f"❌ Relationship test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Database Models Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Connection
    results.append(("Connection", test_connection()))
    
    if results[-1][1]:
        # Test 2: Table Creation
        results.append(("Table Creation", test_table_creation()))
        
        # Test 3: CRUD Operations
        results.append(("CRUD Operations", test_crud_operations()))
        
        # Test 4: Relationships
        results.append(("Relationships", test_relationships()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
