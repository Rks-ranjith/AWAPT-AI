import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import httpx

from awap.core.poc_builder import build_http_request_raw, build_http_response_raw

if TYPE_CHECKING:
    from awap.engines.scan_context import ScanContext


class AttackModule(ABC):
    module_id: str = "base"
    vuln_class: str = "UNKNOWN"

    def __init__(self, rate_limit: float = 10.0):
        self._default_rps = rate_limit
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            follow_redirects=False,
            verify=False,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def send_payload(
        self,
        url: str,
        method: str,
        payload: str,
        param: str,
        param_type: str,
        context: "ScanContext | None" = None,
    ) -> tuple[httpx.Response | None, dict[str, Any]]:
        """Send attack request with rate limiting, scope checks, and raw capture."""
        meta: dict[str, Any] = {"blocked": False, "reason": None}

        if context:
            if not context.scope_enforcer.is_in_scope(url):
                meta["blocked"] = True
                meta["reason"] = "out_of_scope"
                return None, meta
            await context.rate_limiter.acquire(context.target_domain)

        method = method.upper()
        try:
            if param_type == "url_param":
                import urllib.parse
                sep = "&" if "?" in url else "?"
                enc = urllib.parse.quote(str(payload), safe="")
                test_url = f"{url}{sep}{param}={enc}"
                resp = await self.client.request(method, test_url)
            elif param_type == "body":
                resp = await self.client.request(method, url, data={param: payload})
            elif param_type == "header":
                resp = await self.client.request(method, url, headers={param: payload})
            else:
                resp = await self.client.request(method, url)

            if resp.status_code == 429 and context:
                await asyncio.sleep(2.0)
                return await self.send_payload(url, method, payload, param, param_type, context)

            req_raw = build_http_request_raw(
                method,
                str(resp.request.url),
                dict(resp.request.headers),
            )
            res_raw = build_http_response_raw(
                resp.status_code,
                dict(resp.headers),
                resp.text,
            )
            meta["request_raw"] = req_raw
            meta["response_raw"] = res_raw
            meta["response_status"] = resp.status_code
            meta["response_headers"] = dict(resp.headers)
            meta["response_body"] = resp.text[:4000]
            return resp, meta
        except Exception as exc:
            meta["error"] = str(exc)
            return None, meta

    def analyze_with_rae(
        self,
        context: "ScanContext | None",
        url: str,
        resp: httpx.Response,
        payload: str,
    ) -> dict[str, Any]:
        if not context:
            return {"is_vulnerable": False, "confidence": 0.0, "evidence": []}
        return context.response_analyzer.analyze_response(url, resp, payload)

    @abstractmethod
    async def run(
        self,
        target_url: str,
        params: list[dict],
        context: "ScanContext | None" = None,
    ) -> list[dict]:
        pass
