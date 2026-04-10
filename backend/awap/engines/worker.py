import logging
import asyncio
from awap.core.celery_app import celery_app
from awap.engines.manager import ScanManager

logger = logging.getLogger(__name__)

# Run the async scan manager inside the synchronous celery task
def _run_scan_sync(scan_id: int):
    loop = asyncio.get_event_loop()
    manager = ScanManager(scan_id=scan_id)
    loop.run_until_complete(manager.run_scan())

@celery_app.task(bind=True, name="awap.engines.worker.execute_scan", acks_late=True)
def execute_scan(self, scan_id: int):
    logger.info(f"[{self.request.id}] Starting Celery execution for Scan {scan_id}")
    try:
        _run_scan_sync(scan_id)
        return {"status": "SUCCESS", "scan_id": scan_id}
    except Exception as e:
        logger.error(f"[{self.request.id}] Scan {scan_id} failed: {str(e)}")
        return {"status": "FAILED", "scan_id": scan_id, "error": str(e)}
