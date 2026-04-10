from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from .base import Base

class TargetStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"

class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    base_url = Column(String, unique=True, index=True, nullable=False)
    status = Column(Enum(TargetStatus), default=TargetStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scans = relationship("Scan", back_populates="target")
    findings = relationship("Finding", back_populates="target")
