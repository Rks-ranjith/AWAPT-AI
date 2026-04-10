import asyncio
from playwright.async_api import BrowserContext, Page, Request, Response
from .types import CrawlerConfig, CrawlResult, NetworkRequest, FormDefinition
from .scope import ScopeEnforcer
from .queue import URLNormalizer

class JavaScriptCrawler:
    def __init__(self, config: CrawlerConfig, scope: ScopeEnforcer):
        self.config = config
        self.scope = scope
        self.request_log: list[NetworkRequest] = []

    async def crawl(self, start_url: str, context: BrowserContext) -> CrawlResult:
        page = await context.new_page()
        
        # Avoid blocking images/fonts to speed up
        await page.route("**/*", lambda route: route.continue_() if route.request.resource_type not in ["image", "media", "font"] else route.abort())

        page.on("request", self._on_request)

        try:
            await page.goto(start_url, wait_until="networkidle", timeout=self.config.timeout_ms)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1) # Settle SPA renders

            await self._discover_spa_routes(page)

            links = await self._extract_links(page)
            forms = await self._extract_forms(page)

            # Filter links by scope
            in_scope_links = [l for l in links if self.scope.is_in_scope(l)]

            return CrawlResult(
                links=in_scope_links,
                forms=forms,
                network_requests=list(self.request_log),
                base_url=start_url
            )
        finally:
            await page.close()

    def _on_request(self, request: Request):
        if self.scope.is_in_scope(request.url):
            self.request_log.append(NetworkRequest(
                url=request.url,
                method=request.method,
                headers=dict(request.headers),
                post_data=request.post_data,
                resource_type=request.resource_type
            ))

    async def _extract_links(self, page: Page) -> list[str]:
        # Extract all hrefs
        return await page.evaluate("Array.from(document.querySelectorAll('a[href]')).map(a => a.href)")

    async def _extract_forms(self, page: Page) -> list[FormDefinition]:
        forms = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('form').forEach(form => {
                    const inputs = [];
                    form.querySelectorAll('input, textarea, select').forEach(input => {
                        inputs.push({
                            name: input.name || input.id || null,
                            type: input.type || 'text',
                            value: input.value || '',
                            required: input.required,
                            pattern: input.pattern || null,
                            maxlength: input.maxLength || null,
                        });
                    });
                    results.push({
                        action: form.action || window.location.href,
                        method: form.method || 'GET',
                        enctype: form.enctype || 'application/x-www-form-urlencoded',
                        inputs: inputs,
                        hasFileUpload: inputs.some(i => i.type === 'file'),
                    });
                });
                return results;
            }
        """)
        return [FormDefinition(**f) for f in forms]

    async def _discover_spa_routes(self, page: Page):
        await page.evaluate("""
            window.__awap_routes = [];
            const originalPushState = history.pushState;
            history.pushState = function(...args) {
                window.__awap_routes.push(window.location.href);
                return originalPushState.apply(this, args);
            };
            window.addEventListener('hashchange', () => { window.__awap_routes.push(window.location.href); });
            window.addEventListener('popstate', () => { window.__awap_routes.push(window.location.href); });
        """)

        nav_selectors = ["a[href]", "button[onclick]", "[data-route]"]
        
        for selector in nav_selectors:
            elements = await page.query_selector_all(selector)
            for element in elements[:10]:
                try:
                    await element.click(timeout=1000)
                    await asyncio.sleep(0.2)
                except Exception:
                    continue
