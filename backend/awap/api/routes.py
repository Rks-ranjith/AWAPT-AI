from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from awap.api import crud, schemas
from awap.core.database import get_db

router = APIRouter()

@router.get("/")
async def api_root():
    return {"message": "AWAP-AI API v1.1.0 is running", "docs": "/docs"}

@router.get("/targets", response_model=List[schemas.Target])
async def read_targets(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_targets(db, skip=skip, limit=limit)

@router.post("/targets", response_model=schemas.Target)
async def create_target(target: schemas.TargetCreate, db: AsyncSession = Depends(get_db)):
    db_target = await crud.get_target_by_url(db, url=target.base_url)
    if db_target:
        raise HTTPException(status_code=400, detail="Target already exists")
    return await crud.create_target(db=db, target=target)

@router.delete("/targets/{target_id}")
async def delete_target(target_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud.delete_target(db, target_id=target_id)
    if not success:
        raise HTTPException(status_code=404, detail="Target not found")
    return {"status": "success"}

@router.get("/findings", response_model=List[schemas.Finding])
async def read_findings(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_findings(db, skip=skip, limit=limit)

@router.get("/analytics/summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    return await crud.get_analytics_summary(db)

@router.post("/scans", response_model=schemas.Scan)
async def create_scan(scan: schemas.ScanCreate, db: AsyncSession = Depends(get_db)):
    db_scan = await crud.create_scan(db=db, scan=scan)
    from awap.engines.worker import execute_scan
    execute_scan.delay(db_scan.id)
    return db_scan

@router.get("/scans", response_model=List[schemas.Scan])
async def read_scans(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_scans(db, skip=skip, limit=limit)

@router.get("/scans/{scan_id}", response_model=schemas.Scan)
async def read_scan(scan_id: int, db: AsyncSession = Depends(get_db)):
    db_scan = await crud.get_scan(db, scan_id=scan_id)
    if db_scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return db_scan

@router.patch("/findings/{finding_id}", response_model=schemas.Finding)
async def update_finding(finding_id: int, finding_update: schemas.FindingUpdate, db: AsyncSession = Depends(get_db)):
    db_finding = await crud.update_finding(db, finding_id=finding_id, finding_update=finding_update)
    if db_finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return db_finding

@router.get("/scans/{scan_id}/report")
async def download_scan_report(scan_id: int, db: AsyncSession = Depends(get_db)):
    from starlette.responses import FileResponse
    from awap.core.report_generator import generate_scan_report
    from awap.models.scan import Scan
    from awap.models.target import Target
    from awap.models.finding import Finding
    from sqlalchemy import select
    
    res = await db.execute(select(Scan).filter(Scan.id == scan_id))
    scan = res.scalars().first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    res_target = await db.execute(select(Target).filter(Target.id == scan.target_id))
    target = res_target.scalars().first()
    
    res_findings = await db.execute(select(Finding).filter(Finding.scan_id == scan_id))
    findings = res_findings.scalars().all()
    
    pdf_path = generate_scan_report(db, scan, target, findings)
    
    return FileResponse(
        path=pdf_path,
        filename=f"AWAP_Scan_Report_{scan_id}.pdf",
        media_type="application/pdf"
    )

@router.get("/findings/{finding_id}/exploit")
async def generate_exploit(finding_id: int, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import PlainTextResponse
    from awap.models.finding import Finding
    from awap.models.target import Target
    from awap.core.exploit_gen import generate_exploit_script
    from sqlalchemy import select
    
    res = await db.execute(select(Finding).filter(Finding.id == finding_id))
    finding = res.scalars().first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
        
    res_target = await db.execute(select(Target).filter(Target.id == finding.target_id))
    target = res_target.scalars().first()
    script = generate_exploit_script(finding, target)
    
    return PlainTextResponse(
        content=script,
        media_type="text/x-python",
        headers={"Content-Disposition": f"attachment; filename=exploit_{finding.vuln_class.lower()}_{finding_id}.py"}
    )
