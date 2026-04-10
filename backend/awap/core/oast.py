import uuid
import time
from typing import Dict, Optional, List
from pydantic import BaseModel
from datetime import datetime

class OASTInteraction(BaseModel):
    token: str
    client_ip: str
    method: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    body: Optional[str]
    timestamp: datetime

class OASTManager:
    """
    Manages ephemeral OAST tokens and tracks external interactions.
    This is used to detect Blind SSRF, Out-of-band SQLi, etc.
    """
    def __init__(self):
        # In a real-world scenario, this would use Redis for persistence/TTL
        # For now, we'll use an in-memory registry for the MVP
        self._interactions: List[OASTInteraction] = []
        self._active_tokens: Dict[str, dict] = {}

    def generate_token(self, scan_id: int, module_id: str) -> str:
        """Generates a unique OAST token linked to a specific scan and module."""
        token = uuid.uuid4().hex[:12]
        self._active_tokens[token] = {
            "scan_id": scan_id,
            "module_id": module_id,
            "created_at": time.time()
        }
        return token

    def register_interaction(self, token: str, client_ip: str, method: str, headers: dict, params: dict, body: Optional[str] = None):
        """Records an external interaction hit on the OAST endpoint."""
        interaction = OASTInteraction(
            token=token,
            client_ip=client_ip,
            method=method,
            headers=dict(headers),
            query_params=dict(params),
            body=body,
            timestamp=datetime.utcnow()
        )
        self._interactions.append(interaction)
        return interaction

    def get_interactions(self, token: str) -> List[OASTInteraction]:
        """Retrieves all interactions for a specific token."""
        return [i for i in self._interactions if i.token == token]

    def verify_interaction(self, token: str) -> bool:
        """Checks if a token has been hit."""
        return any(i.token == token for i in self._interactions)

# Global OAST Manager Instance
oast_manager = OASTManager()
