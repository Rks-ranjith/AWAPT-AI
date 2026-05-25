from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class Target(Base):
    __tablename__ = "targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String, nullable=False)
    scope_rules = Column(JSONB, nullable=False, default=list)
    authorized = Column(Boolean, nullable=False, default=False)
    authorized_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    scans = relationship("Scan", back_populates="target", cascade="all, delete-orphan")
