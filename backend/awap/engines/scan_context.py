"""Scan execution context (architecture §6.1 AttackModule context)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from awap.core.rate_limit import TargetRateLimiter
from awap.engines.crawler.scope import ScopeEnforcer
from awap.engines.response.analyzer import ResponseAnalysisEngine


@dataclass
class ScanContext:
    scan_id: str
    target_id: str
    target_domain: str
    base_url: str
    profile: str
    scope_enforcer: ScopeEnforcer
    rate_limiter: TargetRateLimiter
    response_analyzer: ResponseAnalysisEngine = field(default_factory=ResponseAnalysisEngine)
    tech_stack: dict[str, Any] = field(default_factory=dict)
    oast_base: str = ""

    @classmethod
    def from_target(cls, scan_id: str, target_id: str, domain: str, profile: str, scope_rules: list) -> "ScanContext":
        from awap.core.config import settings

        # Map localhost/127.0.0.1 to host.docker.internal for docker loopback compatibility
        mapped_domain = domain.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")

        in_scope = [domain, mapped_domain]
        out_scope: list[str] = []
        for rule in scope_rules or []:
            if isinstance(rule, dict):
                pattern = rule.get("pattern") or rule.get("domain") or ""
                if rule.get("type") == "out_of_scope":
                    out_scope.append(pattern)
                elif pattern:
                    in_scope.append(pattern)
                    mapped_pattern = pattern.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
                    in_scope.append(mapped_pattern)
            elif isinstance(rule, str):
                in_scope.append(rule)
                mapped_rule = rule.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
                in_scope.append(mapped_rule)

        enforcer = ScopeEnforcer(in_scope=list(set(in_scope)), out_of_scope=out_scope)
        rps = getattr(settings, "SCAN_RATE_LIMIT", 10.0)
        
        base_url = mapped_domain if mapped_domain.startswith("http") else f"https://{mapped_domain}"
        
        return cls(
            scan_id=str(scan_id),
            target_id=str(target_id),
            target_domain=domain,
            base_url=base_url,
            profile=profile or "standard",
            scope_enforcer=enforcer,
            rate_limiter=TargetRateLimiter(requests_per_second=float(rps)),
            oast_base=settings.OAST_SERVER or "",
        )
