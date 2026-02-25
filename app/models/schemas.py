"""
SQLAlchemy ORM models for AOI Segformer inference results
Defines Image, Class, and Region tables with relationships
"""

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Index, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.models.database import Base


class Image(Base):
    """
    Images table - stores basic information about each inference image
    """
    __tablename__ = "images"
    
    # Primary key
    img_unique_id = Column(String(255), primary_key=True, index=True)
    
    # Image dimensions
    image_height = Column(Integer, nullable=False)
    image_width = Column(Integer, nullable=False)
    
    # Processing information
    processing_time_seconds = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # File paths
    input_image_path = Column(String(500), nullable=False)
    result_image_1_path = Column(String(500), nullable=True)
    result_image_2_path = Column(String(500), nullable=True)
    result_image_3_path = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    
    # Relationships
    classes = relationship(
        "Class",
        back_populates="image",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    regions = relationship(
        "Region",
        back_populates="image",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    def __repr__(self):
        return f"<Image(img_unique_id='{self.img_unique_id}', timestamp='{self.timestamp}')>"


class Class(Base):
    """
    Classes table - stores classification information for each image
    """
    __tablename__ = "classes"
    
    # Primary key
    class_unique_id = Column(String(255), primary_key=True, index=True)
    
    # Foreign key to images table with CASCADE delete
    img_unique_id = Column(
        String(255),
        ForeignKey("images.img_unique_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Class information
    class_id = Column(Integer, nullable=False, index=True)  # 1-4
    class_name = Column(String(100), nullable=False)
    
    # Statistics
    total_regions = Column(Integer, nullable=False)
    total_area_pixels = Column(Integer, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    
    # Relationships
    image = relationship("Image", back_populates="classes")
    regions = relationship(
        "Region",
        back_populates="class_obj",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    def __repr__(self):
        return f"<Class(class_unique_id='{self.class_unique_id}', class_name='{self.class_name}', total_regions={self.total_regions})>"


class Region(Base):
    """
    Regions table - stores detailed information about each detected region
    """
    __tablename__ = "regions"
    
    # Primary key
    region_unique_id = Column(String(255), primary_key=True, index=True)
    
    # Foreign keys with CASCADE delete
    class_unique_id = Column(
        String(255),
        ForeignKey("classes.class_unique_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    img_unique_id = Column(
        String(255),
        ForeignKey("images.img_unique_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Region identification
    region_id = Column(Integer, nullable=False, index=True)
    
    # Centroid coordinates
    centroid_x = Column(Float, nullable=False)
    centroid_y = Column(Float, nullable=False)
    
    # Bounding box coordinates
    bbox_x = Column(Integer, nullable=False)
    bbox_y = Column(Integer, nullable=False)
    bbox_width = Column(Integer, nullable=False)
    bbox_height = Column(Integer, nullable=False)
    
    # Geometric properties
    area_pixels = Column(Integer, nullable=False)
    perimeter = Column(Float, nullable=False)
    major_axis = Column(Float, nullable=False)
    minor_axis = Column(Float, nullable=False)
    
    # Shape metrics
    circularity = Column(Float, nullable=False)  # 0-1
    aspect_ratio = Column(Float, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    
    # Relationships
    class_obj = relationship("Class", back_populates="regions")
    image = relationship("Image", back_populates="regions")
    
    def __repr__(self):
        return f"<Region(region_unique_id='{self.region_unique_id}', region_id={self.region_id}, area={self.area_pixels})>"


# Create composite indexes for common query patterns
Index('idx_classes_img_class', Class.img_unique_id, Class.class_id)
Index('idx_regions_img_class', Region.img_unique_id, Region.class_unique_id)
Index('idx_regions_class_region', Region.class_unique_id, Region.region_id)


# Class name enumeration for reference
CLASS_NAMES = {
    1: "PI_Particle",
    2: "PR_Peeling",
    3: "Copper_Nodule",
    4: "Env_Particle"
}
