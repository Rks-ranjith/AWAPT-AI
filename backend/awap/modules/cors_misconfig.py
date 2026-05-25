from awap.engines.attack.base import AttackModule

class CORSModule(AttackModule):
    async def run(self, url: str, params: list[dict]) -> list[dict]:
        findings = []
        try:
            headers = {"Origin": "https://evil.com"}
            resp = await self.client.get(url, headers=headers)
            
            allow_origin = resp.headers.get("Access-Control-Allow-Origin", "")
            allow_creds = resp.headers.get("Access-Control-Allow-Credentials", "")
            
            if allow_origin == "https://evil.com" and allow_creds == "true":
                findings.append({
                    'vuln_class': 'CORS_MISCONFIG',
                    'url': url, 'param': None,
                    'payload': "Origin: https://evil.com", 'evidence': "Reflected origin with credentials allowed",
                    'severity': 'CRITICAL', 'cvss': 9.0,
                    'request_raw': str(resp.request.headers),
                    'response_raw': str(resp.headers)
                })
        except Exception:
            pass
        return findings
