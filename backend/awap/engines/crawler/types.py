from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional

@dataclass
class NetworkRequest:
    url: str
    method: str
    headers: Dict[str, str]
    post_data: Optional[str]
    resource_type: str

@dataclass
class FormInput:
    name: Optional[str]
    type: str
    value: str
    required: bool
    pattern: Optional[str]
    maxlength: Optional[int]

@dataclass
class FormDefinition:
    action: str
    method: str
    enctype: str
    inputs: List[Dict]
    hasFileUpload: bool

@dataclass
class CrawlerConfig:
    max_depth: int = 5
    max_urls_per_path: int = 3
    timeout_ms: int = 30000

@dataclass
class CrawlResult:
    links: List[str] = field(default_factory=list)
    forms: List[FormDefinition] = field(default_factory=list)
    api_calls: List[str] = field(default_factory=list)
    network_requests: List[NetworkRequest] = field(default_factory=list)
    base_url: str = ""
