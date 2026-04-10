from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from awap.core.database import get_db
from awap.models.target import Target
from awap.models.scan import Scan
from awap.engines.worker import execute_scan
from typing import Optional
import secrets

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Simple API Key validation for MVP
# In production, these would be stored in the DB
VALID_API_KEYS = ["AWAP_DEMO_CI_CD_KEY_2026"]

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

@router.post("/trigger-scan")
async def trigger_cicd_scan(
    target_url: str,
    project_name: str = "CI-CD-Automation",
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Triggers an autonomous scan via a CI/CD webhook call.
    Automatically indexes the target if it doesn't exist.
    """
    # Check if target exists
    target = db.query(Target).filter(Target.base_url == target_url).first()
    if not target:
        target = Target(base_url=target_url, name=project_name)
        db.add(target)
        db.commit()
        db.refresh(target)
        
    # Create Scan
    new_scan = Scan(target_id=target.id, status="PENDING")
    db.add(new_scan)
    db.commit()
    db.refresh(new_scan)
    
    # Dispatch to Celery
    execute_scan.delay(new_scan.id)
    
    return {
        "status": "scan_dispatched",
        "scan_id": new_scan.id,
        "target_id": target.id,
        "mode": "CI/CD Pipeline"
    }
