from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from .base import Base

class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    
    module_id = Column(String, nullable=False)
    vuln_class = Column(String, index=True, nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    
    endpoint_url = Column(String, nullable=False)
    method = Column(String, nullable=False)
    parameter = Column(String, nullable=True)
    
    # Technical Details
    payload = Column(String, nullable=True)
    request_raw = Column(String, nullable=True)
    response_raw = Column(String, nullable=True)
    confidence = Column(Integer, default=100)
    
    # Structured evidence (e.g. matched regex, DB type)
    evidence = Column(JSON, nullable=True)
    ai_summary = Column(String, nullable=True)
    remediation = Column(String, nullable=True)
    
    cvss_score = Column(Integer, nullable=True)
    cvss_vector = Column(String, nullable=True)
    
    discovered_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="NEW") # NEW, VERIFIED, ESCALATED, RESOLVED
    
    # Relationships
    target = relationship("Target", back_populates="findings")
    scan = relationship("Scan", back_populates="findings")
