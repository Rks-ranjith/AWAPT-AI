from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(String, nullable=False)
    method = Column(String, nullable=False, default="GET")
    params = Column(JSONB, nullable=False, default=list)
    source = Column(String, nullable=False) # 'crawler', 'js_analysis', 'manual'
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    scan = relationship("Scan", back_populates="endpoints")
