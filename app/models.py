from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base, get_db

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    photos = relationship("Photo", back_populates="owner")

class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Changed these to match the tutorial exactly:
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    
    upload_date = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="photos")