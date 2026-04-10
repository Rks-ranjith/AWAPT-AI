from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from .base import Base

class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    
    # Metrics
    endpoints_discovered = Column(Integer, default=0)
    requests_sent = Column(Integer, default=0)
    current_phase = Column(String, default="INITIALIZING") # RECON, CRAWLING, VULN_SCAN, REPORTING
    
    # Relationships
    target = relationship("Target", back_populates="scans")
    findings = relationship("Finding", back_populates="scan")
