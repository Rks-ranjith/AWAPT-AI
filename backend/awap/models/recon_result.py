from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class ReconResult(Base):
    __tablename__ = "recon_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    type = Column(String, nullable=False) # 'subdomain', 'port', 'technology', 'waf'
    data = Column(JSONB, nullable=False)
    source = Column(String, nullable=False)
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    scan = relationship("Scan", back_populates="recon_results")
