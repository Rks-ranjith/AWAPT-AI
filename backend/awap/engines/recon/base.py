import asyncio
import aiohttp
import httpx
import logging
from urllib.parse import urlparse
import dns.resolver

logger = logging.getLogger(__name__)

async def enumerate_subdomains(domain: str) -> list[dict]:
    results = []
    
    # 1. crt.sh
    async with aiohttp.ClientSession() as session:
        try:
            url = f"https://crt.sh/?q=%.{domain}&output=json"
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for entry in data:
                        name = entry.get("name_value", "").lower()
                        for n in name.split("\\n"):
                            if n not in [r["subdomain"] for r in results]:
                                results.append({"subdomain": n, "source": "crt.sh"})
        except Exception as e:
            logger.warning(f"crt.sh error: {e}")
            
    # 2. DNS Brute-force (simplified)
    # Using python's dns module (dnspython must be in requirements)
    common_subs = ["api", "dev", "staging", "test", "admin", "mail", "www"]
    
    async def check_sub(sub):
        sub_domain = f"{sub}.{domain}"
        try:
            # We use an executor because dnspython's sync resolver blocks
            loop = asyncio.get_event_loop()
            answers = await loop.run_in_executor(None, dns.resolver.resolve, sub_domain, 'A')
            ip = answers[0].to_text()
            if sub_domain not in [r["subdomain"] for r in results]:
                results.append({"subdomain": sub_domain, "ip": ip, "source": "dns"})
        except Exception:
            pass

    await asyncio.gather(*(check_sub(sub) for sub in common_subs))
    
    return results

async def fingerprint_target(url: str) -> dict:
    tech = {"server": None, "framework": None, "cms": None, "waf": None}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                headers = resp.headers
                body = (await resp.text()).lower()
                
                tech["server"] = headers.get("Server")
                tech["language"] = headers.get("X-Powered-By")
                
                # WAF
                if "cf-ray" in headers or "cloudflare" in headers.get("Server", "").lower():
                    tech["waf"] = "Cloudflare"
                elif "x-akamai" in headers:
                    tech["waf"] = "Akamai"
                
                # CMS / Framework
                if "/wp-content/" in body:
                    tech["cms"] = "WordPress"
                elif "laravel_session" in headers.get("Set-Cookie", ""):
                    tech["framework"] = "Laravel"
        except Exception as e:
            logger.warning(f"Fingerprinting failed: {e}")
            
        # WAF specific test
        try:
            waf_url = f"{url}?q=<script>alert(1)</script>"
            async with session.get(waf_url, timeout=10) as resp:
                body = (await resp.text()).lower()
                if "cloudflare ray id" in body:
                    tech["waf"] = "Cloudflare"
                elif "access denied" in body:
                    tech["waf"] = "Generic WAF"
        except Exception:
            pass
            
    return tech

async def scan_common_ports(host: str) -> list[int]:
    common_ports = [80, 443, 8080, 8443, 3000, 5000, 8000, 8888, 9000]
    open_ports = []
    
    async def check_port(port):
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3.0)
            writer.close()
            await writer.wait_closed()
            open_ports.append(port)
        except Exception:
            pass

    await asyncio.gather(*(check_port(port) for port in common_ports))
    return open_ports
