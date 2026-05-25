from awap.engines.attack.base import AttackModule


class OpenRedirectModule(AttackModule):
    module_id = "open_redirect"
    vuln_class = "OPEN_REDIRECT"

    REDIRECT_PAYLOADS = [
        "https://evil.example",
        "//evil.example",
        "/\\evil.example",
    ]

    async def run(self, url: str, params: list[dict], context=None) -> list[dict]:
        findings = []
        for param in params:
            for payload in self.REDIRECT_PAYLOADS:
                try:
                    resp, meta = await self.send_payload(
                        url, "GET", payload, param["name"], param["type"], context
                    )
                    if not resp:
                        continue
                    if resp.status_code in (301, 302, 307, 308):
                        loc = resp.headers.get("Location", "")
                        if "evil.example" in loc:
                            findings.append({
                                "vuln_class": "OPEN_REDIRECT",
                                "url": url,
                                "method": "GET",
                                "param": param["name"],
                                "payload": payload,
                                "evidence": f"Redirects to {loc}",
                                "severity": "MEDIUM",
                                "cvss": 6.1,
                                "request_raw": meta.get("request_raw"),
                                "response_raw": meta.get("response_raw"),
                            })
                            break
                except Exception:
                    pass
        return findings
