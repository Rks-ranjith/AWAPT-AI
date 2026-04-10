# AWAP-AI — Core Scanning Engine Implementation Guide
## For AI Code Generation Systems — Authorized Security Research Use Only

---

## PREFACE

This document is a ground-level implementation guide for the critical subsystems of the AWAP-AI scanning engine. It is written to prevent the most common failure modes that occur when AI code generators produce scanning tools — incorrect async handling, missing scope enforcement, fragile response parsing, and flawed crawl logic. Every section includes real working patterns, known failure modes, and production-grade implementation guidance. Architecture, UI, and folder structure are covered in separate documents. This guide covers only the engine internals.

---

## 1. WEB CRAWLER ENGINE — DETAILED IMPLEMENTATION

### 1.1 Core Crawling Principles

The crawler is the foundation of the entire scan. If it misses endpoints, nothing downstream can find them. The crawler must behave like a real browser operated by a security researcher: it follows links, submits forms, executes JavaScript, respects session state, and never visits the same URL twice.

**Critical design constraint:** Every URL the crawler visits must be checked against the scope ruleset before the request is made — not after. Visiting out-of-scope URLs even once is a compliance failure.

### 1.2 Handling Modern JavaScript Websites

Static HTML crawling is insufficient for any application built after 2015. Use Playwright with headless Chromium. Do NOT use Requests + BeautifulSoup as the primary crawl strategy — use it only as a fallback for non-JS pages.

```python
from playwright.async_api import async_playwright, Page, BrowserContext
import asyncio

class JavaScriptCrawler:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.visited_urls: set[str] = set()
        self.discovered_endpoints: list[Endpoint] = []
        self.request_log: list[NetworkRequest] = []

    async def crawl(self, start_url: str, context: BrowserContext) -> CrawlResult:
        page = await context.new_page()

        # Intercept ALL network requests made by the page
        # This is how you find hidden API endpoints — not just links
        page.on("request", self._on_request)
        page.on("response", self._on_response)

        await page.goto(start_url, wait_until="networkidle", timeout=30000)

        # Wait for SPA routing to settle — critical for React/Vue/Angular apps
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)  # Additional settle time for deferred renders

        # Extract all links AFTER full JS execution
        links = await self._extract_links(page)
        forms = await self._extract_forms(page)
        api_calls = self._extract_api_calls_from_log()

        await page.close()
        return CrawlResult(links=links, forms=forms, api_calls=api_calls)

    async def _on_request(self, request):
        # Log every network request the browser makes
        # This catches XHR, Fetch, WebSocket, and preflight requests
        if self._is_in_scope(request.url):
            self.request_log.append(NetworkRequest(
                url=request.url,
                method=request.method,
                headers=dict(request.headers),
                post_data=request.post_data,
                resource_type=request.resource_type,
            ))
```

**SPA Route Discovery — Critical Pattern:**

Single-page apps change routes without making new HTTP requests. You must listen for `pushState` and `hashchange` events and re-crawl after each route change.

```python
async def _discover_spa_routes(self, page: Page) -> list[str]:
    discovered_routes = []

    # Inject route change listener before any navigation
    await page.evaluate("""
        window.__awap_routes = [];
        const originalPushState = history.pushState;
        history.pushState = function(...args) {
            window.__awap_routes.push(window.location.href);
            return originalPushState.apply(this, args);
        };
        window.addEventListener('hashchange', () => {
            window.__awap_routes.push(window.location.href);
        });
        window.addEventListener('popstate', () => {
            window.__awap_routes.push(window.location.href);
        });
    """)

    # Click all nav elements to trigger route changes
    nav_selectors = ["a[href]", "button[onclick]", "[data-route]",
                     "[data-href]", "[ng-click]", "[v-on\\:click]", "[@click]"]

    for selector in nav_selectors:
        elements = await page.query_selector_all(selector)
        for element in elements[:20]:  # Cap per selector to avoid infinite loops
            try:
                await element.click(timeout=2000)
                await page.wait_for_load_state("networkidle", timeout=3000)
                await asyncio.sleep(0.3)
            except Exception:
                continue  # Non-clickable elements are fine to skip

    routes = await page.evaluate("window.__awap_routes")
    return [r for r in routes if self._is_in_scope(r)]
```

### 1.3 Session Cookie Maintenance

Session loss is the most common crawler failure. When a session expires mid-crawl, authenticated endpoints become invisible.

```python
class SessionManager:
    def __init__(self, auth_config: AuthConfig):
        self.auth_config = auth_config
        self._context: BrowserContext = None
        self._session_valid = False
        self._last_auth_check = 0

    async def get_authenticated_context(self, playwright) -> BrowserContext:
        browser = await playwright.chromium.launch(headless=True)
        self._context = await browser.new_context(
            # Persist storage across pages — critical for maintaining login state
            storage_state=self.auth_config.storage_state_path if self.auth_config.storage_state_path else None
        )

        if self.auth_config.login_url:
            await self._perform_login()

        return self._context

    async def _perform_login(self):
        page = await self._context.new_page()
        await page.goto(self.auth_config.login_url)

        # Fill credentials
        await page.fill(self.auth_config.username_selector, self.auth_config.username)
        await page.fill(self.auth_config.password_selector, self.auth_config.password)
        await page.click(self.auth_config.submit_selector)
        await page.wait_for_load_state("networkidle")

        # Verify login succeeded by checking for auth indicator
        if self.auth_config.auth_success_indicator:
            success = await page.query_selector(self.auth_config.auth_success_indicator)
            if not success:
                raise AuthenticationError("Login failed — auth indicator not found")

        # Save storage state (cookies + localStorage) for reuse
        await self._context.storage_state(path="/tmp/awap_session.json")
        self._session_valid = True
        await page.close()

    async def check_and_refresh_session(self, page: Page) -> bool:
        """Call this before crawling each page in authenticated mode."""
        if self.auth_config.session_check_url:
            response = await page.goto(self.auth_config.session_check_url)
            if response.status in [401, 403] or await self._is_login_page(page):
                await self._perform_login()
                return True  # Session was refreshed
        return False  # Session still valid

    async def _is_login_page(self, page: Page) -> bool:
        url = page.url
        title = await page.title()
        has_password_field = await page.query_selector("input[type=password]")
        return bool(
            has_password_field or
            any(kw in url.lower() for kw in ["login", "signin", "auth"]) or
            any(kw in title.lower() for kw in ["login", "sign in"])
        )
```

### 1.4 Preventing Infinite Crawl Loops

This is the most common crawler bug in AI-generated code. Without deduplication, the crawler will loop forever on paginated content or parameterized URLs.

```python
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
import hashlib

class URLNormalizer:
    # Parameters that are safe to strip — they don't change page content
    IGNORABLE_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
        "fbclid", "gclid", "ref", "referrer", "_ga", "mc_cid", "mc_eid",
        "timestamp", "ts", "cb", "cachebust", "v", "_",
    }

    # Parameters that DO matter for deduplication
    # Treat pages with different values of these as distinct endpoints
    STRUCTURAL_PARAMS = {"id", "page", "tab", "section", "type", "category", "action"}

    @classmethod
    def normalize(cls, url: str) -> str:
        parsed = urlparse(url)

        # Strip fragment — fragments never change server-side content
        parsed = parsed._replace(fragment="")

        # Filter and sort query parameters for consistent hashing
        params = parse_qs(parsed.query, keep_blank_values=False)
        filtered = {
            k: v for k, v in params.items()
            if k.lower() not in cls.IGNORABLE_PARAMS
        }

        # Sort params so ?a=1&b=2 and ?b=2&a=1 hash identically
        sorted_query = urlencode(sorted(filtered.items()), doseq=True)
        normalized = urlunparse(parsed._replace(query=sorted_query))
        return normalized.rstrip("/")

    @classmethod
    def fingerprint(cls, url: str) -> str:
        """Returns a hash that treats parameterized URLs as the same endpoint.
        e.g. /user/1 and /user/2 get the same fingerprint for dedup purposes."""
        parsed = urlparse(url)
        path = cls._normalize_path(parsed.path)
        return hashlib.md5(f"{parsed.netloc}{path}".encode()).hexdigest()

    @classmethod
    def _normalize_path(cls, path: str) -> str:
        """Replace numeric IDs and UUIDs with placeholders."""
        import re
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{uuid}', path, flags=re.IGNORECASE
        )
        # Replace pure numeric segments
        path = re.sub(r'/\d+(/|$)', r'/{id}\1', path)
        return path


class CrawlQueue:
    def __init__(self, max_depth: int = 5, max_urls_per_path_pattern: int = 3):
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.visited_normalized: set[str] = set()
        self.visited_fingerprints: dict[str, int] = {}  # fingerprint → count
        self.max_depth = max_depth
        self.max_urls_per_path_pattern = max_urls_per_path_pattern

    def should_visit(self, url: str, depth: int) -> bool:
        if depth > self.max_depth:
            return False

        normalized = URLNormalizer.normalize(url)
        if normalized in self.visited_normalized:
            return False

        # Allow max N variations of the same path pattern
        # Prevents crawling /user/1 through /user/10000
        fp = URLNormalizer.fingerprint(url)
        if self.visited_fingerprints.get(fp, 0) >= self.max_urls_per_path_pattern:
            return False

        return True

    def mark_visited(self, url: str):
        normalized = URLNormalizer.normalize(url)
        fp = URLNormalizer.fingerprint(url)
        self.visited_normalized.add(normalized)
        self.visited_fingerprints[fp] = self.visited_fingerprints.get(fp, 0) + 1

    async def add(self, url: str, depth: int, priority: int = 5):
        if self.should_visit(url, depth):
            # Lower number = higher priority in asyncio.PriorityQueue
            await self.queue.put((priority, depth, url))
```

### 1.5 Domain Scope Enforcement

```python
import re
from urllib.parse import urlparse

class ScopeEnforcer:
    def __init__(self, scope_config: ScopeConfig):
        self.in_scope_patterns = [
            self._compile_pattern(p) for p in scope_config.in_scope
        ]
        self.out_of_scope_patterns = [
            self._compile_pattern(p) for p in scope_config.out_of_scope
        ]
        # Always block internal/cloud metadata ranges
        self.blocked_ips = self._build_blocked_ip_set()

    def _compile_pattern(self, pattern: str) -> re.Pattern:
        # Convert wildcard patterns to regex
        # *.example.com → matches any subdomain
        escaped = re.escape(pattern).replace(r'\*', r'[^.]+')
        return re.compile(f"^{escaped}$", re.IGNORECASE)

    def is_in_scope(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""

            # HARD BLOCK: Never allow internal or cloud metadata IPs
            if self._is_internal_ip(host):
                return False

            # Must match at least one in-scope pattern
            in_scope = any(p.match(host) for p in self.in_scope_patterns)
            if not in_scope:
                return False

            # Must not match any out-of-scope pattern
            out_of_scope = any(p.match(host) for p in self.out_of_scope_patterns)
            return not out_of_scope

        except Exception:
            return False  # Fail closed on parse errors

    def _is_internal_ip(self, host: str) -> bool:
        import ipaddress
        try:
            ip = ipaddress.ip_address(host)
            return (
                ip.is_private or
                ip.is_loopback or
                ip.is_link_local or
                ip.is_multicast or
                # Block cloud metadata endpoints
                str(ip).startswith("169.254.")  # AWS/GCP/Azure metadata
            )
        except ValueError:
            # hostname, not IP — check for localhost patterns
            return host in ["localhost", "metadata.google.internal",
                            "169.254.169.254"]

    def _build_blocked_ip_set(self) -> set:
        return {
            "127.0.0.1", "::1", "0.0.0.0",
            "169.254.169.254",  # AWS/Azure/GCP metadata
            "metadata.google.internal",
        }
```

### 1.6 Form and Input Extraction

```python
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
```

### 1.7 Crawl Prioritization Strategy

Assign priority scores to discovered URLs before adding them to the queue. High-value endpoints should be crawled first.

```python
class CrawlPrioritizer:
    # Lower score = higher priority (asyncio.PriorityQueue is min-heap)
    HIGH_VALUE_PATHS = [
        "/api/", "/admin/", "/login", "/upload", "/graphql",
        "/v1/", "/v2/", "/rest/", "/ws/", "/dashboard",
    ]
    LOW_VALUE_PATHS = [
        "/static/", "/assets/", "/images/", "/fonts/",
        "/favicon", "/robots.txt", "/sitemap.xml",
    ]

    @classmethod
    def score(cls, url: str, depth: int) -> int:
        base = depth * 10  # Deeper = lower priority
        path = urlparse(url).path.lower()

        for high in cls.HIGH_VALUE_PATHS:
            if high in path:
                base -= 20  # Boost high-value paths

        for low in cls.LOW_VALUE_PATHS:
            if low in path:
                base += 50  # Deprioritize static assets

        return max(0, base)
```

---

## 2. ENDPOINT AND PARAMETER DISCOVERY ENGINE

### 2.1 Multi-Source Endpoint Extraction

Endpoints must be harvested from five distinct sources. Missing any source means missing attack surface.

```python
class EndpointDiscoveryEngine:
    async def discover_all(self, crawl_result: CrawlResult, js_files: list[str]) -> list[Endpoint]:
        endpoints = []

        # Source 1: Direct links from crawl
        endpoints.extend(self._from_links(crawl_result.links))

        # Source 2: Form action URLs
        endpoints.extend(self._from_forms(crawl_result.forms))

        # Source 3: XHR/Fetch calls captured during crawl
        endpoints.extend(self._from_network_log(crawl_result.network_requests))

        # Source 4: JavaScript file static analysis
        for js_url in js_files:
            js_content = await self._fetch_js(js_url)
            endpoints.extend(self._from_javascript(js_content))

        # Source 5: Common path brute-force with wordlist
        endpoints.extend(await self._from_bruteforce(crawl_result.base_url))

        # Deduplicate while preserving richest metadata
        return self._deduplicate(endpoints)
```

### 2.2 JavaScript Endpoint Extraction

This is where most scanners miss large portions of the attack surface. Modern apps route everything through JS.

```python
import re
import ast

class JavaScriptAnalyzer:
    # Patterns for API endpoint strings in JS bundles
    ENDPOINT_PATTERNS = [
        # Fetch and XHR calls
        re.compile(r'''(?:fetch|axios\.(?:get|post|put|delete|patch))\s*\(\s*[`'"]((?:/[\w\-./{}?=&%]+)[`'"])'''),
        # String literals that look like API paths
        re.compile(r'''["'`](/(?:api|v\d|rest|graphql|gql|ws)[/\w\-{}?=&%.]*)[`'"]'''),
        # Template literals with path variables
        re.compile(r'''`(/[\w/\-]+\$\{[^}]+\}[\w/\-]*)`'''),
        # Object property assignments that look like endpoints
        re.compile(r'''(?:url|endpoint|path|route|baseUrl|apiUrl)\s*[:=]\s*[`'"]((?:https?://[^/]+)?/[\w/\-?.=&%{}]+)[`'"]'''),
        # Express/router patterns
        re.compile(r'''router\.(?:get|post|put|delete|patch|all)\s*\(\s*[`'"]([\w/\-:?*.]+)[`'"]'''),
    ]

    # Patterns for leaked secrets and credentials
    SECRET_PATTERNS = [
        re.compile(r'''(?:api[_-]?key|apikey|api[_-]?secret|token|bearer|secret[_-]?key)\s*[:=]\s*[`'"]([\w\-./+=]{20,})[`'"]''', re.IGNORECASE),
        re.compile(r'''(?:password|passwd|pwd)\s*[:=]\s*[`'"]((?!.*\$\{)[^'"]{6,})[`'"]''', re.IGNORECASE),
        re.compile(r'''AKIA[0-9A-Z]{16}'''),  # AWS Access Key ID
        re.compile(r'''eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'''),  # JWT
    ]

    def extract_endpoints(self, js_content: str, base_url: str) -> list[DiscoveredEndpoint]:
        endpoints = []

        # Try to unpack webpack bundles
        if "webpackJsonp" in js_content or "__webpack_require__" in js_content:
            js_content = self._unpack_webpack(js_content)

        for pattern in self.ENDPOINT_PATTERNS:
            for match in pattern.finditer(js_content):
                path = match.group(1)
                endpoints.append(DiscoveredEndpoint(
                    url=self._resolve_url(path, base_url),
                    source="javascript_static_analysis",
                    confidence=0.7,
                ))

        return self._deduplicate(endpoints)

    def _unpack_webpack(self, js: str) -> str:
        """
        Webpack bundles concatenate module strings.
        Extract string literals from module array to improve regex coverage.
        """
        module_pattern = re.compile(r'function\(module,exports,\w+\)\{(.*?)\}(?=,function|\))', re.DOTALL)
        modules = module_pattern.findall(js)
        return "\n".join(modules) if modules else js
```

### 2.3 Parameter Extraction and Storage

```python
from dataclasses import dataclass, field
from enum import Enum

class ParamLocation(Enum):
    URL_QUERY   = "url_query"
    URL_PATH    = "url_path"
    BODY_FORM   = "body_form"
    BODY_JSON   = "body_json"
    BODY_XML    = "body_xml"
    HEADER      = "header"
    COOKIE      = "cookie"
    GRAPHQL     = "graphql"

@dataclass
class Parameter:
    name: str
    location: ParamLocation
    original_value: str
    endpoint_id: str
    data_type: str = "string"      # string | integer | boolean | array | object
    is_reflected: bool = False      # Did original value appear in response?
    is_in_sql_context: bool = False # Did response suggest SQL context?
    is_in_html_context: bool = False
    is_in_js_context: bool = False
    injection_points: list[str] = field(default_factory=list)
    # Attack metadata populated after initial probe
    waf_detected: bool = False
    encoding_required: list[str] = field(default_factory=list)

class ParameterStore:
    """Central registry of all discovered parameters across all endpoints."""

    def __init__(self, db_session):
        self.db = db_session
        self._cache: dict[str, list[Parameter]] = {}

    async def register(self, param: Parameter):
        key = param.endpoint_id
        if key not in self._cache:
            self._cache[key] = []
        self._cache[key].append(param)
        await self._persist(param)

    async def get_attack_candidates(self, vuln_class: str) -> list[tuple[str, Parameter]]:
        """
        Return (endpoint_url, param) pairs filtered by relevance to a vuln class.
        Don't send XSS payloads to JSON-only APIs. Don't send SQLi to file upload fields.
        """
        candidates = []
        for endpoint_id, params in self._cache.items():
            for param in params:
                if self._is_relevant(param, vuln_class):
                    candidates.append((endpoint_id, param))
        return candidates

    def _is_relevant(self, param: Parameter, vuln_class: str) -> bool:
        irrelevant = {
            "SQLI":  [ParamLocation.HEADER, ParamLocation.COOKIE],  # Less common but not impossible
            "XSS":   [ParamLocation.BODY_JSON],  # JSON responses rarely rendered as HTML
            "SSTI":  [ParamLocation.BODY_JSON, ParamLocation.COOKIE],
            "CMDI":  [],  # All locations potentially relevant
            "SSRF":  [ParamLocation.URL_QUERY, ParamLocation.BODY_JSON],
        }
        # Default: all locations are relevant
        skip_locations = irrelevant.get(vuln_class, [])
        return param.location not in skip_locations
```

### 2.4 Parameter Fuzzing Preparation

Before sending attack payloads, perform a baseline probe to understand parameter behavior:

```python
class ParameterProfiler:
    async def profile(self, endpoint: Endpoint, param: Parameter,
                      http_client: AsyncHTTPClient) -> ParameterProfile:
        """
        Send 3 baseline requests to understand normal parameter behavior.
        This data is used to:
        1. Detect reflection
        2. Set anomaly detection baselines
        3. Identify injection context
        """
        canary = f"AWAP{id(param):x}"  # Unique probe string, no special chars

        response = await http_client.request(
            method=endpoint.method,
            url=endpoint.url,
            inject={param.name: canary, **self._other_params_with_valid_values(param)},
        )

        profile = ParameterProfile(
            param_name=param.name,
            baseline_status=response.status_code,
            baseline_length=len(response.body),
            baseline_time=response.elapsed_ms,
        )

        # Detect reflection
        if canary in response.text:
            profile.is_reflected = True
            profile.reflection_context = self._detect_context(response.text, canary)

        # Detect SQL context from error on invalid input
        sql_probe_response = await http_client.request(
            method=endpoint.method,
            url=endpoint.url,
            inject={param.name: "'", **self._other_params_with_valid_values(param)},
        )
        if self._has_sql_error(sql_probe_response.text):
            profile.likely_sql_context = True

        return profile

    def _detect_context(self, body: str, canary: str) -> str:
        idx = body.find(canary)
        if idx == -1:
            return "unknown"
        surrounding = body[max(0, idx-50):idx+len(canary)+50]
        if re.search(r'<[^>]*AWAP', surrounding) or re.search(r'AWAP[^<]*>', surrounding):
            return "html_attribute"
        if "<script" in body[max(0,idx-200):idx]:
            return "javascript_string"
        if re.search(r'(?:WHERE|FROM|SELECT|INSERT).*AWAP', surrounding, re.IGNORECASE):
            return "sql_query"
        return "html_body"
```

---

## 3. ATTACK EXECUTION ENGINE

### 3.1 Attack Module Registration

Use a plugin registry pattern. Modules self-register on import. The engine does not hardcode module names.

```python
from abc import ABC, abstractmethod
from typing import ClassVar
import importlib, pkgutil

# Global registry — populated by module imports
_MODULE_REGISTRY: dict[str, type["AttackModule"]] = {}

def register_module(cls):
    """Decorator that registers an attack module class."""
    _MODULE_REGISTRY[cls.module_id] = cls
    return cls

class AttackModule(ABC):
    module_id: ClassVar[str]
    vuln_class: ClassVar[str]
    severity: ClassVar[str]
    requires_reflection: ClassVar[bool] = False
    requires_oob: ClassVar[bool] = False
    safe_to_run_in_prod: ClassVar[bool] = True

    def __init__(self, payload_engine, http_client, oob_server=None):
        self.payload_engine = payload_engine
        self.http = http_client
        self.oob = oob_server

    @abstractmethod
    async def run(self, endpoint: Endpoint, param: Parameter,
                  profile: ParameterProfile) -> list["Finding"]: ...

    @abstractmethod
    async def verify(self, finding: "Finding") -> bool: ...

    def build_finding(self, endpoint, param, payload, request, response,
                      confidence, evidence) -> "Finding":
        return Finding(
            module_id=self.module_id,
            vuln_class=self.vuln_class,
            severity=self.severity,
            endpoint=endpoint.url,
            method=endpoint.method,
            parameter=param.name,
            parameter_location=param.location,
            payload=payload,
            request_raw=request.to_raw(),
            response_raw=response.to_raw(),
            confidence=confidence,
            evidence=evidence,
        )


def load_all_modules():
    """Import all modules from the modules package, triggering self-registration."""
    import awap.modules as pkg
    for _, name, _ in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"awap.modules.{name}")

def get_modules_for_profile(scan_profile: str) -> list[type[AttackModule]]:
    profile_filters = {
        "quick":   lambda m: m.severity == "CRITICAL",
        "standard":lambda m: m.severity in ["CRITICAL", "HIGH"],
        "full":    lambda m: True,
        "stealth": lambda m: m.safe_to_run_in_prod,
    }
    filter_fn = profile_filters.get(scan_profile, lambda m: True)
    return [m for m in _MODULE_REGISTRY.values() if filter_fn(m)]
```

### 3.2 Example: Production-Quality SQLi Error Module

This is what a well-implemented attack module looks like — not a skeleton:

```python
@register_module
class SQLiErrorModule(AttackModule):
    module_id = "sqli_error"
    vuln_class = "SQLI"
    severity = "CRITICAL"

    # Comprehensive SQL error signatures organized by DB
    SQL_ERRORS = {
        "mysql": [
            r"you have an error in your sql syntax",
            r"warning: mysql_",
            r"mysql_fetch_array\(\)",
            r"supplied argument is not a valid mysql result",
            r"mysql\.connector\.errors",
            r"\[mysql\]\[odbc",
        ],
        "postgresql": [
            r"pg_query\(\)",
            r"pg_exec\(\)",
            r"pg::syntaxerror",
            r"error: operator does not exist",
            r"pgsqlexception",
            r"unterminated quoted string at or near",
        ],
        "mssql": [
            r"unclosed quotation mark after the character string",
            r"incorrect syntax near",
            r"sqlexception",
            r"microsoft ole db provider for sql server",
            r"\[sql server\]",
            r"odbc sql server driver",
        ],
        "oracle": [
            r"ora-\d{5}",
            r"oracle error",
            r"oracle\.jdbc",
            r"quoted string not properly terminated",
        ],
        "sqlite": [
            r"sqlite_error",
            r"sqlite3\.operationalerror",
            r"unable to open database file",
            r"no such column:",
        ],
        "generic": [
            r"sql syntax.*mysql",
            r"warning.*\Wpg_",
            r"valid mysql result",
            r"mysqlclient",
            r"syntax error.*sql",
            r"jdbc driver",
        ],
    }

    PAYLOADS = ["'", '"', "';", '";', "' OR '1'='1", "' OR 1=1--",
                "' AND 1=2--", "1'", "1\"", "\\", "''", "`"]

    async def run(self, endpoint: Endpoint, param: Parameter,
                  profile: ParameterProfile) -> list[Finding]:
        findings = []

        for payload in self.PAYLOADS:
            try:
                response = await self.http.inject(
                    endpoint=endpoint,
                    param=param,
                    payload=payload,
                    timeout=10,
                )

                db_type, error_pattern = self._check_sql_error(response.text)

                if db_type:
                    finding = self.build_finding(
                        endpoint=endpoint,
                        param=param,
                        payload=payload,
                        request=response.request,
                        response=response,
                        confidence=0.9,
                        evidence={
                            "db_type": db_type,
                            "error_pattern": error_pattern,
                            "matched_text": self._extract_error_context(response.text, error_pattern),
                        },
                    )
                    findings.append(finding)
                    break  # First confirmed error is enough — don't spam

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._log_error(f"SQLi error probe failed for {endpoint.url}: {e}")
                continue

        return findings

    async def verify(self, finding: Finding) -> bool:
        """Repeat the exact request that triggered the finding to confirm it's reproducible."""
        response = await self.http.inject(
            endpoint=Endpoint(url=finding.endpoint, method=finding.method),
            param=Parameter(name=finding.parameter, location=finding.parameter_location,
                            original_value=""),
            payload=finding.payload,
            timeout=10,
        )
        db_type, _ = self._check_sql_error(response.text)
        return db_type is not None

    def _check_sql_error(self, body: str) -> tuple[str, str]:
        body_lower = body.lower()
        for db, patterns in self.SQL_ERRORS.items():
            for pattern in patterns:
                if re.search(pattern, body_lower):
                    return db, pattern
        return None, None

    def _extract_error_context(self, body: str, pattern: str) -> str:
        match = re.search(pattern, body.lower())
        if not match:
            return ""
        start = max(0, match.start() - 100)
        end = min(len(body), match.end() + 200)
        return body[start:end]
```

### 3.3 Safe Payload Injection

The HTTP injection layer must handle all parameter locations correctly:

```python
class PayloadInjector:
    async def inject(self, endpoint: Endpoint, param: Parameter,
                     payload: str, extra_headers: dict = None) -> HTTPResponse:
        """
        Inject payload into the correct location based on parameter type.
        Never modifies the endpoint object — always creates request copies.
        """
        headers = {**endpoint.base_headers, **(extra_headers or {})}

        if param.location == ParamLocation.URL_QUERY:
            url = self._inject_url_param(endpoint.url, param.name, payload)
            return await self._send(endpoint.method, url, headers=headers,
                                    body=endpoint.base_body)

        elif param.location == ParamLocation.BODY_FORM:
            body = {**endpoint.base_body_params, param.name: payload}
            return await self._send(endpoint.method, endpoint.url,
                                    headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                                    body=urlencode(body))

        elif param.location == ParamLocation.BODY_JSON:
            import json, copy
            body = copy.deepcopy(endpoint.base_body_json or {})
            self._set_nested_json(body, param.name, payload)
            return await self._send(endpoint.method, endpoint.url,
                                    headers={**headers, "Content-Type": "application/json"},
                                    body=json.dumps(body))

        elif param.location == ParamLocation.HEADER:
            headers[param.name] = payload
            return await self._send(endpoint.method, endpoint.url,
                                    headers=headers, body=endpoint.base_body)

        elif param.location == ParamLocation.COOKIE:
            headers["Cookie"] = self._inject_cookie(
                endpoint.base_cookies, param.name, payload
            )
            return await self._send(endpoint.method, endpoint.url,
                                    headers=headers, body=endpoint.base_body)

        elif param.location == ParamLocation.URL_PATH:
            url = endpoint.url.replace(f"{{{param.name}}}", payload)
            return await self._send(endpoint.method, url,
                                    headers=headers, body=endpoint.base_body)

        raise ValueError(f"Unsupported parameter location: {param.location}")

    def _set_nested_json(self, obj: dict, dotted_key: str, value: str):
        """Supports nested JSON keys like 'user.profile.name'."""
        keys = dotted_key.split(".")
        for key in keys[:-1]:
            obj = obj.setdefault(key, {})
        obj[keys[-1]] = value
```

---

## 4. PAYLOAD MANAGEMENT SYSTEM

### 4.1 Payload Database Structure

```python
# payloads/
# ├── sqli/
# │   ├── error_based.txt
# │   ├── blind_boolean.txt
# │   ├── time_based.txt
# │   ├── oob.txt
# │   └── second_order.txt
# ├── xss/
# │   ├── reflected.txt
# │   ├── stored.txt
# │   ├── dom.txt
# │   ├── csp_bypass.txt
# │   └── polyglots.txt
# ├── ssrf/
# │   ├── internal_probes.txt
# │   ├── cloud_metadata.txt
# │   └── protocol_wrappers.txt
# ├── ssti/
# │   ├── jinja2.txt
# │   ├── twig.txt
# │   ├── freemarker.txt
# │   └── generic.txt
# └── waf_bypass/
#     ├── cloudflare.txt
#     ├── aws_waf.txt
#     └── generic.txt

class PayloadLibrary:
    def __init__(self, payload_dir: str):
        self.payload_dir = payload_dir
        self._cache: dict[str, list[str]] = {}
        self._used: dict[str, set[str]] = {}  # Track used payloads per scan session

    def get(self, vuln_class: str, sub_type: str = None,
            waf: str = None, context: str = None) -> list[str]:
        key = f"{vuln_class}/{sub_type or 'all'}"

        if key not in self._cache:
            self._cache[key] = self._load(vuln_class, sub_type)

        payloads = list(self._cache[key])  # Copy to avoid mutation

        # Apply WAF-specific bypass layer on top
        if waf:
            payloads = self._apply_waf_bypasses(payloads, waf)

        # Apply context encoding
        if context:
            payloads = self._apply_context_encoding(payloads, context)

        # Prioritize: put high-confidence payloads first
        payloads = self._prioritize(payloads, vuln_class)

        return payloads

    def mark_used(self, scan_id: str, payload: str):
        if scan_id not in self._used:
            self._used[scan_id] = set()
        self._used[scan_id].add(payload)

    def is_used(self, scan_id: str, payload: str) -> bool:
        return payload in self._used.get(scan_id, set())

    def _load(self, vuln_class: str, sub_type: str) -> list[str]:
        payloads = []
        search_paths = []

        if sub_type:
            search_paths.append(
                os.path.join(self.payload_dir, vuln_class.lower(), f"{sub_type}.txt")
            )
        else:
            vuln_dir = os.path.join(self.payload_dir, vuln_class.lower())
            if os.path.isdir(vuln_dir):
                search_paths = [
                    os.path.join(vuln_dir, f)
                    for f in os.listdir(vuln_dir)
                    if f.endswith(".txt")
                ]

        for path in search_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            payloads.append(line)

        return payloads
```

### 4.2 Payload Mutation Engine

```python
class PayloadMutator:
    """
    Takes a seed payload and produces variants.
    Critical for WAF bypass and filter evasion.
    """

    @staticmethod
    def url_encode(payload: str) -> str:
        from urllib.parse import quote
        return quote(payload, safe="")

    @staticmethod
    def double_url_encode(payload: str) -> str:
        from urllib.parse import quote
        return quote(quote(payload, safe=""), safe="")

    @staticmethod
    def html_entities(payload: str) -> str:
        return payload.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    @staticmethod
    def unicode_escape_js(payload: str) -> str:
        return "".join(f"\\u{ord(c):04x}" if ord(c) > 127 or c in "<>\"'" else c
                       for c in payload)

    @staticmethod
    def mixed_case(payload: str) -> str:
        return "".join(c.upper() if i % 2 == 0 else c.lower()
                       for i, c in enumerate(payload))

    @staticmethod
    def sql_comment_injection(payload: str) -> str:
        """Insert SQL inline comments between keywords to bypass WAF keyword matching."""
        keywords = ["SELECT", "UNION", "FROM", "WHERE", "AND", "OR", "INSERT", "DROP"]
        result = payload
        for kw in keywords:
            result = re.sub(kw, f"{kw[:2]}/**/{ kw[2:]}", result, flags=re.IGNORECASE)
        return result

    @staticmethod
    def null_byte_injection(payload: str) -> str:
        return payload + "\x00"

    @staticmethod
    def newline_injection(payload: str) -> str:
        return payload.replace(" ", "%0a")

    @classmethod
    def generate_variants(cls, payload: str, vuln_class: str,
                          waf_detected: bool = False) -> list[str]:
        variants = [payload]  # Always include original

        if vuln_class == "XSS":
            variants.extend([
                cls.html_entities(payload),
                cls.url_encode(payload),
                cls.double_url_encode(payload),
                cls.unicode_escape_js(payload),
                payload.replace("<script>", "<Script>").replace("</script>", "</Script>"),
                payload.replace("<", "\x3c").replace(">", "\x3e"),
            ])

        elif vuln_class == "SQLI":
            variants.extend([
                cls.url_encode(payload),
                cls.double_url_encode(payload),
                cls.sql_comment_injection(payload),
                payload.replace(" ", "+"),
                payload.replace("'", "%27"),
                cls.mixed_case(payload),
            ])

        elif vuln_class == "CMDI":
            variants.extend([
                cls.url_encode(payload),
                payload.replace(" ", "${IFS}"),   # Bypass space filters in shell
                payload.replace(";", "%3b"),
                payload.replace("|", "%7c"),
                payload.replace("&", "%26"),
            ])

        # If WAF detected, apply aggressive bypass mutations
        if waf_detected:
            extra = []
            for v in variants:
                extra.append(cls.double_url_encode(v))
                extra.append(v.replace("=", "%3d").replace("+", "%2b"))
            variants.extend(extra)

        # Deduplicate while preserving order
        seen = set()
        return [v for v in variants if not (v in seen or seen.add(v))]
```

---

## 5. RESPONSE ANALYSIS ENGINE

### 5.1 Multi-Layer Analysis Architecture

```python
class ResponseAnalyzer:
    """
    Analyzes HTTP responses across 6 layers simultaneously.
    Returns a VulnerabilitySignal with confidence score and evidence.
    """

    def __init__(self, baseline: ResponseBaseline):
        self.baseline = baseline
        self.error_patterns = self._load_error_patterns()

    async def analyze(self, response: HTTPResponse, payload: str,
                      param: Parameter, vuln_class: str) -> AnalysisResult:
        signals = []

        # Layer 1: Error pattern matching
        error_signal = self._check_error_patterns(response, vuln_class)
        if error_signal:
            signals.append(error_signal)

        # Layer 2: Reflected payload detection
        reflection_signal = self._check_reflection(response, payload)
        if reflection_signal:
            signals.append(reflection_signal)

        # Layer 3: HTTP status anomaly
        status_signal = self._check_status_anomaly(response)
        if status_signal:
            signals.append(status_signal)

        # Layer 4: Content-length anomaly
        length_signal = self._check_length_anomaly(response)
        if length_signal:
            signals.append(length_signal)

        # Layer 5: Response time anomaly (for blind/time-based)
        timing_signal = self._check_timing_anomaly(response)
        if timing_signal:
            signals.append(timing_signal)

        # Layer 6: Structural changes
        structural_signal = self._check_structural_changes(response)
        if structural_signal:
            signals.append(structural_signal)

        return AnalysisResult(
            signals=signals,
            confidence=self._aggregate_confidence(signals),
            is_likely_vulnerable=len(signals) > 0 and self._aggregate_confidence(signals) > 0.6,
        )

    def _check_error_patterns(self, response: HTTPResponse,
                               vuln_class: str) -> Signal | None:
        if vuln_class not in self.error_patterns:
            return None

        body_lower = response.text.lower()
        for category, patterns in self.error_patterns[vuln_class].items():
            for pattern in patterns:
                if re.search(pattern, body_lower):
                    return Signal(
                        type="error_pattern",
                        confidence=0.85,
                        evidence={"category": category, "pattern": pattern},
                    )
        return None

    def _check_reflection(self, response: HTTPResponse, payload: str) -> Signal | None:
        # Check for direct reflection
        if payload in response.text:
            return Signal(type="direct_reflection", confidence=0.7,
                          evidence={"payload": payload, "encoding": "none"})

        # Check for encoded reflections
        encodings = {
            "url": urllib.parse.unquote(payload),
            "html": html.unescape(payload),
            "double_url": urllib.parse.unquote(urllib.parse.unquote(payload)),
        }
        for enc_name, decoded in encodings.items():
            if decoded != payload and decoded in response.text:
                return Signal(type="encoded_reflection", confidence=0.65,
                              evidence={"payload": payload, "encoding": enc_name})
        return None

    def _check_timing_anomaly(self, response: HTTPResponse) -> Signal | None:
        """
        For time-based blind vulnerabilities.
        Only flag if response time significantly exceeds baseline AND
        the payload was a time-based payload (contains SLEEP, WAITFOR, pg_sleep etc.)
        """
        if self.baseline.mean_response_time is None:
            return None

        threshold = max(
            self.baseline.mean_response_time + 3 * self.baseline.std_response_time,
            4000,  # Minimum 4 second absolute threshold
        )

        if response.elapsed_ms > threshold:
            return Signal(
                type="timing_anomaly",
                confidence=0.75,
                evidence={
                    "elapsed_ms": response.elapsed_ms,
                    "baseline_mean_ms": self.baseline.mean_response_time,
                    "threshold_ms": threshold,
                },
            )
        return None

    def _check_length_anomaly(self, response: HTTPResponse) -> Signal | None:
        if self.baseline.mean_content_length is None:
            return None

        delta_pct = abs(len(response.body) - self.baseline.mean_content_length) / max(self.baseline.mean_content_length, 1)

        if delta_pct > 0.15:  # More than 15% change in content length
            return Signal(
                type="length_anomaly",
                confidence=0.4,  # Low confidence alone — needs corroboration
                evidence={
                    "response_length": len(response.body),
                    "baseline_length": self.baseline.mean_content_length,
                    "delta_pct": delta_pct,
                },
            )
        return None

    def _aggregate_confidence(self, signals: list[Signal]) -> float:
        if not signals:
            return 0.0
        # Combine signals using Noisy-OR model
        # P(at least one signal is correct) = 1 - product(1 - P(each signal))
        p_none_correct = 1.0
        for signal in signals:
            p_none_correct *= (1.0 - signal.confidence)
        return 1.0 - p_none_correct
```

### 5.2 False Positive Reduction

```python
class FalsePositiveFilter:
    """
    Apply before recording a finding. Requires multiple confirming signals
    for low-confidence detections.
    """

    FP_THRESHOLDS = {
        "error_pattern":     0.0,   # SQL error in response = always record
        "direct_reflection": 0.6,   # Reflection alone = only if >60% confidence
        "timing_anomaly":    0.0,   # Only record if confirmed with 3 trials
        "length_anomaly":    0.9,   # Never record length change alone
        "status_change":     0.7,
    }

    # Known "false positive" error pages that many apps serve for any 404
    FALSE_POSITIVE_INDICATORS = [
        "page not found",
        "404 not found",
        "the page you requested",
        "this page does not exist",
    ]

    def is_false_positive(self, result: AnalysisResult, response: HTTPResponse) -> bool:
        # If the response is a generic error page, discard
        body_lower = response.text.lower()
        if any(fp in body_lower for fp in self.FALSE_POSITIVE_INDICATORS):
            if response.status_code in [400, 404, 500]:
                return True

        # If only signal is low-confidence length change, discard
        if (len(result.signals) == 1 and
                result.signals[0].type == "length_anomaly" and
                result.signals[0].confidence < 0.9):
            return True

        # Timing: require 3 consecutive timing anomalies
        if (result.signals and
                all(s.type == "timing_anomaly" for s in result.signals) and
                len(result.signals) < 3):
            return True  # Will be re-confirmed by verification module

        return False
```

---

## 6. ASYNCHRONOUS SCANNING SYSTEM

### 6.1 Async Architecture

**Critical rule:** Never use `asyncio.gather(*all_tasks)` for scan tasks. This launches all tasks simultaneously, saturates connections, and crashes the target. Use a semaphore-controlled worker pool.

```python
import asyncio
from asyncio import Semaphore

class ScanWorkerPool:
    def __init__(self, config: ScanConfig):
        self.config = config
        # Semaphore controls total concurrent requests system-wide
        self._request_semaphore = Semaphore(config.max_concurrent_requests)
        # Separate semaphore per target prevents a single target getting all connections
        self._per_target_semaphores: dict[str, Semaphore] = {}
        self._rate_limiter = RateLimiter(config.requests_per_second)
        self._task_queue: asyncio.Queue = asyncio.Queue(maxsize=config.queue_size)
        self._results: list[Finding] = []
        self._running = False

    async def submit(self, task: ScanTask):
        await self._task_queue.put(task)

    async def run(self, num_workers: int = None):
        num_workers = num_workers or self.config.worker_count
        self._running = True
        workers = [
            asyncio.create_task(self._worker(i))
            for i in range(num_workers)
        ]
        # Sentinel values to stop workers when queue is empty
        for _ in range(num_workers):
            await self._task_queue.put(None)

        await asyncio.gather(*workers)

    async def _worker(self, worker_id: int):
        while self._running:
            task = await self._task_queue.get()
            if task is None:
                break
            try:
                await self._execute_with_limits(task)
            except Exception as e:
                log.error(f"Worker {worker_id} task failed: {e}", exc_info=True)
            finally:
                self._task_queue.task_done()

    async def _execute_with_limits(self, task: ScanTask):
        target_host = urlparse(task.endpoint.url).netloc

        # Acquire per-target semaphore
        if target_host not in self._per_target_semaphores:
            self._per_target_semaphores[target_host] = Semaphore(
                self.config.max_connections_per_target
            )

        async with self._per_target_semaphores[target_host]:
            async with self._request_semaphore:
                # Rate limit: wait if we're sending too fast
                await self._rate_limiter.acquire()
                result = await task.execute()
                if result:
                    self._results.extend(result)
```

### 6.2 Rate Limiter Implementation

```python
import time

class RateLimiter:
    """
    Token bucket rate limiter.
    More accurate than simple sleep-based throttling.
    """
    def __init__(self, rate: float):  # rate = requests per second
        self.rate = rate
        self.tokens = rate
        self.last_check = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_check
            self.last_check = now
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)

            if self.tokens >= 1:
                self.tokens -= 1
            else:
                # Wait for next token
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
```

---

## 7. SCAN CONTROL AND SAFETY SYSTEM

### 7.1 Scan State Machine

```python
from enum import Enum
import asyncio

class ScanState(Enum):
    CREATED        = "created"
    SCOPE_VERIFIED = "scope_verified"
    RECON          = "recon"
    CRAWL          = "crawl"
    MAPPING        = "mapping"
    ATTACK         = "attack"
    ANALYSIS       = "analysis"
    REPORTING      = "reporting"
    COMPLETE       = "complete"
    PAUSED         = "paused"
    ABORTED        = "aborted"
    FAILED         = "failed"

class ScanController:
    def __init__(self, scan_id: str, db, event_bus):
        self.scan_id = scan_id
        self.db = db
        self.event_bus = event_bus
        self._state = ScanState.CREATED
        self._pause_event = asyncio.Event()
        self._abort_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially

    @property
    def is_running(self) -> bool:
        return self._state not in [ScanState.PAUSED, ScanState.ABORTED,
                                   ScanState.COMPLETE, ScanState.FAILED]

    async def pause(self):
        self._pause_event.clear()
        await self._transition(ScanState.PAUSED)

    async def resume(self):
        self._pause_event.set()
        await self._transition(self._pre_pause_state)

    async def abort(self):
        self._abort_event.set()
        self._pause_event.set()  # Unblock any waiting code
        await self._transition(ScanState.ABORTED)

    async def checkpoint(self):
        """
        Call this at the start of every scan task.
        Blocks on pause, raises on abort.
        Workers must call this regularly.
        """
        if self._abort_event.is_set():
            raise ScanAbortedException(f"Scan {self.scan_id} aborted")
        # Block until unpaused
        await self._pause_event.wait()
        if self._abort_event.is_set():
            raise ScanAbortedException(f"Scan {self.scan_id} aborted during pause")

    async def _transition(self, new_state: ScanState):
        old_state = self._state
        self._state = new_state
        await self.db.update_scan_state(self.scan_id, new_state)
        await self.event_bus.emit("scan_state_change", {
            "scan_id": self.scan_id,
            "old_state": old_state.value,
            "new_state": new_state.value,
        })
```

### 7.2 Anti-DoS Controls

```python
class AntiDoSGuard:
    """
    Hard limits that cannot be overridden by user config.
    These protect both the target and the scanning platform.
    """
    HARD_MAX_RPS = 50           # Never exceed 50 req/s regardless of config
    HARD_MAX_CONNECTIONS = 50   # Never exceed 50 concurrent connections
    BACKOFF_STATUS_CODES = {429, 503, 502}
    ERROR_RATE_THRESHOLD = 0.3  # If >30% requests error, throttle

    def __init__(self):
        self._error_window: list[bool] = []  # Rolling window of last 100 requests
        self._consecutive_429s = 0

    def clamp_config(self, config: ScanConfig) -> ScanConfig:
        config.requests_per_second = min(config.requests_per_second, self.HARD_MAX_RPS)
        config.max_concurrent_requests = min(config.max_concurrent_requests,
                                             self.HARD_MAX_CONNECTIONS)
        return config

    async def on_response(self, response: HTTPResponse, rate_limiter: RateLimiter):
        is_error = response.status_code >= 500 or response.status_code in self.BACKOFF_STATUS_CODES

        self._error_window.append(is_error)
        if len(self._error_window) > 100:
            self._error_window.pop(0)

        if response.status_code == 429:
            self._consecutive_429s += 1
            backoff = min(2 ** self._consecutive_429s, 60)  # Exponential, max 60s
            log.warning(f"Rate limited (429). Backing off {backoff}s.")
            await asyncio.sleep(backoff)
            rate_limiter.rate = max(1, rate_limiter.rate * 0.5)  # Halve rate
        else:
            self._consecutive_429s = 0

        # If error rate is high, throttle proactively
        if len(self._error_window) >= 20:
            error_rate = sum(self._error_window) / len(self._error_window)
            if error_rate > self.ERROR_RATE_THRESHOLD:
                rate_limiter.rate = max(1, rate_limiter.rate * 0.7)
                log.warning(f"High error rate ({error_rate:.0%}). Reducing rate to {rate_limiter.rate:.1f} req/s")
```

---

## 8. SCAN DATA STORAGE DESIGN

### 8.1 PostgreSQL Schema

```sql
-- Endpoints table — indexed for fast parameter lookups
CREATE TABLE endpoints (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id         UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    normalized_url  TEXT NOT NULL,
    method          VARCHAR(10) NOT NULL,
    content_type    VARCHAR(100),
    status_code     INT,
    base_response_length INT,
    base_response_time_ms INT,
    discovered_at   TIMESTAMPTZ DEFAULT NOW(),
    crawl_depth     INT DEFAULT 0,
    source          VARCHAR(50),  -- 'crawler'|'js_analysis'|'bruteforce'|'network_log'
    UNIQUE(scan_id, normalized_url, method)
);
CREATE INDEX idx_endpoints_scan_id ON endpoints(scan_id);
CREATE INDEX idx_endpoints_url_pattern ON endpoints USING gin(to_tsvector('simple', url));

-- Parameters table
CREATE TABLE parameters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint_id     UUID NOT NULL REFERENCES endpoints(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    location        VARCHAR(20) NOT NULL,  -- url_query|body_form|body_json|header|cookie
    original_value  TEXT,
    data_type       VARCHAR(20) DEFAULT 'string',
    is_reflected    BOOLEAN DEFAULT FALSE,
    reflection_context VARCHAR(30),
    waf_detected    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_parameters_endpoint ON parameters(endpoint_id);

-- Findings table
CREATE TABLE findings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id         UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    endpoint_id     UUID REFERENCES endpoints(id),
    parameter_id    UUID REFERENCES parameters(id),
    module_id       VARCHAR(50) NOT NULL,
    vuln_class      VARCHAR(30) NOT NULL,
    severity        VARCHAR(10) NOT NULL,
    cvss_score      NUMERIC(3,1),
    cvss_vector     TEXT,
    cwe_id          TEXT,
    payload         TEXT,
    confidence      NUMERIC(3,2),
    verified        BOOLEAN DEFAULT FALSE,
    false_positive  BOOLEAN DEFAULT FALSE,
    status          VARCHAR(20) DEFAULT 'open',
    assigned_to     UUID REFERENCES users(id),
    evidence        JSONB,           -- Full evidence blob
    request_raw     TEXT,
    response_raw    TEXT,
    screenshot_url  TEXT,
    discovered_at   TIMESTAMPTZ DEFAULT NOW(),
    verified_at     TIMESTAMPTZ,
    llm_explanation TEXT,
    remediation     TEXT
);
CREATE INDEX idx_findings_scan_id ON findings(scan_id);
CREATE INDEX idx_findings_severity ON findings(severity) WHERE false_positive = FALSE;
CREATE INDEX idx_findings_vuln_class ON findings(vuln_class);
-- Full-text search across finding content
CREATE INDEX idx_findings_fts ON findings USING gin(
    to_tsvector('english', coalesce(vuln_class,'') || ' ' || coalesce(payload,''))
);

-- Request/response log (high-volume — partition by scan_id)
CREATE TABLE request_log (
    id              BIGSERIAL,
    scan_id         UUID NOT NULL,
    endpoint_id     UUID,
    method          VARCHAR(10),
    url             TEXT,
    request_headers JSONB,
    request_body    TEXT,
    response_status INT,
    response_headers JSONB,
    response_body   TEXT,
    elapsed_ms      INT,
    payload         TEXT,
    module_id       VARCHAR(50),
    logged_at       TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY HASH(scan_id);

-- Create 8 partitions for request_log
CREATE TABLE request_log_0 PARTITION OF request_log FOR VALUES WITH (modulus 8, remainder 0);
-- ... (repeat for 1-7)
CREATE INDEX idx_request_log_scan ON request_log(scan_id, logged_at);
```

### 8.2 Storage Best Practices

```python
class ScanDataStore:
    # Do NOT store full request/response bodies in the findings table.
    # Store them in the request_log and reference by ID.
    # Findings table must stay fast — it's queried constantly during scans.

    MAX_RESPONSE_BODY_SIZE = 1024 * 1024  # 1MB max stored per response

    async def log_request(self, scan_id: str, req: HTTPRequest,
                          resp: HTTPResponse, module_id: str = None) -> str:
        # Truncate oversized bodies before storage
        response_body = resp.text
        if len(response_body) > self.MAX_RESPONSE_BODY_SIZE:
            response_body = response_body[:self.MAX_RESPONSE_BODY_SIZE] + "\n[TRUNCATED]"

        return await self.db.execute("""
            INSERT INTO request_log
            (scan_id, method, url, request_headers, request_body,
             response_status, response_headers, response_body, elapsed_ms, module_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING id
        """, scan_id, req.method, req.url, json.dumps(dict(req.headers)),
            req.body, resp.status_code, json.dumps(dict(resp.headers)),
            response_body, resp.elapsed_ms, module_id)

    async def save_finding(self, finding: Finding, scan_id: str) -> str:
        # Check for duplicate finding before inserting
        existing = await self.db.fetchrow("""
            SELECT id FROM findings
            WHERE scan_id=$1 AND vuln_class=$2 AND endpoint_id=$3 AND parameter_id=$4
              AND false_positive = FALSE
        """, scan_id, finding.vuln_class, finding.endpoint_id, finding.parameter_id)

        if existing:
            return existing["id"]  # Deduplicate at storage layer

        return await self.db.execute("""
            INSERT INTO findings
            (scan_id, endpoint_id, parameter_id, module_id, vuln_class, severity,
             confidence, payload, request_raw, response_raw, evidence)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING id
        """, scan_id, finding.endpoint_id, finding.parameter_id, finding.module_id,
            finding.vuln_class, finding.severity, finding.confidence,
            finding.payload, finding.request_raw, finding.response_raw,
            json.dumps(finding.evidence))
```

---

## 9. VULNERABILITY RESULT VALIDATION

### 9.1 Multi-Trial Verification

```python
class FindingVerifier:
    """
    Before a finding becomes a confirmed vulnerability, it must pass verification.
    This cuts false positive rates dramatically.
    """

    REQUIRED_CONFIRMATIONS = {
        "SQLI_ERROR":    1,  # Error signature is definitive
        "SQLI_BLIND":    3,  # Boolean-blind needs 3 consistent trials
        "SQLI_TIME":     3,  # Time-based needs 3 consistent timing anomalies
        "XSS_REFLECTED": 2,  # Reflection needs 2 confirmations
        "XSS_STORED":    2,
        "CMDI":          2,
        "SSRF":          1,  # OOB callback is definitive
        "SSTI":          2,
        "IDOR":          2,
        "CORS":          1,
    }

    async def verify(self, finding: Finding, module: AttackModule,
                     delay_between_trials: float = 1.0) -> VerificationResult:
        required = self.REQUIRED_CONFIRMATIONS.get(
            f"{finding.vuln_class}_{finding.sub_type or 'ERROR'}", 2
        )
        confirmations = 0

        for trial in range(required + 1):  # One extra to reduce noise
            await asyncio.sleep(delay_between_trials)
            try:
                confirmed = await module.verify(finding)
                if confirmed:
                    confirmations += 1
            except Exception as e:
                log.warning(f"Verification trial {trial} failed: {e}")

        # Must confirm in required/total trials
        success_rate = confirmations / (required + 1)
        verified = confirmations >= required

        return VerificationResult(
            verified=verified,
            confirmations=confirmations,
            trials=required + 1,
            success_rate=success_rate,
            confidence_adjustment=success_rate,
        )
```

### 9.2 Proof-of-Concept Generation

```python
class PoCGenerator:
    @staticmethod
    def generate_curl(finding: Finding) -> str:
        req = finding.request_raw
        # Parse raw HTTP request and convert to curl command
        lines = req.split("\n")
        method_line = lines[0].split()
        method = method_line[0]
        path = method_line[1]

        # Extract host from headers
        host = next((l.split(": ")[1] for l in lines if l.lower().startswith("host:")), "")
        url = f"https://{host}{path}"

        # Build curl command
        cmd = f"curl -v -X {method}"
        for line in lines[1:]:
            if ": " in line and not line.lower().startswith("content-length"):
                key, val = line.split(": ", 1)
                cmd += f' -H "{key}: {val.strip()}"'
        if finding.method in ["POST", "PUT", "PATCH"] and finding.request_body:
            cmd += f" --data '{finding.request_body}'"
        cmd += f" '{url}'"
        return cmd

    @staticmethod
    def generate_python(finding: Finding) -> str:
        import json
        body = finding.evidence.get("request_body", "")
        headers_raw = finding.evidence.get("request_headers", {})

        return f"""import requests

url = "{finding.endpoint}"
headers = {json.dumps(headers_raw, indent=4)}
payload = "{finding.payload}"

response = requests.request(
    method="{finding.method}",
    url=url,
    headers=headers,
    {"data=" + repr(body) if body else ""},
    verify=False,
    timeout=30,
)

print(f"Status: {{response.status_code}}")
print(f"Length: {{len(response.text)}}")
print(response.text[:500])
"""
```

---

## 10. ERROR HANDLING AND STABILITY

### 10.1 HTTP Client with Retry Logic

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class RobustHTTPClient:
    RETRY_EXCEPTIONS = (
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.ConnectError,
        httpx.RemoteProtocolError,
    )

    def __init__(self, config: ScanConfig):
        self.client = httpx.AsyncClient(
            verify=False,            # Scanning self-signed certs is normal
            follow_redirects=True,
            timeout=httpx.Timeout(
                connect=10.0,
                read=30.0,
                write=10.0,
                pool=60.0,
            ),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=50,
            ),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(tuple(RETRY_EXCEPTIONS)),
        reraise=True,
    )
    async def request(self, method: str, url: str, **kwargs) -> HTTPResponse:
        try:
            response = await self.client.request(method, url, **kwargs)
            return HTTPResponse.from_httpx(response)
        except httpx.ConnectTimeout:
            log.debug(f"Connect timeout: {url}")
            raise
        except httpx.ReadTimeout:
            log.debug(f"Read timeout: {url}")
            raise
        except httpx.TooManyRedirects:
            # Log but don't retry — infinite redirect loop in target
            log.warning(f"Too many redirects: {url}")
            return HTTPResponse.error(url, 0, "too_many_redirects")
        except httpx.InvalidURL as e:
            log.warning(f"Invalid URL {url}: {e}")
            return HTTPResponse.error(url, 0, "invalid_url")
        except Exception as e:
            log.error(f"Unexpected HTTP error for {url}: {type(e).__name__}: {e}")
            raise
```

### 10.2 Scan Recovery

```python
class ScanRecoveryManager:
    """
    Saves scan progress at regular checkpoints.
    On restart after crash, resumes from last checkpoint.
    """

    CHECKPOINT_EVERY_N_TASKS = 50

    async def save_checkpoint(self, scan_id: str, state: ScanCheckpoint):
        await self.db.execute("""
            INSERT INTO scan_checkpoints (scan_id, checkpoint_data, saved_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (scan_id) DO UPDATE
            SET checkpoint_data = $2, saved_at = NOW()
        """, scan_id, json.dumps(state.to_dict()))

    async def load_checkpoint(self, scan_id: str) -> ScanCheckpoint | None:
        row = await self.db.fetchrow(
            "SELECT checkpoint_data FROM scan_checkpoints WHERE scan_id=$1",
            scan_id
        )
        if row:
            return ScanCheckpoint.from_dict(json.loads(row["checkpoint_data"]))
        return None

    async def resume_scan(self, scan_id: str) -> bool:
        checkpoint = await self.load_checkpoint(scan_id)
        if not checkpoint:
            return False

        log.info(f"Resuming scan {scan_id} from checkpoint: "
                 f"phase={checkpoint.phase}, "
                 f"endpoints_done={len(checkpoint.completed_endpoint_ids)}")

        # Filter already-processed endpoints out of the work queue
        # before re-launching the scan engine
        return True
```

---

## 11. PERFORMANCE OPTIMIZATION

### 11.1 Response Caching

```python
import hashlib
from functools import lru_cache

class ResponseCache:
    """
    Cache baseline responses to avoid redundant requests.
    Only cache GET requests with no injection — never cache attack requests.
    """
    def __init__(self, max_size_mb: int = 100):
        self._store: dict[str, CachedResponse] = {}
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._current_size = 0

    def _cache_key(self, method: str, url: str, headers: dict) -> str:
        # Exclude time-varying headers from cache key
        stable_headers = {k: v for k, v in headers.items()
                         if k.lower() not in ["date", "x-request-id", "x-trace-id"]}
        content = f"{method}:{url}:{sorted(stable_headers.items())}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, method: str, url: str, headers: dict) -> CachedResponse | None:
        if method != "GET":
            return None  # Never cache non-GET requests
        key = self._cache_key(method, url, headers)
        cached = self._store.get(key)
        if cached and not cached.is_expired():
            return cached
        return None

    def set(self, method: str, url: str, headers: dict,
            response: HTTPResponse, ttl: int = 300):
        if method != "GET":
            return
        key = self._cache_key(method, url, headers)
        body_size = len(response.body)
        if body_size > 5 * 1024 * 1024:  # Don't cache responses > 5MB
            return
        # Evict if needed
        while self._current_size + body_size > self._max_size_bytes and self._store:
            oldest_key = next(iter(self._store))
            evicted = self._store.pop(oldest_key)
            self._current_size -= len(evicted.body)

        self._store[key] = CachedResponse(response=response, expires_at=time.time() + ttl)
        self._current_size += body_size
```

### 11.2 Endpoint Attack Prioritization

```python
class AttackPrioritizer:
    """
    Score endpoints to decide which ones to attack first.
    High-risk endpoints get the full payload set.
    Low-risk endpoints get a quick probe.
    """

    def score_endpoint(self, endpoint: Endpoint, params: list[Parameter]) -> float:
        score = 0.0

        # Technology stack indicators
        tech_scores = {
            "php": 0.3, "asp": 0.3, "aspx": 0.3, "jsp": 0.3,
            "cfm": 0.2, "py": 0.1, "rb": 0.1,
        }
        ext = endpoint.url.split(".")[-1].lower() if "." in endpoint.url else ""
        score += tech_scores.get(ext, 0.0)

        # Parameter count — more params = more attack surface
        score += min(len(params) * 0.1, 0.5)

        # Parameter types
        for param in params:
            if param.is_reflected:
                score += 0.3  # Reflected params = XSS candidates
            if param.data_type == "integer":
                score += 0.2  # Integer params = SQLi candidates
            if param.location in [ParamLocation.BODY_JSON, ParamLocation.BODY_FORM]:
                score += 0.1

        # Path keywords
        high_risk_keywords = ["admin", "api", "upload", "exec", "cmd", "run",
                              "query", "search", "filter", "proxy", "redirect",
                              "load", "include", "template", "render", "eval"]
        path_lower = endpoint.url.lower()
        for kw in high_risk_keywords:
            if kw in path_lower:
                score += 0.2
                break

        return min(score, 1.0)
```

---

## 12. DEVELOPER IMPLEMENTATION NOTES

### 12.1 Common AI Code Generator Mistakes and How to Fix Them

**Mistake 1: Using `requests` library for crawling SPAs**
AI generators default to `requests.get()` for crawling. This misses all JavaScript-rendered content. Fix: Use Playwright with `wait_until="networkidle"` for all crawling.

**Mistake 2: Storing raw HTTP bodies directly in findings tables**
AI generators dump everything into one table. Fix: Separate the `findings` table (small, frequently queried) from the `request_log` table (high-volume, append-only). Use foreign key references.

**Mistake 3: `asyncio.gather()` without concurrency limits**
AI generators love `asyncio.gather(*all_1000_tasks)`. This crashes everything. Fix: Always use a `Semaphore`-controlled worker pool with explicit concurrency limits per target.

**Mistake 4: URL deduplication by string equality alone**
`/user/1` and `/user/2` are the same endpoint for attack purposes. Fix: Use path pattern fingerprinting (`/user/{id}`) for deduplication, not just string comparison.

**Mistake 5: Forgetting to re-inject valid values for other parameters**
When testing `param_b`, you must provide valid values for `param_a`, `param_c`, etc. or the server may reject the request before it even hits the vulnerable parameter. Fix: Always carry `original_value` for all parameters and inject them alongside the attack payload.

**Mistake 6: Not establishing a response baseline before attacking**
Without a baseline, every 500 error looks like a vulnerability. Fix: Send 3-5 benign requests to each endpoint before attack phase. Record mean status code, response length, and response time.

**Mistake 7: Checking scope after making the request**
AI generators often check scope in post-processing. Fix: Scope enforcement must happen BEFORE any network connection is opened. Fail-closed on scope check errors.

**Mistake 8: Hardcoding User-Agent as `python-requests`**
Immediately blocked by most WAFs. Fix: Rotate through a pool of realistic browser User-Agent strings.

**Mistake 9: No retry logic on network errors**
One timeout kills the whole scan. Fix: Use `tenacity` with exponential backoff for all HTTP calls, with hard caps on retry count.

**Mistake 10: Forgetting CSRF token handling for POST forms**
AI generators send POST requests without extracting and including CSRF tokens. Fix: Before submitting any form, extract the CSRF token from the page, include it in the submission, and observe whether the server validates it (itself a finding).

### 12.2 Required User-Agent Pool

```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]
```

### 12.3 CSRF Token Extraction

```python
async def extract_csrf_token(page: Page) -> dict[str, str]:
    """Returns {field_name: token_value} for all detected CSRF tokens."""
    tokens = {}

    # Method 1: Hidden form inputs
    hidden_inputs = await page.evaluate("""
        () => {
            const result = {};
            document.querySelectorAll('input[type=hidden]').forEach(el => {
                if (/csrf|token|nonce|_wpnonce/i.test(el.name)) {
                    result[el.name] = el.value;
                }
            });
            return result;
        }
    """)
    tokens.update(hidden_inputs)

    # Method 2: Meta tags (common in Laravel, Rails, Django)
    meta_token = await page.evaluate("""
        () => {
            const meta = document.querySelector('meta[name="csrf-token"], meta[name="_token"]');
            return meta ? {[meta.getAttribute('name')]: meta.getAttribute('content')} : {};
        }
    """)
    tokens.update(meta_token)

    return tokens
```

### 12.4 OOB Callback Server Pattern

```python
class OOBServer:
    """
    Receives out-of-band callbacks for blind SSRF, XXE, CMDI verification.
    Must be reachable from the target server — deploy on internet-accessible host.
    """
    def __init__(self, domain: str, http_port: int = 8888, dns_port: int = 5353):
        self.domain = domain
        self._callbacks: dict[str, asyncio.Event] = {}
        self._received: dict[str, OOBCallback] = {}

    def generate_payload_token(self, scan_id: str, finding_id: str) -> str:
        """Generate unique subdomain token for this finding."""
        token = hashlib.sha256(f"{scan_id}{finding_id}{time.time()}".encode()).hexdigest()[:12]
        self._callbacks[token] = asyncio.Event()
        return token

    def get_http_url(self, token: str) -> str:
        return f"http://{token}.{self.domain}:{self.http_port}"

    def get_dns_hostname(self, token: str) -> str:
        return f"{token}.{self.domain}"

    async def wait_for_callback(self, token: str, timeout: float = 30.0) -> bool:
        """Returns True if callback was received within timeout."""
        event = self._callbacks.get(token)
        if not event:
            return False
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def on_http_callback(self, request: IncomingRequest):
        """Called by the HTTP server when a callback arrives."""
        token = self._extract_token(request.host)
        if token and token in self._callbacks:
            self._received[token] = OOBCallback(
                token=token,
                type="http",
                source_ip=request.client_ip,
                received_at=datetime.utcnow(),
                data=request.path,
            )
            self._callbacks[token].set()

    async def on_dns_callback(self, query: DNSQuery):
        """Called by the DNS server when a lookup arrives."""
        token = self._extract_token(query.name)
        if token and token in self._callbacks:
            self._received[token] = OOBCallback(
                token=token,
                type="dns",
                source_ip=query.source_ip,
                received_at=datetime.utcnow(),
                data=query.name,
            )
            self._callbacks[token].set()
```

---

## IMPLEMENTATION CHECKLIST

Before considering the engine production-ready, verify each item:

**Crawler:**
- [ ] Playwright headless Chromium with `networkidle` wait
- [ ] Session persistence across pages (storage_state)
- [ ] URL normalization + path pattern fingerprinting deduplication
- [ ] Scope enforcement BEFORE requests, fail-closed
- [ ] SPA route discovery via history API interception
- [ ] Network request log capturing all XHR/Fetch
- [ ] CSRF token extraction for form submissions

**Attack Engine:**
- [ ] Module self-registration via decorator
- [ ] Baseline established before any attack payloads
- [ ] Valid values injected for all non-targeted parameters
- [ ] Per-parameter location handling (URL, form, JSON, header, cookie)
- [ ] Rate limiter (token bucket) with hard caps
- [ ] Checkpoint/resume on crash

**Response Analysis:**
- [ ] Multi-layer analysis (error, reflection, status, length, timing)
- [ ] Noisy-OR confidence aggregation
- [ ] False positive filter (generic error pages, low-signal-only detections)
- [ ] 3-trial confirmation for timing-based findings

**Storage:**
- [ ] Findings deduplicated at INSERT level
- [ ] Request log partitioned by scan_id
- [ ] Response bodies truncated at 1MB
- [ ] All tables indexed for scan_id lookups

**Safety:**
- [ ] RFC1918 and metadata IP hard-block
- [ ] 429 exponential backoff
- [ ] Error-rate-triggered throttling
- [ ] Scan pause/abort with immediate effect on all workers
- [ ] Audit log for all scan start/stop/auth events

---

*This document covers engine implementation only. For architecture, UI, and deployment see companion documents.*
*FOR AUTHORIZED SECURITY RESEARCH USE ONLY.*
