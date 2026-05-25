from awap.engines.attack.base import AttackModule

class SecurityHeadersModule(AttackModule):
    REQUIRED_HEADERS = {
        'Strict-Transport-Security': 'MISSING HSTS',
        'X-Frame-Options': 'MISSING Clickjacking Protection',
        'X-Content-Type-Options': 'MISSING MIME sniffing protection',
        'Content-Security-Policy': 'MISSING CSP',
        'Referrer-Policy': 'MISSING Referrer control',
    }

    async def run(self, url: str, params: list[dict]) -> list[dict]:
        findings = []
        try:
            resp = await self.client.get(url)
            for header, msg in self.REQUIRED_HEADERS.items():
                if header not in resp.headers:
                    findings.append({
                        'vuln_class': 'SECURITY_HEADERS',
                        'url': url, 'param': None,
                        'payload': None, 'evidence': msg,
                        'severity': 'INFO', 'cvss': 0.0,
                        'request_raw': str(resp.request.url),
                        'response_raw': str(resp.headers)
                    })
        except Exception:
            pass
        return findings
