from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, update
from awap.models.target import Target
from awap.models.finding import Finding
from awap.models.scan import Scan
from awap.api import schemas

async def get_targets(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Target).offset(skip).limit(limit))
    return result.scalars().all()

async def create_target(db: AsyncSession, target: schemas.TargetCreate):
    db_target = Target(name=target.name, base_url=target.base_url)
    db.add(db_target)
    await db.commit()
    await db.refresh(db_target)
    return db_target

async def get_target_by_url(db: AsyncSession, url: str):
    result = await db.execute(select(Target).filter(Target.base_url == url))
    return result.scalars().first()

async def delete_target(db: AsyncSession, target_id: int):
    result = await db.execute(select(Target).filter(Target.id == target_id))
    db_target = result.scalars().first()
    if db_target:
        await db.delete(db_target)
        await db.commit()
    return db_target

async def get_findings(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Finding).order_by(Finding.id.desc()).offset(skip).limit(limit))
    return result.scalars().all()

async def get_analytics_summary(db: AsyncSession):
    total_findings = await db.scalar(select(func.count(Finding.id)))
    critical = await db.scalar(select(func.count(Finding.id)).filter(Finding.severity == "CRITICAL"))
    high = await db.scalar(select(func.count(Finding.id)).filter(Finding.severity == "HIGH"))
    medium = await db.scalar(select(func.count(Finding.id)).filter(Finding.severity == "MEDIUM"))
    low = await db.scalar(select(func.count(Finding.id)).filter(Finding.severity == "LOW"))
    
    active_scans = await db.scalar(select(func.count(Scan.id)).filter(Scan.status == "RUNNING"))
    targets_count = await db.scalar(select(func.count(Target.id)))
    
    return {
        "total": total_findings or 0,
        "critical": critical or 0,
        "high": high or 0,
        "medium": medium or 0,
        "low": low or 0,
        "active_scans": active_scans or 0,
        "targets_count": targets_count or 0
    }

async def create_scan(db: AsyncSession, scan: schemas.ScanCreate):
    db_scan = Scan(target_id=scan.target_id, status="RUNNING")
    db.add(db_scan)
    await db.commit()
    await db.refresh(db_scan)
    return db_scan

async def get_scans(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Scan).offset(skip).limit(limit))
    return result.scalars().all()

async def get_scan(db: AsyncSession, scan_id: int):
    result = await db.execute(select(Scan).filter(Scan.id == scan_id))
    return result.scalars().first()

async def update_finding(db: AsyncSession, finding_id: int, finding_update: schemas.FindingUpdate):
    result = await db.execute(select(Finding).filter(Finding.id == finding_id))
    db_finding = result.scalars().first()
    if db_finding:
        db_finding.status = finding_update.status
        await db.commit()
        await db.refresh(db_finding)
    return db_finding
