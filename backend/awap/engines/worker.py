"""
Celery scan worker — architecture §12.1 state machine:
CREATED → SCOPE_VERIFIED → RECON → CRAWL → MAPPING → ATTACK → ANALYSIS → REPORTING → COMPLETE
"""
import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select

from awap.api.crud import log_scan_event, update_scan_state
from awap.core.celery_app import celery_app
from awap.core.database import AsyncSessionLocal
from awap.models.scan import Scan
from awap.models.target import Target

logger = logging.getLogger(__name__)


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        from awap.core.database import engine
        try:
            loop.run_until_complete(engine.dispose())
        except Exception:
            pass


async def _publish_redis_event(scan_id: str, event: dict):
    from awap.core.config import settings
    import redis.asyncio as redis

    r = redis.from_url(settings.REDIS_URL)
    await r.publish("scan_events", json.dumps({"scan_id": scan_id, "event": event}))
    await r.aclose()


async def _set_phase(db, scan_id: str, state: str, progress: int, message: str):
    await update_scan_state(db, scan_id, state, progress=progress)
    await log_scan_event(db, scan_id, "INFO", message)
    await _publish_redis_event(
        scan_id, {"type": "STATE_CHANGE", "state": state, "progress": progress, "message": message}
    )


async def async_run_scope(scan_id: str, target_id: str):
    async with AsyncSessionLocal() as db:
        target = await db.scalar(select(Target).filter(Target.id == target_id))
        if not target:
            raise ValueError(f"Target {target_id} not found")
        if not target.authorized:
            raise ValueError("Target is not authorized for scanning")

        scan = await db.scalar(select(Scan).filter(Scan.id == scan_id))
        if scan and not scan.started_at:
            scan.started_at = datetime.utcnow()
            await db.commit()

        from awap.engines.scan_context import ScanContext

        ctx = ScanContext.from_target(
            scan_id, target_id, target.domain, scan.profile if scan else "standard", target.scope_rules or []
        )
        if not ctx.scope_enforcer.is_in_scope(ctx.base_url) and not ctx.scope_enforcer.is_in_scope(
            f"http://{target.domain}"
        ):
            raise ValueError(f"Target domain {target.domain} failed scope validation")

        await _set_phase(db, scan_id, "SCOPE_VERIFIED", 5, f"Scope verified for {target.domain}")


async def async_run_recon(scan_id: str, target_id: str):
    async with AsyncSessionLocal() as db:
        await _set_phase(db, scan_id, "RECON", 15, "Reconnaissance phase started")
        target = await db.scalar(select(Target).filter(Target.id == target_id))
        if not target:
            raise ValueError(f"Target {target_id} not found")

        from awap.engines.recon.base import enumerate_subdomains, fingerprint_target, scan_common_ports
        from awap.models.recon_result import ReconResult

        # Map localhost/127.0.0.1 to host.docker.internal for docker loopback compatibility
        mapped_domain = target.domain.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")

        for s in await enumerate_subdomains(target.domain):
            db.add(
                ReconResult(
                    scan_id=scan_id, type="subdomain", data=s, source=s.get("source", "unknown")
                )
            )
        base_url = mapped_domain if mapped_domain.startswith("http") else f"https://{mapped_domain}"
        tech = await fingerprint_target(base_url)
        db.add(ReconResult(scan_id=scan_id, type="technology", data=tech, source="fingerprint"))
        
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        ports = await scan_common_ports(parsed.hostname or mapped_domain)
        db.add(ReconResult(scan_id=scan_id, type="port", data={"open_ports": ports}, source="portscan"))
        await db.commit()
        await log_scan_event(db, scan_id, "INFO", "Reconnaissance complete")


async def async_run_crawl(scan_id: str, target_id: str):
    async with AsyncSessionLocal() as db:
        await _set_phase(db, scan_id, "CRAWL", 35, "Crawl phase started")
        target = await db.scalar(select(Target).filter(Target.id == target_id))
        from awap.core.config import settings
        from awap.engines.crawler.base import crawl_target

        base = target.domain if target.domain.startswith("http") else f"https://{target.domain}"
        mapped_base = base.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
        await crawl_target(mapped_base, scan_id, max_pages=settings.SCAN_MAX_PAGES)
        await log_scan_event(db, scan_id, "INFO", "Crawl complete")


async def async_run_mapping(scan_id: str, target_id: str):
    async with AsyncSessionLocal() as db:
        await _set_phase(db, scan_id, "MAPPING", 45, "Parameter discovery (MAPPING) started")
        from awap.engines.attack.manager import build_scan_context, run_mapping

        ctx = await build_scan_context(db, scan_id, target_id)
        count = await run_mapping(db, scan_id, ctx)
        await log_scan_event(db, scan_id, "INFO", f"Mapping complete — {count} hidden parameters discovered")


async def async_run_attack(scan_id: str, target_id: str):
    async with AsyncSessionLocal() as db:
        await _set_phase(db, scan_id, "ATTACK", 60, "Attack execution started")
        from awap.engines.attack.manager import run_attacks

        n = await run_attacks(db, scan_id, target_id)
        await log_scan_event(db, scan_id, "INFO", f"Attack phase complete — {n} findings")


async def async_run_analysis(scan_id: str, target_id: str):
    async with AsyncSessionLocal() as db:
        await _set_phase(db, scan_id, "ANALYSIS", 80, "AI analysis started")
        from awap.engines.ai.manager import run_ai_analysis

        await run_ai_analysis(db, scan_id)
        await log_scan_event(db, scan_id, "INFO", "AI analysis complete")


async def async_run_report(scan_id: str, target_id: str):
    async with AsyncSessionLocal() as db:
        await _set_phase(db, scan_id, "REPORTING", 95, "Report generation started")
        from awap.reporting.report_generator import generate_reports

        generate_reports(scan_id, target_id, template="tech")
        await update_scan_state(db, scan_id, "COMPLETE", progress=100)
        await log_scan_event(db, scan_id, "INFO", "Scan completed successfully")
        await _publish_redis_event(
            scan_id, {"type": "STATE_CHANGE", "state": "COMPLETE", "progress": 100}
        )
        try:
            from awap.core.notifier import dispatch_scan_complete_alerts
            await dispatch_scan_complete_alerts(scan_id, target_id)
        except Exception as e:
            logger.error(f"Failed to dispatch scan alerts: {e}")


async def async_log_error(scan_id: str, msg: str):
    async with AsyncSessionLocal() as db:
        await log_scan_event(db, scan_id, "ERROR", msg)
        await update_scan_state(db, scan_id, "FAILED", error_message=msg)
        await _publish_redis_event(scan_id, {"type": "STATE_CHANGE", "state": "FAILED", "message": msg})


@celery_app.task(bind=True, max_retries=3, name="awap.engines.worker.run_scope")
def run_scope_task(self, scan_id: str, target_id: str):
    try:
        run_async(async_run_scope(scan_id, target_id))
        run_recon_task.delay(scan_id, target_id)
    except Exception as exc:
        run_async(async_log_error(scan_id, f"Scope verification failed: {exc}"))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3, name="awap.engines.worker.run_recon")
def run_recon_task(self, scan_id: str, target_id: str):
    try:
        run_async(async_run_recon(scan_id, target_id))
        run_crawl_task.delay(scan_id, target_id)
    except Exception as exc:
        run_async(async_log_error(scan_id, f"Recon error: {exc}"))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3, name="awap.engines.worker.run_crawl")
def run_crawl_task(self, scan_id: str, target_id: str):
    try:
        run_async(async_run_crawl(scan_id, target_id))
        run_mapping_task.delay(scan_id, target_id)
    except Exception as exc:
        run_async(async_log_error(scan_id, f"Crawl error: {exc}"))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3, name="awap.engines.worker.run_mapping")
def run_mapping_task(self, scan_id: str, target_id: str):
    try:
        run_async(async_run_mapping(scan_id, target_id))
        run_attack_task.delay(scan_id, target_id)
    except Exception as exc:
        run_async(async_log_error(scan_id, f"Mapping error: {exc}"))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3, name="awap.engines.worker.run_attack")
def run_attack_task(self, scan_id: str, target_id: str):
    try:
        run_async(async_run_attack(scan_id, target_id))
        run_analysis_task.delay(scan_id, target_id)
    except Exception as exc:
        run_async(async_log_error(scan_id, f"Attack error: {exc}"))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3, name="awap.engines.worker.run_analysis")
def run_analysis_task(self, scan_id: str, target_id: str):
    try:
        run_async(async_run_analysis(scan_id, target_id))
        run_report_task.delay(scan_id, target_id)
    except Exception as exc:
        run_async(async_log_error(scan_id, f"Analysis error: {exc}"))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3, name="awap.engines.worker.run_report")
def run_report_task(self, scan_id: str, target_id: str):
    try:
        run_async(async_run_report(scan_id, target_id))
    except Exception as exc:
        run_async(async_log_error(scan_id, f"Reporting error: {exc}"))
        raise self.retry(exc=exc, countdown=30)
