from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class Scan(Base):
    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id = Column(UUID(as_uuid=True), ForeignKey("targets.id"), nullable=False)
    state = Column(String, nullable=False, default="CREATED")
    profile = Column(String, nullable=False, default="standard")
    progress = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    target = relationship("Target", back_populates="scans")
    recon_results = relationship("ReconResult", back_populates="scan", cascade="all, delete-orphan")
    endpoints = relationship("Endpoint", back_populates="scan", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
    scan_logs = relationship("ScanLog", back_populates="scan", cascade="all, delete-orphan")
