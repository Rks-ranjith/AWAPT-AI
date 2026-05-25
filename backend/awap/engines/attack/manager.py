import asyncio
import hashlib
import inspect
import importlib
import pkgutil
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from awap.core.poc_builder import build_poc_artifacts, _default_impact
from awap.engines.attack.base import AttackModule
from awap.engines.scan_context import ScanContext
from awap.models.endpoint import Endpoint
from awap.models.finding import Finding
from awap.models.target import Target

logger = logging.getLogger(__name__)

COMMON_FUZZ_PARAMS = [
    "id", "q", "search", "query", "page", "url", "redirect", "file",
    "path", "name", "email", "user", "token", "next", "return", "dest",
]


async def build_scan_context(db: AsyncSession, scan_id: str, target_id: str) -> ScanContext:
    from awap.models.scan import Scan

    target = await db.scalar(select(Target).filter(Target.id == target_id))
    scan = await db.scalar(select(Scan).filter(Scan.id == scan_id))
    if not target:
        raise ValueError(f"Target {target_id} not found")
    return ScanContext.from_target(
        scan_id=scan_id,
        target_id=target_id,
        domain=target.domain,
        profile=scan.profile if scan else "standard",
        scope_rules=target.scope_rules or [],
    )


async def run_mapping(db: AsyncSession, scan_id: str, context: ScanContext) -> int:
    """Architecture phase: MAPPING — hidden parameter discovery."""
    from awap.engines.crawler.fuzzer import ParameterFuzzer
    from awap.models.endpoint import Endpoint

    endpoints = await db.execute(select(Endpoint).filter(Endpoint.scan_id == scan_id).limit(5))
    endpoints = endpoints.scalars().all()
    discovered = 0

    for ep in endpoints:
        if not context.scope_enforcer.is_in_scope(ep.url):
            continue
        fuzzer = ParameterFuzzer(ep.url)
        try:
            hidden = await fuzzer.run(method=ep.method or "GET")
            if hidden:
                merged = list(set((ep.params or []) + hidden))
                ep.params = merged
                discovered += len(hidden)
        except Exception as e:
            logger.warning("Parameter fuzzer failed on %s: %s", ep.url, e)
        finally:
            await fuzzer.close()

    await db.commit()
    return discovered


async def run_attacks(db: AsyncSession, scan_id: str, target_id: str) -> int:
    context = await build_scan_context(db, scan_id, target_id)

    endpoints = await db.execute(select(Endpoint).filter(Endpoint.scan_id == scan_id))
    endpoints = endpoints.scalars().all()

    import awap.modules

    modules: list[AttackModule] = []
    for _, module_name, _ in pkgutil.iter_modules(awap.modules.__path__):
        imported = importlib.import_module(f"awap.modules.{module_name}")
        for _, obj in inspect.getmembers(imported, inspect.isclass):
            if issubclass(obj, AttackModule) and obj is not AttackModule:
                try:
                    modules.append(obj())
                except Exception:
                    pass

    from awap.core.config import settings

    sem = asyncio.Semaphore(settings.MAX_CONCURRENT_CONNECTIONS)

    active_findings: list[dict] = []
    seen: set[str] = set()

    async def run_module_on_endpoint(module: AttackModule, ep: Endpoint):
        async with sem:
            if not context.scope_enforcer.is_in_scope(ep.url):
                return []
            param_names = list(ep.params) if ep.params else list(COMMON_FUZZ_PARAMS)
            params_info = [
                {
                    "name": p,
                    "type": "url_param" if (ep.method or "GET").upper() == "GET" else "body",
                }
                for p in param_names
            ]
            try:
                # Enforce 15-second per-module timeout — prevents any stalling
                # exploit attempt from hanging the entire Celery attack pipeline.
                try:
                    return await asyncio.wait_for(
                        module.run(ep.url, params_info, context=context),
                        timeout=15.0,
                    )
                except TypeError:
                    return await asyncio.wait_for(
                        module.run(ep.url, params_info),
                        timeout=15.0,
                    )
            except asyncio.TimeoutError:
                logger.warning(
                    "[ATTACK] Module %s timed out (>15s) on %s — skipping.",
                    getattr(module, "module_id", type(module).__name__),
                    ep.url,
                )
                return []
            except Exception as e:
                logger.debug("Module %s on %s: %s", module, ep.url, e)
                return []

    tasks = [run_module_on_endpoint(mod, ep) for ep in endpoints for mod in modules]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if not isinstance(res, list):
            continue
        for f in res:
            key = hashlib.sha256(
                f"{f.get('vuln_class')}:{f.get('url')}:{f.get('param')}:{f.get('payload')}".encode()
            ).hexdigest()
            if key in seen:
                continue
            seen.add(key)

            method = f.get("method") or "GET"
            param_type = f.get("parameter_type") or (
                "URL_PARAM" if method == "GET" else "BODY"
            )
            f["method"] = method
            f["parameter_type"] = param_type
            artifacts = build_poc_artifacts(f)
            f["poc_artifacts"] = artifacts
            f["request_raw"] = artifacts.get("request_raw") or f.get("request_raw")
            f["response_raw"] = artifacts.get("response_raw") or f.get("response_raw")
            f["steps_to_reproduce"] = artifacts.get("steps_to_reproduce")
            f["impact"] = f.get("impact") or _default_impact(f.get("vuln_class", ""))
            active_findings.append(f)

    for f in active_findings:
        rae_conf = f.get("confidence", 0.8)
        finding = Finding(
            scan_id=scan_id,
            vuln_class=f["vuln_class"],
            severity=f.get("severity", "MEDIUM"),
            cvss_score=f.get("cvss") or f.get("cvss_score"),
            url=f["url"],
            method=f.get("method", "GET"),
            param=f.get("param"),
            parameter_type=f.get("parameter_type", "URL_PARAM"),
            payload=f.get("payload"),
            evidence=f.get("evidence"),
            request_raw=f.get("request_raw"),
            response_raw=f.get("response_raw"),
            description=f.get("description"),
            remediation=f.get("remediation"),
            impact=f.get("impact"),
            steps_to_reproduce=f.get("steps_to_reproduce"),
            poc_artifacts=f.get("poc_artifacts"),
            confidence=float(rae_conf) if rae_conf else 0.75,
            confirmed=bool(f.get("confirmed", f.get("confidence", 0) >= 0.7)),
        )
        db.add(finding)

    await db.commit()

    import json
    import redis.asyncio as redis
    from awap.core.config import settings

    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    for f in active_findings:
        try:
            await r.publish(
                "scan_events",
                json.dumps({"scan_id": str(scan_id), "event": {"type": "FINDING", "data": f}}),
            )
        except Exception:
            pass
    await r.aclose()

    for mod in modules:
        try:
            await mod.close()
        except Exception:
            pass
    return len(active_findings)
