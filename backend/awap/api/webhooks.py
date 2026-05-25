from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from awap.core.database import get_db
from awap.core.config import settings
from awap.models.target import Target
from awap.models.scan import Scan
from awap.engines.worker import run_scope_task
from typing import Optional

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    keys = settings.webhook_key_list
    if not keys:
        raise HTTPException(
            status_code=503,
            detail="Webhook API keys not configured. Set WEBHOOK_API_KEYS in environment.",
        )
    if not x_api_key or x_api_key not in keys:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key


@router.post("/trigger-scan")
async def trigger_cicd_scan(
    target_url: str,
    project_name: str = "CI-CD-Automation",
    authorized: bool = False,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    Triggers an autonomous scan via a CI/CD webhook call.
    Target must already exist with authorized=True unless authorized=true is passed explicitly.
    """
    result = await db.execute(select(Target).filter(Target.domain == target_url))
    target = result.scalar()
    if not target:
        if not authorized:
            raise HTTPException(
                status_code=403,
                detail="Target not found. Create and authorize the target in AWAPT-AI first, "
                "or pass authorized=true only for pre-approved automation scopes.",
            )
        target = Target(domain=target_url, authorized=True)
        db.add(target)
        await db.commit()
        await db.refresh(target)
    elif not target.authorized:
        raise HTTPException(status_code=403, detail="Target exists but is not authorized for scanning")

    new_scan = Scan(target_id=target.id, state="CREATED")
    db.add(new_scan)
    await db.commit()
    await db.refresh(new_scan)

    run_scope_task.delay(str(new_scan.id), str(target.id))

    return {
        "status": "scan_dispatched",
        "scan_id": new_scan.id,
        "target_id": target.id,
        "mode": "CI/CD Pipeline",
    }
