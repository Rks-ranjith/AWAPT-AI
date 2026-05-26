import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from awap.api import crud, schemas
from awap.core.celery_app import celery_app
from awap.core.config import settings
from awap.core.database import get_db
from awap.models import Finding, Scan, Target
from awap.models.endpoint import Endpoint as EndpointModel
from awap.reporting.report_generator import (
    VALID_TEMPLATES,
    fetch_scan_report_data,
    generate_reports,
)

router = APIRouter()


@router.post("/targets", response_model=schemas.Target)
async def create_target(target: schemas.TargetCreate, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    db_target = await crud.get_target_by_domain(db, domain=target.domain)
    if db_target:
        db_target.name = target.name
        db_target.base_url = target.base_url
        db_target.authorized = target.authorized
        if target.authorized:
            db_target.authorized_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_target)
        return db_target
    return await crud.create_target(db=db, target=target)


@router.get("/targets", response_model=List[schemas.Target])
async def read_targets(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await crud.get_targets(db, skip=skip, limit=limit)


@router.delete("/targets/{target_id}")
async def delete_target(target_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Target).filter(Target.id == target_id))
    target = result.scalar()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    await db.delete(target)
    await db.commit()
    return {"status": "deleted", "target_id": str(target_id)}

@router.post("/scans", response_model=schemas.Scan)
async def create_scan(scan: schemas.ScanCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Target.authorized).where(Target.id == scan.target_id)
    )
    auth = result.scalar()
    if not auth:
        raise HTTPException(status_code=403, detail="Target not authorized for scanning")

    db_scan = await crud.create_scan(db=db, scan=scan)

    from awap.engines.worker import run_scope_task
    run_scope_task.delay(str(db_scan.id), str(scan.target_id))

    return db_scan


@router.get("/scans", response_model=List[schemas.Scan])
async def read_scans(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    return await crud.get_scans(db, skip=skip, limit=limit)


@router.get("/scans/{scan_id}", response_model=schemas.Scan)
async def read_scan(scan_id: UUID, db: AsyncSession = Depends(get_db)):
    db_scan = await crud.get_scan(db, scan_id=scan_id)
    if db_scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return db_scan


@router.get("/scans/{scan_id}/findings", response_model=List[schemas.Finding])
async def read_scan_findings(scan_id: UUID, db: AsyncSession = Depends(get_db)):
    return await crud.get_scan_findings(db, scan_id=scan_id)


@router.get("/scans/{scan_id}/endpoints", response_model=List[schemas.Endpoint])
async def read_scan_endpoints(scan_id: UUID, db: AsyncSession = Depends(get_db)):
    """Fetch all crawled endpoints for a scan — powers the live Attack Surface Graph."""
    result = await db.execute(
        select(EndpointModel)
        .filter(EndpointModel.scan_id == scan_id)
        .order_by(EndpointModel.discovered_at)
    )
    return result.scalars().all()


@router.get("/scans/{scan_id}/logs", response_model=List[schemas.ScanLog])
async def read_scan_logs(scan_id: UUID, db: AsyncSession = Depends(get_db)):
    return await crud.get_scan_logs(db, scan_id=scan_id)


@router.post("/scans/{scan_id}/pause")
async def pause_scan(scan_id: UUID, db: AsyncSession = Depends(get_db)):
    await crud.update_scan_state(db, scan_id, "PAUSED")
    return {"status": "PAUSED"}


@router.post("/scans/{scan_id}/resume")
async def resume_scan(scan_id: UUID, db: AsyncSession = Depends(get_db)):
    await crud.update_scan_state(db, scan_id, "RESUMED")
    return {"status": "RESUMED"}


@router.get("/findings", response_model=List[schemas.Finding])
async def read_all_findings(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Finding).order_by(desc(Finding.discovered_at)).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.patch("/findings/{finding_id}", response_model=schemas.Finding)
async def update_finding(finding_id: UUID, updates: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Finding).filter(Finding.id == finding_id))
    finding = result.scalar()
    if not finding:
        raise HTTPException(404, "Finding not found")
    for key, value in updates.items():
        if hasattr(finding, key):
            setattr(finding, key, value)
    await db.commit()
    await db.refresh(finding)
    return finding


@router.get("/analytics/summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(Finding.id)))
    critical = await db.scalar(
        select(func.count(Finding.id)).filter(Finding.severity == "CRITICAL")
    )
    high = await db.scalar(
        select(func.count(Finding.id)).filter(Finding.severity == "HIGH")
    )
    medium = await db.scalar(
        select(func.count(Finding.id)).filter(Finding.severity == "MEDIUM")
    )
    low = await db.scalar(
        select(func.count(Finding.id)).filter(Finding.severity == "LOW")
    )
    active_scans = await db.scalar(
        select(func.count(Scan.id)).filter(
            Scan.state.notin_(["COMPLETE", "FAILED", "ABORTED"])
        )
    )
    targets_count = await db.scalar(select(func.count(Target.id)))

    vuln_dist_query = (
        select(Finding.vuln_class, func.count(Finding.id))
        .group_by(Finding.vuln_class)
    )
    vuln_dist_res = await db.execute(vuln_dist_query)
    vuln_distribution = {row[0]: row[1] for row in vuln_dist_res.all()}

    return {
        "total": total or 0,
        "critical": critical or 0,
        "high": high or 0,
        "medium": medium or 0,
        "low": low or 0,
        "active_scans": active_scans or 0,
        "targets_count": targets_count or 0,
        "vuln_distribution": vuln_distribution,
    }


@router.get("/health", response_model=schemas.HealthCheck)
async def health_check(db: AsyncSession = Depends(get_db)):
    status = {"status": "ok", "celery": "error", "postgres": "error", "redis": "error"}
    try:
        await db.execute(select(Target.id).limit(1))
        status["postgres"] = "connected"
    except Exception:
        pass

    try:
        i = celery_app.control.inspect()
        if i.ping():
            status["celery"] = "connected"
        import redis.asyncio as redis
        r = redis.from_url(settings.REDIS_URL)
        if await r.ping():
            status["redis"] = "connected"
        await r.aclose()
    except Exception:
        pass

    if "error" in status.values():
        status["status"] = "degraded"
        return status

    return status


async def _resolve_scan_id(scan_id: str, db: AsyncSession) -> UUID:
    if scan_id == "latest":
        result = await db.execute(select(Scan).order_by(desc(Scan.started_at)))
        scan = result.scalars().first()
        if not scan:
            raise HTTPException(404, "No scans found")
        return scan.id
    try:
        return UUID(scan_id)
    except ValueError:
        raise HTTPException(400, "Invalid scan ID format")


async def _ensure_reports(scan_uuid: UUID, db: AsyncSession, template: str = "tech") -> None:
    scan = await crud.get_scan(db, scan_uuid)
    if not scan:
        raise HTTPException(404, "Scan not found")
    report_dir = os.path.join("reports", str(scan_uuid))
    legacy = f"reports/AWAP_Scan_Report_{scan_uuid}.pdf"
    tpl_pdf = os.path.join(report_dir, f"report_{template}.pdf")
    if not os.path.exists(tpl_pdf) and not os.path.exists(legacy):
        generate_reports(str(scan_uuid), str(scan.target_id), template=template)


@router.get("/reports/{scan_id}/preview")
async def report_preview(
    scan_id: str,
    template: str = Query("tech"),
    db: AsyncSession = Depends(get_db),
):
    """JSON preview for the Reports UI."""
    if template not in VALID_TEMPLATES:
        raise HTTPException(400, detail=f"Invalid template. Use one of: {', '.join(VALID_TEMPLATES)}")
    scan_uuid = await _resolve_scan_id(scan_id, db)
    scan = await crud.get_scan(db, scan_uuid)
    if not scan:
        raise HTTPException(404, "Scan not found")
    data = await fetch_scan_report_data(str(scan_uuid), str(scan.target_id))
    if not data:
        raise HTTPException(404, "Report data not available")
    return {
        "scan_id": data["scan_id"],
        "target": data["target"],
        "scan_state": data["scan_state"],
        "generated_at": data["generated_at"],
        "template": template,
        "severity_counts": data["severity_counts"],
        "finding_count": len(data["findings"]),
        "top_findings": data["findings"][:5],
    }


@router.post("/reports/{scan_id}/generate")
async def generate_report_on_demand(
    scan_id: str,
    template: str = Query("tech"),
    db: AsyncSession = Depends(get_db),
):
    if template not in VALID_TEMPLATES and template != "all":
        raise HTTPException(400, detail=f"Invalid template. Use one of: {', '.join(VALID_TEMPLATES)}, or all")
    scan_uuid = await _resolve_scan_id(scan_id, db)
    scan = await crud.get_scan(db, scan_uuid)
    if not scan:
        raise HTTPException(404, "Scan not found")
    paths = generate_reports(str(scan_uuid), str(scan.target_id), template=template)
    return {"status": "generated", "scan_id": str(scan_uuid), "template": template, "paths": paths}


@router.get("/reports/{scan_id}/json")
async def report_json(scan_id: str, db: AsyncSession = Depends(get_db)):
    scan_uuid = await _resolve_scan_id(scan_id, db)
    scan = await crud.get_scan(db, scan_uuid)
    if not scan:
        raise HTTPException(404, "Scan not found")
    data = await fetch_scan_report_data(str(scan_uuid), str(scan.target_id))
    if not data:
        raise HTTPException(404, "Report data not available")
    return data


@router.get("/reports/{scan_id}/bounty")
async def report_bounty_json(scan_id: str, db: AsyncSession = Depends(get_db)):
    scan_uuid = await _resolve_scan_id(scan_id, db)
    await _ensure_reports(scan_uuid, db, template="bounty")
    path = os.path.join("reports", str(scan_uuid), "bounty_submissions.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Bounty report not found")
    return FileResponse(
        path,
        media_type="application/json",
        filename=f"bounty_submissions_{scan_uuid}.json",
    )


@router.get("/reports/{scan_id}/markdown")
async def download_markdown_report(
    scan_id: str,
    template: str = Query("bounty"),
    db: AsyncSession = Depends(get_db),
):
    if template not in VALID_TEMPLATES:
        raise HTTPException(400, detail=f"Invalid template. Use one of: {', '.join(VALID_TEMPLATES)}")
    scan_uuid = await _resolve_scan_id(scan_id, db)
    await _ensure_reports(scan_uuid, db, template=template)
    path = os.path.join("reports", str(scan_uuid), f"report_{template}.md")
    if not os.path.exists(path):
        raise HTTPException(404, "Markdown report not found")
    return FileResponse(
        path,
        media_type="text/markdown",
        filename=f"AWAP_Report_{scan_uuid}_{template}.md",
    )


@router.get("/reports/{scan_id}/pdf")
async def download_pdf_report(
    scan_id: str,
    template: str = Query("tech"),
    db: AsyncSession = Depends(get_db),
):
    if template not in VALID_TEMPLATES:
        raise HTTPException(400, detail=f"Invalid template. Use one of: {', '.join(VALID_TEMPLATES)}")
    scan_uuid = await _resolve_scan_id(scan_id, db)
    await _ensure_reports(scan_uuid, db, template=template)
    path = os.path.join("reports", str(scan_uuid), f"report_{template}.pdf")
    legacy = f"reports/AWAP_Scan_Report_{scan_uuid}.pdf"
    if not os.path.exists(path):
        path = legacy
    if not os.path.exists(path):
        raise HTTPException(404, "Report not found")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"AWAP_Report_{scan_uuid}_{template}.pdf",
    )


@router.get("/reports/{scan_id}/csv")
async def download_csv_report(scan_id: str, db: AsyncSession = Depends(get_db)):
    scan_uuid = await _resolve_scan_id(scan_id, db)
    await _ensure_reports(scan_uuid, db)
    path = os.path.join("reports", str(scan_uuid), "findings.csv")
    legacy = f"reports/AWAP_Scan_Report_{scan_uuid}.csv"
    if not os.path.exists(path):
        path = legacy
    if not os.path.exists(path):
        raise HTTPException(404, "CSV report not found")
    return FileResponse(
        path,
        media_type="text/csv",
        filename=f"AWAP_Findings_{scan_uuid}.csv",
    )


@router.get("/findings/{finding_id}/poc")
async def get_finding_poc(finding_id: UUID, db: AsyncSession = Depends(get_db)):
    """Full PoC package for bug bounty submission (architecture §13.1 evidence)."""
    result = await db.execute(select(Finding).filter(Finding.id == finding_id))
    finding = result.scalar()
    if not finding:
        raise HTTPException(404, "Finding not found")
    from awap.core.poc_builder import build_poc_artifacts, bounty_markdown_report
    from awap.reporting.report_generator import finding_to_record

    target_domain = ""
    scan = await crud.get_scan(db, finding.scan_id)
    if scan:
        t = await db.scalar(select(Target).filter(Target.id == scan.target_id))
        target_domain = t.domain if t else ""
    record = finding_to_record(finding, target_domain)
    return {
        "finding_id": str(finding.id),
        "title": record.get("title"),
        "severity": finding.severity,
        "cvss_score": finding.cvss_score,
        "cwe_id": finding.cwe_id,
        "poc_artifacts": finding.poc_artifacts or build_poc_artifacts(record),
        "bounty_markdown": record.get("bounty_markdown") or bounty_markdown_report(record, target_domain),
        "steps_to_reproduce": finding.steps_to_reproduce,
        "impact": finding.impact,
    }


@router.get("/findings/{finding_id}/exploit")
async def download_exploit(finding_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Finding).filter(Finding.id == finding_id))
    finding = result.scalar()
    if not finding:
        raise HTTPException(404, "Finding not found")

    from awap.reporting.report_generator import poc_curl, poc_python

    record = {
        "url": finding.url,
        "param": finding.param,
        "payload": finding.payload,
    }
    exploit_content = f'''# AWAP-Ai Proof of Concept
# Vulnerability: {finding.vuln_class}
# Target: {finding.url}
# CWE: {finding.cwe_id or "N/A"}
# CVSS: {finding.cvss_score or "N/A"}

"""
{ finding.description or "Reproduce manually and verify impact before submission." }
"""

# curl PoC:
# {poc_curl(record)}

{poc_python(record)}
'''
    os.makedirs("reports", exist_ok=True)
    temp_path = f"reports/exploit_{finding_id}.py"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(exploit_content)

    return FileResponse(
        temp_path,
        media_type="text/x-python",
        filename=f"poc_{finding_id}.py",
    )


@router.get("/settings", response_model=schemas.SystemSettingsResponse)
async def read_settings(db: AsyncSession = Depends(get_db)):
    from awap.models.setting import SystemSetting
    result = await db.execute(select(SystemSetting).filter(SystemSetting.id == "default"))
    sett = result.scalar()
    if not sett:
        sett = SystemSetting(id="default")
        db.add(sett)
        await db.commit()
        await db.refresh(sett)
    return sett


@router.post("/settings", response_model=schemas.SystemSettingsResponse)
async def update_settings(updates: schemas.SystemSettingsUpdate, db: AsyncSession = Depends(get_db)):
    from awap.models.setting import SystemSetting
    result = await db.execute(select(SystemSetting).filter(SystemSetting.id == "default"))
    sett = result.scalar()
    if not sett:
        sett = SystemSetting(id="default")
        db.add(sett)
    
    sett.email_enabled = updates.email_enabled
    sett.email_alert = updates.email_alert
    sett.slack_enabled = updates.slack_enabled
    sett.slack_webhook = updates.slack_webhook
    sett.telegram_enabled = updates.telegram_enabled
    sett.telegram_token = updates.telegram_token
    sett.telegram_chat_id = updates.telegram_chat_id
    
    await db.commit()
    await db.refresh(sett)
    return sett


@router.post("/settings/test-telegram")
async def test_telegram_settings(updates: schemas.SystemSettingsUpdate):
    if not updates.telegram_token or not updates.telegram_chat_id:
        raise HTTPException(status_code=400, detail="Telegram token and chat ID are required to send a test message.")
    import httpx
    url = f"https://api.telegram.org/bot{updates.telegram_token}/sendMessage"
    payload = {
        "chat_id": updates.telegram_chat_id,
        "text": "🤖 **AWAP-Ai Telegram Integration Test**\n\nConnection verified successfully! Your bot is ready to notify you of scan completions and accept scan commands.",
        "parse_mode": "Markdown"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return {"status": "success", "message": "Test message sent successfully."}
            else:
                try:
                    err_info = response.json()
                    detail = err_info.get("description", response.text)
                except Exception:
                    detail = response.text
                raise HTTPException(status_code=400, detail=f"Telegram API Error: {detail}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to communicate with Telegram: {str(e)}")
