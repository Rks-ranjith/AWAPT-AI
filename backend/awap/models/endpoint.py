from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    
    url = Column(String, index=True, nullable=False)
    method = Column(String, nullable=False)
    
    # Store parameters as JSON or summary text for simple reporting
    parameters_json = Column(String, nullable=True) 
    
    is_api = Column(Boolean, default=False)
    is_form = Column(Boolean, default=False)
    
    discovered_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    target = relationship("Target")
    scan = relationship("Scan")
