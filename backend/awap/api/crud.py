from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, update, desc
from awap.models.target import Target
from awap.models.finding import Finding
from awap.models.scan import Scan
from awap.models.scan_log import ScanLog
from awap.api import schemas
from datetime import datetime
import uuid

async def get_targets(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Target).offset(skip).limit(limit))
    return result.scalars().all()

async def create_target(db: AsyncSession, target: schemas.TargetCreate):
    db_target = Target(
        domain=target.domain,
        scope_rules=target.scope_rules,
        authorized=target.authorized
    )
    if getattr(target, 'authorized', False):
        db_target.authorized_at = datetime.utcnow()
    db.add(db_target)
    await db.commit()
    await db.refresh(db_target)
    return db_target

async def get_target_by_domain(db: AsyncSession, domain: str):
    result = await db.execute(select(Target).filter(Target.domain == domain))
    return result.scalars().first()

async def create_scan(db: AsyncSession, scan: schemas.ScanCreate):
    db_scan = Scan(
        target_id=scan.target_id,
        state="CREATED",
        profile=scan.profile,
        progress=0
    )
    db.add(db_scan)
    await db.commit()
    await db.refresh(db_scan)
    return db_scan

async def get_scan(db: AsyncSession, scan_id: uuid.UUID):
    result = await db.execute(select(Scan).filter(Scan.id == scan_id))
    return result.scalars().first()

async def get_scans(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Scan).order_by(desc(Scan.created_at)).offset(skip).limit(limit))
    return result.scalars().all()

async def get_scan_findings(db: AsyncSession, scan_id: uuid.UUID):
    result = await db.execute(select(Finding).filter(Finding.scan_id == scan_id).order_by(desc(Finding.cvss_score)))
    return result.scalars().all()

async def get_scan_logs(db: AsyncSession, scan_id: uuid.UUID):
    result = await db.execute(select(ScanLog).filter(ScanLog.scan_id == scan_id).order_by(ScanLog.logged_at))
    return result.scalars().all()

async def update_scan_state(db: AsyncSession, scan_id: uuid.UUID, state: str, progress: int = None, error_message: str = None):
    scan = await get_scan(db, scan_id)
    if scan:
        scan.state = state
        if progress is not None:
            scan.progress = progress
        if error_message is not None:
            scan.error_message = error_message
        if state == "COMPLETE" or state == "FAILED" or state == "ABORTED":
            scan.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(scan)
    return scan

async def log_scan_event(db: AsyncSession, scan_id: uuid.UUID, level: str, message: str, metadata: dict = None):
    log = ScanLog(scan_id=scan_id, level=level, message=message, metadata_=metadata)
    db.add(log)
    await db.commit()
    return log
