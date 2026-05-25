from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    level = Column(String, nullable=False, default="INFO")
    message = Column(String, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    logged_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    scan = relationship("Scan", back_populates="scan_logs")
