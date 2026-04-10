import asyncio
import logging
from typing import List, Set, Dict
from playwright.async_api import async_playwright, Request
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class Endpoint:
    url: str
    method: str
    params: List[str]
    is_spa_route: bool

class CrawlerEngine:
    def __init__(self, target_url: str, max_depth: int = 3):
        self.target_url = target_url
        self.parsed_target = urlparse(target_url)
        self.discovered_endpoints: Dict[str, dict] = {} 
        self.max_depth = max_depth
        self.crawled_urls: Set[str] = set()
        self.exclusion_list = ["logout", "signout", "delete", "remove", "reset", "purge", "clear"]

    async def run(self) -> List[Endpoint]:
        """Perform recursive crawling with Playwright to extract SPA routes, API calls, and forms."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-web-security', '--disable-features=IsolateOrigins,site-per-process']
            )
            
            # Configure context to mimic reality and ignore weak TLS on targets
            context = await browser.new_context(
                ignore_https_errors=True,
                user_agent="AWAP-AI/1.0 (Security Research/Crawler; +https://github.com/)"
            )
            page = await context.new_page()
            
            # Event Listener: Intercept XHR / Fetch calls used in SPA React/Vue frontends
            page.on("request", lambda r: asyncio.create_task(self._handle_request(r)))
            
            try:
                await self._crawl_page(page, self.target_url, depth=0)
            except Exception as e:
                logger.error(f"[CRAWL] Fatal exception on {self.target_url}: {e}")
            finally:
                await browser.close()

        results = []
        for key, data in self.discovered_endpoints.items():
            results.append(Endpoint(
                url=data['url'],
                method=data['method'],
                params=list(data['params']),
                is_spa_route=data['is_spa']
            ))
        return results
        
    async def _handle_request(self, request: Request):
        """Intercepts all background network traffic the JS attempts to send to map hidden APIs."""
        if request.resource_type in ["xhr", "fetch"]:
            url = request.url
            if self._is_in_scope(url):
                self._add_endpoint(url, request.method, is_spa=True)

    def _is_in_scope(self, url: str) -> bool:
        netloc_match = urlparse(url).netloc == self.parsed_target.netloc
        risky_keyword = any(key in url.lower() for key in self.exclusion_list)
        return netloc_match and not risky_keyword

    def _add_endpoint(self, url: str, method: str, params: List[str] | None = None, is_spa: bool = False):
        clean_url = url.split('#')[0]
        key = f"{method} {clean_url}"
        
        if key not in self.discovered_endpoints:
            self.discovered_endpoints[key] = {
                'url': clean_url,
                'method': method,
                'params': set(params or []),
                'is_spa': is_spa
            }
        elif params:
            self.discovered_endpoints[key]['params'].update(params)

    async def _crawl_page(self, page, url: str, depth: int):
        if depth > self.max_depth:
            return

        logger.info(f"[CRAWL] Mapping depth {depth} -> {url}")
        self._add_endpoint(url, "GET")

        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
            
            # Extract standard href anchors
            links = await page.eval_on_selector_all(
                "a[href]", 
                "elements => elements.map(el => el.href)"
            )
            
            # Extract form endpoints with exact required parameter keys
            forms = await page.eval_on_selector_all(
                "form",
                """elements => elements.map(el => {
                    const inputs = Array.from(el.querySelectorAll('input, select, textarea'));
                    return { 
                        action: el.action, 
                        method: el.method || 'GET',
                        params: inputs.map(i => i.name).filter(n => n)
                    }
                })"""
            )
            
            for f in forms:
                target_action = f['action'] if f['action'] else url
                if self._is_in_scope(target_action):
                    self._add_endpoint(target_action, str(f['method']).upper(), f['params'])

            # Proceed recursively for discovered links within scope
            for link in set(links):
                if self._is_in_scope(link) and f"GET {link.split('#')[0]}" not in self.discovered_endpoints:
                    await self._crawl_page(page, link, depth + 1)

        except Exception as e:
            logger.debug(f"[CRAWL] Non-fatal navigation timeout on {url}")

    async def brute_force_parameters(self) -> None:
        """
        Implements Phase 2: Hidden Parameter Discovery.
        Fuzzes endpoints with a common wordlist to find undocumented GET inputs.
        """
        logger.info("[CRAWL] Initiating Parameter Discovery via Fuzzing...")
        common_params = ["debug", "admin", "test", "dev", "dir", "file", "id", "user", "path", "cmd"]
        
        import httpx
        
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            for key, data in self.discovered_endpoints.items():
                if data['method'] == "GET" and not data['is_spa']:
                    base_url = data['url']
                    try:
                        # 1. Establish baseline response length
                        baseline_resp = await client.get(base_url)
                        baseline_len = len(baseline_resp.content)
                        
                        # 2. Async bombard with test parameters
                        for param in common_params:
                            test_url = f"{base_url}?{param}=test_value_123"
                            resp = await client.get(test_url)
                            if abs(len(resp.content) - baseline_len) > 50:  # Differential response analysis
                                logger.info(f"[DISCOVERY] Found hidden parameter '{param}' on {base_url}")
                                data['params'].add(param)
                    except Exception as e:
                        continue
