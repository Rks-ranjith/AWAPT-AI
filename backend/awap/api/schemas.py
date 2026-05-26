from pydantic import BaseModel, HttpUrl, validator, root_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

class TargetBase(BaseModel):
    domain: Optional[str] = None
    scope_rules: List[Dict[str, Any]] = []
    authorized: bool = False
    name: Optional[str] = None
    base_url: Optional[str] = None

    @root_validator(pre=True)
    def resolve_fields(cls, values):
        if not isinstance(values, dict):
            domain = getattr(values, 'domain', None)
            base_url = getattr(values, 'base_url', None) or domain
            name = getattr(values, 'name', None) or domain
            return {
                'domain': domain,
                'scope_rules': getattr(values, 'scope_rules', []),
                'authorized': getattr(values, 'authorized', False),
                'name': name,
                'base_url': base_url,
                'id': getattr(values, 'id', None),
                'authorized_at': getattr(values, 'authorized_at', None),
                'created_at': getattr(values, 'created_at', None),
            }

        domain = values.get('domain')
        base_url = values.get('base_url')
        name = values.get('name')
        
        if not domain:
            if base_url:
                domain = base_url
            elif name:
                domain = name
        
        if not base_url and domain:
            base_url = domain
        if not name and domain:
            name = domain
            
        values['domain'] = domain
        values['base_url'] = base_url
        values['name'] = name
        return values

class TargetCreate(TargetBase):
    pass

class Target(TargetBase):
    id: UUID
    authorized_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ScanBase(BaseModel):
    target_id: UUID
    profile: str = "standard"

class ScanCreate(ScanBase):
    pass

class Scan(ScanBase):
    id: UUID
    state: str
    progress: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class FindingBase(BaseModel):
    vuln_class: str
    severity: str
    url: str

class Finding(FindingBase):
    id: UUID
    scan_id: UUID
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    cwe_id: Optional[str] = None
    method: Optional[str] = "GET"
    param: Optional[str] = None
    parameter_type: Optional[str] = None
    payload: Optional[str] = None
    evidence: Optional[str] = None
    request_raw: Optional[str] = None
    response_raw: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    impact: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    poc_artifacts: Optional[Dict[str, Any]] = None
    confidence: float
    false_positive: bool
    confirmed: bool
    discovered_at: datetime

    class Config:
        from_attributes = True

class ScanLog(BaseModel):
    id: UUID
    scan_id: UUID
    level: str
    message: str
    metadata_: Optional[Dict[str, Any]] = None
    logged_at: datetime

    class Config:
        from_attributes = True

class EndpointBase(BaseModel):
    url: str
    method: str = "GET"
    source: str
    params: List[Any] = []

class EndpointCreate(EndpointBase):
    pass

class Endpoint(EndpointBase):
    id: UUID
    scan_id: UUID
    discovered_at: datetime

    class Config:
        from_attributes = True

class HealthCheck(BaseModel):
    status: str
    celery: str
    postgres: str
    redis: str

class SystemSettingsBase(BaseModel):
    email_enabled: bool = False
    email_alert: Optional[str] = None
    slack_enabled: bool = False
    slack_webhook: Optional[str] = None
    telegram_enabled: bool = False
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

class SystemSettingsUpdate(SystemSettingsBase):
    pass

class SystemSettingsResponse(SystemSettingsBase):
    id: str

    class Config:
        from_attributes = True
