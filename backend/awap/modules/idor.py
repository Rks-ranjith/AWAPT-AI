import re
from awap.engines.attack.base import AttackModule

class IDORModule(AttackModule):
    """
    Insecure Direct Object Reference (IDOR) / BOLA Module.
    Identifies numeric or UUID patterns in URLs and attempts to increment/mutate them.
    In 2027, this is the #1 vulnerability in API-driven architectures.
    """
    async def run(self, url: str, params: list[dict]) -> list[dict]:
        findings = []
        # Pattern to match IDs in URL segments
        # e.g., /api/v1/users/123 -> matches 123
        id_pattern = re.compile(r'/([0-9a-fA-F-]{8,36}|[0-9]{1,10})(/|$)')
        match = id_pattern.search(url)
        
        if match:
            original_id = match.group(1)
            mutations = []
            
            if original_id.isdigit():
                val = int(original_id)
                mutations = [str(val + 1), str(val - 1), "0", "1"]
            else:
                # UUID mutation - bit flipping or simple variations
                # For an automated tool, we might just try a common "test" UUID or 000...
                mutations = ["00000000-0000-0000-0000-000000000000", "11111111-1111-1111-1111-111111111111"]
            
            # Baseline request to establish original response
            try:
                baseline = await self.client.get(url)
                baseline_len = len(baseline.content)
                baseline_status = baseline.status_code
            except Exception:
                return []

            for mutation in mutations:
                test_url = url.replace(original_id, mutation)
                try:
                    resp = await self.client.get(test_url)
                    # Heuristic: If status is same but content is significantly different, or if status is 200
                    # when it should be 403 (requires auth context which we don't fully have, but we assume unauthorized access)
                    if resp.status_code == 200 and abs(len(resp.content) - baseline_len) > 20:
                        findings.append({
                            'vuln_class': 'IDOR',
                            'url': test_url, 'param': 'Path Segment',
                            'payload': mutation,
                            'evidence': f"Resource accessed with mutated ID. Status 200. Differs from baseline length by {abs(len(resp.content)-baseline_len)} bytes.",
                            'severity': 'HIGH', 'cvss': 8.8,
                            'request_raw': test_url,
                            'response_raw': resp.text[:500]
                        })
                        break # One mutation sufficient for proof
                except Exception:
                    pass
        return findings
