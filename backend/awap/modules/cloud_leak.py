from awap.engines.attack.base import AttackModule

class CloudLeakModule(AttackModule):
    """
    Scans for leaked S3 buckets, Azure Blobs, and Google Cloud Storage identifiers
    leaked in the response body (common in JS assets).
    """
    PATTERNS = [
        r'[a-z0-9.-]+\.s3\.amazonaws\.com',
        r's3://[a-z0-9.-]+',
        r'[a-z0-9.-]+\.blob\.core\.windows\.net',
        r'storage\.googleapis\.com/[a-z0-9.-]+',
        r'127\.0\.0\.1:9999/s3/[a-z0-9.-]+' # Local verification pattern
    ]

    async def run(self, url: str, params: list[dict]) -> list[dict]:
        findings = []
        try:
            resp = await self.client.get(url)
            body = resp.text
            import re
            for pattern in self.PATTERNS:
                matches = re.findall(pattern, body)
                for match in matches:
                    # Test if the bucket is public
                    if match.startswith("http"):
                        bucket_url = match
                    elif "127.0.0.1" in match:
                        bucket_url = f"http://{match}"
                    else:
                        bucket_url = f"https://{match}"
                        
                    try:
                        b_resp = await self.client.get(bucket_url)
                        if b_resp.status_code == 200:
                            findings.append({
                                'vuln_class': 'CLOUD_STORAGE_EXPOSURE',
                                'url': url, 'param': 'Body Regex',
                                'payload': match,
                                'evidence': f"Publicly accessible cloud storage found: {bucket_url}",
                                'severity': 'HIGH', 'cvss': 8.1,
                                'request_raw': url,
                                'response_raw': b_resp.text[:500]
                            })
                    except: pass
        except Exception: pass
        return findings
