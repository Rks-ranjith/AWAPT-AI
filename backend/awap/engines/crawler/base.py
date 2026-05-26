import asyncio
import logging
import re
from typing import List, Set, Dict, Any
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from awap.core.database import AsyncSessionLocal
from awap.models.endpoint import Endpoint
from sqlalchemy import select

logger = logging.getLogger(__name__)

JS_ENDPOINT_PATTERNS = [
    r'["\'](/api/[^"\']+)["\']',
    r'["\'](/v\d+/[^"\']+)["\']',
    r'axios\.(get|post|put|delete)\(["\']([^"\']+)["\']',
    r'fetch\(["\']([^"\']+)["\']',
    r'url:\s*["\']([^"\']+)["\']',
]

def extract_endpoints_from_js(js_content: str) -> list[str]:
    endpoints = []
    for pattern in JS_ENDPOINT_PATTERNS:
        matches = re.findall(pattern, js_content)
        endpoints.extend(matches if not matches or isinstance(matches[0], str) else [m[-1] for m in matches])
    return list(set(endpoints))

def is_in_scope(url: str, start_url: str) -> bool:
    target_netloc = urlparse(start_url).netloc
    test_netloc = urlparse(url).netloc
    
    def normalize_netloc(nl: str) -> str:
        return nl.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")

    if test_netloc and normalize_netloc(test_netloc) != normalize_netloc(target_netloc):
        return False
    risk_keywords = ["logout", "signout", "delete"]
    if any(k in url.lower() for k in risk_keywords):
        return False
    return True

async def store_crawl_page(scan_id: str, url: str, links: list[str], forms: list[dict]):
    async with AsyncSessionLocal() as db:
        # Save main endpoint
        method = "GET"
        from urllib.parse import parse_qs
        qs = urlparse(url).query
        params = list(parse_qs(qs).keys())
        
        # Check if exists
        e = await db.scalar(select(Endpoint).filter(Endpoint.scan_id == scan_id, Endpoint.url == url.split("?")[0]))
        if not e:
            e = Endpoint(scan_id=scan_id, url=url.split("?")[0], method=method, params=params, source="crawler")
            db.add(e)
            
        for form in forms:
            action = form.get("action") or url
            action = action.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            form_method = str(form.get("method", "GET")).upper()
            form_params = [i["name"] for i in form.get("inputs", []) if "name" in i]
            fe = await db.scalar(select(Endpoint).filter(Endpoint.scan_id == scan_id, Endpoint.url == action.split("?")[0], Endpoint.method == form_method))
            if not fe:
                db.add(Endpoint(scan_id=scan_id, url=action.split("?")[0], method=form_method, params=form_params, source="crawler"))
                
        await db.commit()

async def harvest_endpoint(req, scan_id: str):
    if req.resource_type in ["xhr", "fetch"]:
        try:
            url = req.url.split("?")[0]
            url = url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            method = req.method
            async with AsyncSessionLocal() as db:
                e = await db.scalar(select(Endpoint).filter(Endpoint.scan_id == scan_id, Endpoint.url == url, Endpoint.method == method))
                if not e:
                    db.add(Endpoint(scan_id=scan_id, url=url, method=method, params=[], source="js_analysis"))
                    await db.commit()
        except:
            pass

async def log_crawl_error(scan_id: str, url: str, error: str):
    logger.warning(f"Crawl error on {url}: {error}")
    # Also optionally insert to scan_log
    from awap.engines.worker import log_scan_event
    async with AsyncSessionLocal() as db:
        await log_scan_event(db, scan_id, "WARNING", f"Crawl error on {url}: {error}")

async def crawl_target(start_url: str, scan_id: str, max_pages: int = 100):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        # Intercept all requests to harvest endpoints
        page.on('request', lambda req: asyncio.create_task(harvest_endpoint(req, scan_id)))
        
        visited = set()
        queue = [start_url]
        
        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            
            try:
                # Use domcontentloaded to handle dynamic pages that have long-running tracking connections
                await page.goto(url, timeout=10000, wait_until='domcontentloaded')
            except Exception as e:
                await log_crawl_error(scan_id, url, f"Navigation timeout or certificate issue: {e}")
                # We do not skip the page on timeout or navigation errors, since some content may have successfully loaded
            
            try:
                # Extract all links
                links = await page.eval_on_selector_all('a[href]', 'els => els.map(e => e.href)')
                
                # Extract all forms
                forms = await page.eval_on_selector_all('form',
                    'els => els.map(e => ({action: e.action, method: e.method, inputs: [...e.elements].map(i => ({name: i.name, type: i.type}))}))')
                
                await store_crawl_page(scan_id, url, links, forms)
                
                queue.extend([l for l in links if is_in_scope(l, start_url)])
                
                # JS content extraction
                scripts = await page.eval_on_selector_all('script', 'els => els.map(e => e.innerText)')
                for script in scripts:
                    endpoints = extract_endpoints_from_js(script)
                    for ep in endpoints:
                        logger.info(f"JS extracted endpoint: {ep}")
                        
            except Exception as e:
                await log_crawl_error(scan_id, url, f"Content extraction failed: {e}")
                continue
        
        await browser.close()
