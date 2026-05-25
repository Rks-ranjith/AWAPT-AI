import asyncio
import os

from awap.engines.attack.base import AttackModule
from awap.core.oast import oast_manager
from awap.core.config import settings


class SSRFBlindModule(AttackModule):
    module_id = "ssrf_blind"
    vuln_class = "SSRF_BLIND"

    async def run(self, url: str, params: list[dict], context=None) -> list[dict]:
        findings = []
        oast_base = settings.OAST_SERVER or os.getenv(
            "AWAP_OAST_URL", "http://localhost:8000/api/v1/oast/callback"
        )
        for param in params:
            token = oast_manager.generate_token(str(context.scan_id if context else "scan"), "ssrf_blind")
            payload = f"{oast_base.rstrip('/')}/{token}"
            try:
                resp, meta = await self.send_payload(
                    url, "GET", payload, param["name"], param["type"], context
                )
            except Exception:
                continue
            await asyncio.sleep(2)
            if oast_manager.verify_interaction(token):
                findings.append({
                    "vuln_class": "SSRF_BLIND",
                    "url": url,
                    "method": "GET",
                    "param": param["name"],
                    "parameter_type": "URL_PARAM",
                    "payload": payload,
                    "evidence": "OAST out-of-band callback received from target",
                    "severity": "HIGH",
                    "cvss": 8.5,
                    "confidence": 0.95,
                    "confirmed": True,
                    "request_raw": meta.get("request_raw") if meta else url,
                    "response_raw": meta.get("response_raw") if meta else "",
                })
        return findings
