from abc import ABC, abstractmethod
from typing import ClassVar, List, Dict, Any, Tuple
import importlib
import pkgutil

class Parameter:
    def __init__(self, name: str, location: str, original_value: str, endpoint_id: str):
        self.name = name
        self.location = location
        self.original_value = original_value
        self.endpoint_id = endpoint_id

class Endpoint:
    def __init__(self, url: str, method: str):
        self.url = url
        self.method = method

class ParameterProfile:
    def __init__(self, param_name: str, baseline_status: int, baseline_length: int, baseline_time: int):
        self.param_name = param_name
        self.baseline_status = baseline_status
        self.baseline_length = baseline_length
        self.baseline_time = baseline_time
        self.is_reflected = False
        self.reflection_context = "unknown"
        self.likely_sql_context = False

class Finding:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

_MODULE_REGISTRY: Dict[str, type["AttackModule"]] = {}

def register_module(cls):
    """Decorator that registers an attack module class."""
    _MODULE_REGISTRY[cls.module_id] = cls
    return cls

class AttackModule(ABC):
    module_id: ClassVar[str]
    vuln_class: ClassVar[str]
    severity: ClassVar[str]
    requires_reflection: ClassVar[bool] = False
    requires_oob: ClassVar[bool] = False
    safe_to_run_in_prod: ClassVar[bool] = True

    def __init__(self, payload_engine, http_client, oob_server=None):
        self.payload_engine = payload_engine
        self.http = http_client
        self.oob = oob_server

    @abstractmethod
    async def run(self, endpoint: Endpoint, param: Parameter, profile: ParameterProfile) -> List[Finding]: 
        pass

    @abstractmethod
    async def verify(self, finding: Finding) -> bool: 
        pass

    def build_finding(self, endpoint, param, payload, request_raw, response_raw, confidence, evidence) -> Finding:
        cvss_map = {"CRITICAL": 9.8, "HIGH": 7.5, "MEDIUM": 5.0, "LOW": 3.0}
        return Finding(
            module_id=self.module_id,
            vuln_class=self.vuln_class,
            severity=self.severity,
            cvss_score=cvss_map.get(self.severity.upper(), 5.0),
            endpoint=endpoint.url,
            method=endpoint.method,
            parameter=param.name,
            parameter_location=param.location,
            payload=payload,
            request_raw=request_raw,
            response_raw=response_raw,
            confidence=confidence,
            evidence=evidence,
        )

def load_all_modules():
    pass
