from fastapi import APIRouter, Request, Header
from awap.core.oast import oast_manager
from typing import Optional

router = APIRouter(prefix="/oast", tags=["OAST"])

@router.get("/callback/{token}")
@router.post("/callback/{token}")
@router.put("/callback/{token}")
async def oast_callback(
    token: str, 
    request: Request,
    user_agent: Optional[str] = Header(None)
):
    """
    Callback endpoint for OAST interactions.
    When a target is exploited (e.g. Blind SSRF), it hits this URL.
    """
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    headers = dict(request.headers)
    params = dict(request.query_params)
    body = await request.body()
    
    oast_manager.register_interaction(
        token=token,
        client_ip=client_ip,
        method=method,
        headers=headers,
        params=params,
        body=body.decode("utf-8", errors="ignore") if body else None
    )
    
    return {"status": "recorded", "token": token}

@router.get("/interactions/{token}")
async def get_interactions(token: str):
    return oast_manager.get_interactions(token)

@router.get("/all")
async def get_all_interactions():
    """Returns all recorded OAST interactions for global stream monitoring."""
    # OASTManager exposes the internal list for this MVP
    return oast_manager._interactions
