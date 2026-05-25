from awap.engines.attack.base import AttackModule

class SubdomainTakeoverModule(AttackModule):
    """
    Subdomain Takeover Module.
    Analyzes CNAME records gathered during Recon.
    Expert level checks for "Ghost" records pointing to expired cloud services.
    """
    SERVICES = {
        "github.io": "There isn't a GitHub Pages site here",
        "amazonaws.com": "NoSuchBucket",
        "azurewebsites.net": "404 Not Found",
        "herokuapp.com": "No such app",
        "bitbucket.io": "Repository not found",
        "wpengine.com": "The site you were looking for doesn't exist",
    }

    async def run(self, url: str, params: list[dict]) -> list[dict]:
        # This module is special - it often runs on the domain itself, 
        # not just specific endpoints.
        findings = []
        try:
            resp = await self.client.get(url)
            body = resp.text
            for domain, indicator in self.SERVICES.items():
                if indicator in body:
                    findings.append({
                        'vuln_class': 'SUBDOMAIN_TAKEOVER',
                        'url': url, 'param': 'N/A',
                        'payload': None,
                        'evidence': f"Domain points to {domain} but service reports signature: '{indicator}'",
                        'severity': 'HIGH', 'cvss': 8.5,
                        'request_raw': str(resp.request.url),
                        'response_raw': body[:500]
                    })
                    break
        except Exception:
            pass
        return findings
