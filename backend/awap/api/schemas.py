from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List

class TargetBase(BaseModel):
    name: str
    base_url: str

class TargetCreate(TargetBase):
    pass

class Target(TargetBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ScanBase(BaseModel):
    target_id: int

class ScanCreate(ScanBase):
    pass

class Scan(ScanBase):
    id: int
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    endpoints_discovered: int
    requests_sent: int
    current_phase: str

    class Config:
        from_attributes = True

class FindingBase(BaseModel):
    vuln_class: str
    severity: str
    endpoint_url: str
    method: str

class FindingUpdate(BaseModel):
    status: str

class Finding(FindingBase):
    id: int
    scan_id: int
    status: str
    discovered_at: datetime
    confidence: int
    payload: Optional[str] = None
    request_raw: Optional[str] = None
    response_raw: Optional[str] = None
    ai_summary: Optional[str] = None
    remediation: Optional[str] = None
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None

    class Config:
        from_attributes = True
