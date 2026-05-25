import httpx
from awap.engines.attack.base import AttackModule

class GraphQLIntrospectionModule(AttackModule):
    
    PAYLOAD = "query IntrospectionQuery { __schema { types { name } } }"
    
    async def run(self, url: str, params: list[dict]) -> list[dict]:
        findings = []
        # We target the root URL stripped to /graphql or similar common routes
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        gql_endpoints = [
            f"{base}/graphql",
            f"{base}/api/graphql",
            f"{base}/v1/graphql"
        ]
        
        for ep in gql_endpoints:
            try:
                resp = await self.client.post(ep, json={"query": self.PAYLOAD})
                if resp.status_code == 200 and "__schema" in resp.text and "types" in resp.text:
                    findings.append({
                        'vuln_class': 'GRAPHQL_INTROSPECTION',
                        'url': ep, 'param': 'body',
                        'payload': self.PAYLOAD,
                        'evidence': "Full GraphQL Schema Introspection Allowed",
                        'severity': 'MEDIUM', 'cvss': 5.3,
                        'request_raw': ep,
                        'response_raw': resp.text[:500]
                    })
                    # If found, break early as other endpoints are unlikely
                    break
            except Exception:
                pass
        return findings
