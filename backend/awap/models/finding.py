from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    vuln_class = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    cvss_score = Column(Float, nullable=True)
    cvss_vector = Column(String, nullable=True)
    cwe_id = Column(String, nullable=True)
    url = Column(String, nullable=False)
    method = Column(String, nullable=True, default="GET")
    param = Column(String, nullable=True)
    parameter_type = Column(String, nullable=True, default="URL_PARAM")
    payload = Column(String, nullable=True)
    evidence = Column(String, nullable=True)
    request_raw = Column(String, nullable=True)
    response_raw = Column(String, nullable=True)
    description = Column(String, nullable=True)
    remediation = Column(String, nullable=True)
    impact = Column(Text, nullable=True)
    steps_to_reproduce = Column(Text, nullable=True)
    poc_artifacts = Column(JSONB, nullable=True)
    confidence = Column(Float, default=0.8)
    false_positive = Column(Boolean, default=False)
    confirmed = Column(Boolean, default=False)
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    scan = relationship("Scan", back_populates="findings")
