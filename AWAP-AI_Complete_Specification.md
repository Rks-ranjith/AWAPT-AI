# AWAP-AI — Complete System Specification & Operational Guide
**AI-Driven Automated Web Application Penetration Testing System**  
Version 2.0 | For Authorized Security Research & Bug Bounty Use Only

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [How the Tool Works — End to End](#2-how-the-tool-works--end-to-end)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [Scan Phases — Detailed Breakdown](#4-scan-phases--detailed-breakdown)
5. [Attack Module Reference](#5-attack-module-reference)
6. [Payload Generation Engine](#6-payload-generation-engine)
7. [AI Integration Layer](#7-ai-integration-layer)
8. [Response Analysis Engine](#8-response-analysis-engine)
9. [Dashboard & UI Screens](#9-dashboard--ui-screens)
10. [Reporting System](#10-reporting-system)
11. [Bug Bounty Hunting Workflow](#11-bug-bounty-hunting-workflow)
12. [Scan Profiles Reference](#12-scan-profiles-reference)
13. [Configuration Reference](#13-configuration-reference)
14. [Security & Ethical Safeguards](#14-security--ethical-safeguards)
15. [DOs and DON'Ts](#15-dos-and-donts)
16. [Troubleshooting & Common Issues](#16-troubleshooting--common-issues)
17. [Vulnerability Reference — CVSS & CWE](#17-vulnerability-reference--cvss--cwe)
18. [Legal & Compliance](#18-legal--compliance)

---

## 1. System Overview

AWAP-AI is an autonomous web application penetration testing platform that combines classical security testing methodology with AI-powered analysis. It is designed for security researchers, bug bounty hunters, and red teamers who need to assess web application security at scale and with researcher-grade depth.

### What It Does

AWAP-AI automates the complete security assessment lifecycle:

```
Target URL → Reconnaissance → Crawling → Parameter Discovery
           → Attack Execution → AI Analysis → Prioritized Report
```

It does not replace a skilled human tester — it amplifies one. The tool handles the tedious, repetitive work (enumerating subdomains, fuzzing thousands of parameters, checking every endpoint for common misconfigurations) so the researcher can focus on manual exploitation of the findings it surfaces.

### What Makes It Different From Traditional Scanners

| Capability | Burp Suite / ZAP | AWAP-AI |
|---|---|---|
| SPA / JavaScript crawling | Limited | Full Playwright headless browser |
| Payload generation | Static wordlists | AI-generated context-aware payloads |
| Vulnerability classification | Pattern matching | ML classifier + LLM explanation |
| Attack chaining | Manual | Automated graph-based chain modeling |
| False positive reduction | Manual review | Behavioral confirmation engine |
| Reporting | Raw dump | CVSS-scored, remediation-guided |
| Bug bounty workflow | Manual | Integrated scope sync, auto-format submissions |

---

## 2. How the Tool Works — End to End

### Complete Scan Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SCAN LIFECYCLE                               │
│                                                                       │
│  1. USER INPUT                                                        │
│     └─ Enter target domain/URL                                        │
│     └─ Upload scope file (in-scope / out-of-scope domains)           │
│     └─ Confirm authorization (legally required)                       │
│     └─ Select scan profile (Quick / Standard / Full / Stealth)       │
│                                                                       │
│  2. RECONNAISSANCE  [automated, ~5-15 mins]                          │
│     └─ Subdomain enumeration via DNS + crt.sh                        │
│     └─ Technology fingerprinting (CMS, framework, server)            │
│     └─ WAF/CDN detection and identification                          │
│     └─ Port scanning on common web ports                             │
│     └─ Cloud asset discovery (S3 buckets, exposed storage)           │
│     └─ GitHub/GitLab secret scanning for target domain               │
│                                                                       │
│  3. CRAWLING & MAPPING  [automated, ~10-30 mins]                     │
│     └─ Playwright headless browser crawls all discovered URLs        │
│     └─ Authenticated crawl (if credentials provided)                 │
│     └─ JavaScript bundle analysis — extracts hidden API endpoints    │
│     └─ Form detection and input field enumeration                    │
│     └─ WebSocket, GraphQL, gRPC endpoint discovery                  │
│     └─ All endpoints scored for attack priority                      │
│                                                                       │
│  4. ATTACK EXECUTION  [automated, ~20-120 mins depending on scope]   │
│     └─ AI generates prioritized attack plan from endpoint map        │
│     └─ Each endpoint tested against relevant vulnerability modules   │
│     └─ Payloads sent at configured rate limit (default: 10 req/s)   │
│     └─ Every response analyzed by Response Analysis Engine           │
│     └─ Positive signals trigger adaptive payload refinement          │
│     └─ OOB callback server monitors for blind vulnerabilities        │
│                                                                       │
│  5. AI ANALYSIS  [automated, ~5-10 mins]                             │
│     └─ ML classifier assigns vuln class + confidence score           │
│     └─ LLM generates human-readable description + remediation        │
│     └─ Attack graph engine models finding relationships              │
│     └─ Exploit chains suggested (IDOR + XSS → account takeover)     │
│     └─ False positive review flags low-confidence findings           │
│                                                                       │
│  6. REPORTING  [automated, ~1-2 mins]                                │
│     └─ Findings sorted by CVSS score (highest first)                 │
│     └─ PoC evidence compiled (curl, Python snippet, Burp export)     │
│     └─ Executive summary generated                                   │
│     └─ Reports exported: PDF, JSON, CSV, Markdown                   │
└─────────────────────────────────────────────────────────────────────┘
```

### State Machine

The scan progresses through these states in order. Each state transition is logged with a timestamp.

```
CREATED → SCOPE_VERIFIED → RECON → CRAWL → MAPPING → ATTACK → ANALYSIS → REPORTING → COMPLETE
                                                                    ↓
                                                               PAUSED (user-initiated)
                                                                    ↓
                                                               ABORTED
                                                               FAILED (with error log)
```

---

## 3. Architecture Deep Dive

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWAP-AI PLATFORM                            │
│                                                                       │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────────────┐    │
│  │   Web UI    │   │  REST API    │   │     CLI / SDK         │    │
│  │  React/TW   │   │  FastAPI     │   │   Python Client       │    │
│  └──────┬──────┘   └──────┬───────┘   └───────────┬───────────┘    │
│         └─────────────────┼───────────────────────┘                 │
│                           ▼                                          │
│              ┌────────────────────────┐                             │
│              │    Scan Orchestrator   │                             │
│              │   FastAPI + Celery     │                             │
│              └──────────┬─────────────┘                             │
│                         │  Redis Streams (Task Bus)                 │
│         ┌───────────────┼────────────────────────┐                 │
│         ▼               ▼                ▼        ▼                 │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ ┌──────────────┐  │
│  │ Recon Engine│ │  Crawler    │ │   Attack   │ │  AI Decision │  │
│  │             │ │  Engine     │ │   Engine   │ │  Engine      │  │
│  └─────────────┘ └─────────────┘ └────────────┘ └──────────────┘  │
│         └───────────────┴────────────────────────┘                 │
│                           ▼                                          │
│              ┌────────────────────────┐                             │
│              │    Data Storage Layer  │                             │
│              │  PostgreSQL │ Redis    │                             │
│              └────────────────────────┘                             │
│                           ▼                                          │
│              ┌────────────────────────┐                             │
│              │   Report Generator    │                              │
│              │  PDF │ JSON │ CSV │ MD │                             │
│              └────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**Scan Orchestrator (FastAPI + Celery)**
- Receives scan requests from the UI/API
- Creates the scan record in PostgreSQL
- Dispatches the Celery task chain: recon → crawl → attack → analysis → report
- Manages scan state transitions and error recovery
- Exposes WebSocket endpoint for real-time dashboard updates

**Recon Engine**
- Enumerates subdomains using DNS brute-force and certificate transparency logs
- Fingerprints technology stack from HTTP headers, meta tags, and response patterns
- Detects WAF/CDN presence and identifies the vendor for bypass strategy selection
- Performs port scanning on common web ports using async TCP connect
- Stores all results in `recon_results` table with source attribution

**Crawler Engine (Playwright)**
- Launches a headless Chromium browser to execute JavaScript-heavy SPAs
- Intercepts all XHR/Fetch requests to harvest dynamic endpoints
- Handles authenticated flows: form login, OAuth, API key injection
- Parses JavaScript bundles to extract hardcoded API endpoints
- Enumerates all input parameters across all discovered endpoints

**Attack Engine**
- Loads attack modules from the registry and filters by scan profile
- Generates payloads via the Payload Generation Engine (static + AI-assisted)
- Dispatches HTTP requests through a rate-limited async request pool
- Streams responses to the Response Analysis Engine
- Sends confirmed findings to the AI Decision Engine for classification

**AI Decision Engine**
- Classifies findings using ML classifier (BERT fine-tuned on CVE/HackerOne data)
- Generates CVSS score estimates for each finding
- Calls LLM API (Claude/GPT-4) for natural language descriptions and remediation
- Builds attack graph modeling relationships between findings
- Applies false positive suppression before findings are written to the database

**Report Generator**
- Serializes all confirmed findings into the finding schema
- Generates PoC evidence (curl commands, Python snippets)
- Renders PDF, JSON, CSV, and Markdown reports
- Stores reports in object storage (MinIO/S3) with access links

---

## 4. Scan Phases — Detailed Breakdown

### Phase 1: Target Input & Scope Verification

**What happens:**
1. User submits a target (domain, IP range, or URL)
2. System normalizes to canonical form (strips trailing slashes, resolves CNAME)
3. Scope file is parsed — defines which domains/IPs are in-scope and out-of-scope
4. Authorization confirmation is presented and logged with timestamp + user ID
5. Target moves to `SCOPE_VERIFIED` state and enters the scan queue

**Scope file format:**
```
# In-scope
*.example.com
api.example.com
192.168.1.0/24

# Out-of-scope
admin.example.com  # explicitly excluded
*.third-party.com  # vendor infrastructure
```

**What can go wrong:**
- Domain doesn't resolve → scan won't start, error logged
- Scope file has conflicting rules → more specific rule wins
- Target is in RFC1918 private range → only allowed in lab mode (explicit flag required)

---

### Phase 2: Reconnaissance

**Subdomain Enumeration (runs in parallel):**

```
Source 1: DNS Brute-Force
  - Wordlist: 5,000 common subdomain prefixes
  - For each prefix: DNS A/AAAA lookup against target domain
  - Validated: must resolve to a real IP address
  - Rate: 500 DNS queries/second (async)

Source 2: Certificate Transparency (crt.sh)
  - Query: https://crt.sh/?q=%.{domain}&output=json
  - Extracts: all SANs from TLS certificates issued for the domain
  - Historical data: catches old subdomains still in use

Source 3: Wayback Machine
  - Query CDX API for all URLs ever indexed for the domain
  - Extracts unique hostnames from historical URLs
```

**Technology Fingerprinting:**

The engine sends a normal GET request and analyzes the response:

| Signal | What it reveals |
|---|---|
| `Server: nginx/1.18.0` | Web server version |
| `X-Powered-By: PHP/8.1` | Backend language |
| `Set-Cookie: laravel_session=` | Laravel framework |
| `<meta name="generator" content="WordPress 6.4">` | CMS version |
| `Cf-Ray:` header present | Behind Cloudflare |
| `X-Amz-Cf-Id:` header | AWS CloudFront CDN |

**WAF Detection:**

Sends a deliberately malicious probe and analyzes the block response:

```
Probe: GET /?q=<script>alert(1)</script>

If response contains:
  "Cloudflare Ray ID"           → Cloudflare WAF
  "mod_security"                → ModSecurity
  "Request blocked"             → Generic WAF
  "__CSRFP_TOKEN" in redirect   → Application-level protection
  
If no block → WAF absent or in detection-only mode
```

---

### Phase 3: Crawling & Mapping

**Playwright Crawl Flow:**

```
1. Launch headless Chromium (no-sandbox mode for Docker)
2. Create browser context with realistic user agent
3. Install request interceptor to harvest all XHR/Fetch URLs
4. Navigate to start URL, wait for networkidle
5. Extract all anchor links from DOM
6. Extract all form actions, methods, and input fields
7. Take screenshot for visual record
8. Follow in-scope links (respecting depth limit)
9. Repeat until max_pages reached or no new pages found
```

**JavaScript Bundle Analysis:**

After crawl, all linked `.js` files are downloaded and analyzed with regex patterns:

```python
PATTERNS = [
    r'["\'](/api/[^"\']+)["\']',          # /api/users endpoint
    r'axios\.get\(["\']([^"\']+)["\']',   # axios.get('/api/data')  
    r'fetch\(["\']([^"\']+)["\']',        # fetch('/api/endpoint')
    r'"baseURL":\s*["\']([^"\']+)["\']',  # Axios baseURL config
]
```

**Endpoint Priority Scoring:**

Every discovered endpoint receives a priority score (0-100) for attack ordering:

| Factor | Score adjustment |
|---|---|
| Has parameters | +30 |
| Parameters accept user-controlled input | +20 |
| Authenticated endpoint | +25 |
| API endpoint (/api/, /v1/, /graphql) | +20 |
| File upload endpoint | +40 |
| Admin interface | +35 |
| Returns sensitive data (email, PII patterns) | +15 |

High-scoring endpoints are attacked first.

---

### Phase 4: Attack Execution

**How Attack Modules Run:**

```
For each endpoint in priority-sorted endpoint list:
  For each vulnerability class relevant to this endpoint type:
    Load attack module
    Get baseline response (no payload)
    Generate payload set for this context
    For each payload:
      Send request (rate-limited)
      Compare response to baseline
      If anomaly detected:
        Flag as potential finding
        Trigger adaptive payload refinement
        After confirmation: write to findings table
        Broadcast to WebSocket for live dashboard update
```

**Rate Limiting:**

All outbound requests pass through a sliding window rate limiter:
- Default: 10 requests/second per target
- Burst protection: no more than 30 requests in any 3-second window
- Automatic backoff: if target returns HTTP 429, scan pauses for 60 seconds and resumes at half the previous rate
- Stealth mode: 1 req/s with randomized delays (0.5-3s) mimicking human browsing

**OOB (Out-of-Band) Callback Server:**

For blind vulnerabilities (blind SQLi, SSRF, XXE, blind command injection) where no in-band signal is visible, AWAP-AI uses OOB detection:

1. Each payload embeds a unique token: e.g., `{token}.oast.example.com`
2. If the server-side code executes the payload, it makes a DNS lookup or HTTP request to the OOB server
3. The OOB server receives the callback and matches the token to the originating scan/payload
4. This confirms the blind vulnerability even though the HTTP response shows nothing

---

## 5. Attack Module Reference

### Full Module Catalog

| Module | Severity | Detection Method | Bug Bounty Priority |
|---|---|---|---|
| `sqli_error` | CRITICAL | Database error string matching | ⭐⭐⭐ High |
| `sqli_blind_boolean` | CRITICAL | True/false condition response diff | ⭐⭐⭐ High |
| `sqli_time_based` | HIGH | Sleep/delay timing confirmation | ⭐⭐⭐ High |
| `sqli_oob` | CRITICAL | DNS/HTTP OOB callback | ⭐⭐⭐ High |
| `xss_reflected` | HIGH | Canary reflection in response body | ⭐⭐⭐ High |
| `xss_stored` | HIGH | Inject → retrieve confirmation | ⭐⭐⭐ High |
| `xss_dom` | HIGH | DOM sink analysis + browser execution | ⭐⭐ Medium |
| `cmd_injection` | CRITICAL | OS command output + OOB callback | ⭐⭐⭐ High |
| `ssrf_internal` | HIGH | Internal IP / cloud metadata response | ⭐⭐⭐ High |
| `ssrf_oob` | HIGH | DNS/HTTP OOB callback | ⭐⭐⭐ High |
| `xxe_classic` | HIGH | XML entity expansion + file read | ⭐⭐ Medium |
| `xxe_blind_oob` | HIGH | DNS/HTTP OOB entity reference | ⭐⭐ Medium |
| `ssti` | CRITICAL | Template expression evaluation | ⭐⭐⭐ High |
| `idor` | HIGH | Cross-account resource access diff | ⭐⭐⭐ High |
| `auth_brute` | HIGH | Rate-limit bypass + credential stuffing | ⭐⭐ Medium |
| `auth_bypass` | CRITICAL | JWT manipulation, session fixation | ⭐⭐⭐ High |
| `file_upload_rce` | CRITICAL | Polyglot upload + path traversal | ⭐⭐⭐ High |
| `path_traversal` | HIGH | Directory traversal + filter bypass | ⭐⭐ Medium |
| `http_smuggling` | HIGH | CL.TE / TE.CL desync probing | ⭐⭐ Medium |
| `cors_misconfig` | MEDIUM | Origin reflection + credentials test | ⭐⭐⭐ High |
| `deserialization` | CRITICAL | Gadget chain payload injection | ⭐⭐ Medium |
| `prototype_pollution` | HIGH | Node.js `__proto__` sink injection | ⭐⭐ Medium |
| `open_redirect` | MEDIUM | Redirect destination manipulation | ⭐⭐⭐ High |
| `csrf` | MEDIUM | Token absence + cross-origin form | ⭐⭐ Medium |
| `jwt_attacks` | HIGH | alg:none, weak secret, kid injection | ⭐⭐⭐ High |
| `security_headers` | INFO | Response header presence check | ⭐ Low |
| `tls_issues` | MEDIUM | Weak ciphers, expired certs | ⭐ Low |

### How Each Module Confirms Findings

**SQL Injection — Error Based:**
- Sends: `' OR '1'='1`, `"`, `1'--`, `1 AND SLEEP(5)--`
- Confirms: Response contains database error string AND differs from baseline
- Evidence: Error message + raw request/response pair

**XSS — Reflected:**
- Sends: Unique canary like `CANARY_abc123` wrapped in XSS payload
- Confirms: Canary appears unencoded in response HTML
- Evidence: Response body with canary highlighted + curl PoC

**SSRF:**
- Sends: `http://169.254.169.254/latest/meta-data/` as parameter value
- Confirms: Response body contains AWS metadata strings (`ami-id`, `instance-id`) OR OOB callback received
- Evidence: Response snippet with metadata or OOB callback log

**Open Redirect:**
- Sends: `https://evil.com` as `redirect`, `next`, `url`, `return` parameter values
- Confirms: Response is 3xx AND `Location` header points to `evil.com`
- Evidence: Response headers showing unvalidated redirect

**CORS Misconfiguration:**
- Sends: Request with `Origin: https://evil.com` header
- Confirms: Response has `Access-Control-Allow-Origin: https://evil.com` AND `Access-Control-Allow-Credentials: true`
- Evidence: Request/response headers pair showing unsafe CORS policy

---

## 6. Payload Generation Engine

### Generation Strategies (Applied in Order)

**1. Static Wordlist Baseline**

Foundation layer. Curated payload lists from:
- SecLists (community-maintained, 250k+ payloads)
- PayloadsAllTheThings (GitHub)
- AWAP-AI proprietary database (from public bug bounty disclosures)

Payloads are organized by vulnerability class and context.

**2. Mutation Engine**

Takes a seed payload and generates evasion variants:

```
Base payload: <script>alert(1)</script>

URL encoding:        %3Cscript%3Ealert%281%29%3C%2Fscript%3E
Double URL encoding: %253Cscript%253Ealert%25281%2529%253C%252Fscript%253E
HTML entity:         &#60;script&#62;alert(1)&#60;/script&#62;
Mixed case:          <sCrIpT>alert(1)</sCrIpT>
Null byte:           <script\x00>alert(1)</script>
Comment injection:   <scr/**/ipt>alert(1)</scr/**/ipt>
Unicode:             <\u0073cript>alert(1)</script>
```

**3. Context-Aware Generation**

Analyzes where the payload is injected and where it is reflected to generate the most appropriate payload:

| Injection Point | Reflection Context | Generated Payload Type |
|---|---|---|
| URL parameter | HTML attribute | `" onmouseover="alert(1)` |
| URL parameter | JavaScript string | `\'; alert(1); //` |
| JSON body | SQL query | `' OR 1=1--` |
| HTTP header | OS command | `; id; whoami` |
| XML body | XML attribute | `"><![CDATA[<script>]]>` |

**4. LLM-Assisted Generation**

When context-aware mutations are insufficient (custom WAF, non-standard application logic), the engine queries Claude API:

```
Prompt: 
"You are a web security expert.
Generate 10 WAF bypass payloads for XSS injection.
Injection context: URL parameter reflected in HTML attribute value.
WAF: Cloudflare (blocking patterns: <script>, javascript:, onerror=)
Return only a JSON array of strings."

Response: [
  "\" onfocus=\"alert`1`\" autofocus=\"",
  "\"><details open ontoggle=alert(1)>",
  ...
]
```

**5. Adaptive Payload Refinement**

After each payload attempt, the response signal feeds a bandit algorithm:
- WAF block (HTTP 403 with block page) → payload was detected → negative signal
- Length change / error in response → partial hit → positive signal, generate variants
- Identical to baseline → no effect → skip this class for this endpoint

Over a scan session, the engine converges on the highest-yield payloads for the specific target.

### Payload Encoding Reference

| Encoding | Applied When | Example |
|---|---|---|
| URL Encode | URL parameters, path segments | `<` → `%3C` |
| Double URL Encode | WAF bypass | `<` → `%253C` |
| HTML Entity | HTML body reflection | `<` → `&lt;` |
| Unicode Escape | JavaScript string context | `<` → `\u003c` |
| SQL Hex | SQL injection context | `admin` → `0x61646d696e` |
| Base64 | Encoded parameter values | `payload` → `cGF5bG9hZA==` |
| Null Byte | File path contexts | `file.php\x00.jpg` |

---

## 7. AI Integration Layer

### How AI Is Used at Each Stage

**Stage: Payload Generation**
- Model: Claude API (`claude-opus-4-6`)
- Input: injection context, technology stack, WAF signatures, blocked patterns
- Output: 10 novel bypass payloads ranked by estimated effectiveness
- When triggered: after static mutations are exhausted or consistently blocked

**Stage: Vulnerability Classification**
- Model: BERT fine-tuned on CVE descriptions + HackerOne public reports
- Input: URL, parameter, payload, evidence string, response snippet
- Output: vulnerability class, CVSS score estimate, confidence (0-1)
- Fallback: if classifier confidence < 0.6, flag for human review

**Stage: Finding Explanation**
- Model: Claude API
- Input: classified finding with all evidence
- Output: 2-3 sentence technical description, specific remediation steps for detected technology
- Format: structured JSON `{description, remediation, code_example, references}`

**Stage: Attack Graph Construction**
- Model: Rule-based graph engine (GNN planned for v2)
- Input: all findings from current scan
- Output: directed graph of exploitation relationships
- Example chain detected: `IDOR (user profile API) → Stored XSS (profile field) → CSRF (admin action) → Account Takeover`

**Stage: False Positive Suppression**
- Model: Random Forest classifier trained on confirmed vs. false positive historical findings
- Input: all signals from Response Analysis Engine
- Output: false positive probability (0-1)
- Threshold: findings with FP probability > 0.7 are flagged for human review, not auto-reported

### Confidence Scoring

Every finding has a confidence score (0.0 to 1.0):

| Score | Meaning | Action |
|---|---|---|
| 0.9 - 1.0 | Confirmed — deterministic evidence | Auto-reported with CRITICAL/HIGH severity |
| 0.7 - 0.9 | High confidence — strong signals | Reported, marked as likely confirmed |
| 0.5 - 0.7 | Medium confidence — some signals | Reported, flagged for manual review |
| 0.0 - 0.5 | Low confidence | Not reported, logged for analyst review |

---

## 8. Response Analysis Engine

### Analysis Layers

Every HTTP response is processed through all six layers:

**Layer 1: Error Pattern Recognition**

Regex library of 500+ error signatures organized by technology:

```
SQL Errors:
  - "you have an error in your sql syntax" → MySQL
  - "pg::syntaxerror" → PostgreSQL
  - "ora-01756" → Oracle
  - "unclosed quotation mark" → MSSQL

Framework Errors:
  - "templatenotfound" → Jinja2/Flask
  - "phpfatalerror" → PHP
  - "javax.servlet.servletexception" → Java
  - "syntaxerror: unexpected token" → Node.js

File Inclusion:
  - "include(): failed to open stream" → PHP LFI
  - "warning: include" → PHP path disclosure
```

**Layer 2: Response Structure Anomaly**

Statistical baseline established over 5-10 clean requests before attack:

| Signal | Threshold | What it indicates |
|---|---|---|
| Content-Length delta | >10% from baseline | Potential data disclosure or injection |
| HTTP status change | Any change | Access control change, redirection |
| Response time | >2 standard deviations | Time-based blind injection |
| Content-Type change | Any change | Server-side execution, file disclosure |
| New Set-Cookie header | Appearance | Session state manipulation |

**Layer 3: Reflection Detection**

Unique canary strings embedded in payloads, searched in response in multiple encodings:

```
Canary: AWAPCANARY_7a3b9f

Direct reflection:     AWAPCANARY_7a3b9f       → XSS context (unencoded)
URL decoded:           AWAPCANARY_7a3b9f       → URL-encoded reflection
HTML decoded:          AWAPCANARY_7a3b9f       → HTML entity reflection
JS decoded:            AWAPCANARY_7a3b9f       → JS string escape context
Partial reflection:    AWAPCANARY              → Filtered reflection (truncated)
```

**Layer 4: Behavioral Analysis**

Application state changes induced by attack payloads:
- Did authentication state change? (session cookie appeared/disappeared)
- Did server make outbound request? (SSRF via OOB callback)
- Did payload create a detectable object? (stored XSS, file upload)
- Did redirect behavior change? (open redirect confirmed)

**Layer 5: Timing Analysis**

For time-based blind attacks:
- 3-trial statistical confirmation (reduces network jitter false positives)
- Threshold: response time > (baseline mean + 4 seconds) for SLEEP(5) payloads
- Network jitter compensation: adjusts threshold based on observed latency variance

**Layer 6: OOB Callback Analysis**

- Every payload embedding a callback token is tracked
- DNS lookup received → confirms server-side execution
- HTTP request received → confirms SSRF/XXE/blind injection
- Correlation: token → scan_id → endpoint → payload → confirms specific vulnerability

---

## 9. Dashboard & UI Screens

### Screen 1: Main Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  AWAP-AI                        ● 3 Active  ▲ System OK    │
├──────────────────────────────────────────────────────────────┤
│  CRITICAL: 12  HIGH: 34  MEDIUM: 67  LOW: 45  INFO: 23     │
├──────────┬───────────────────────────────────────────────────┤
│ Dashboard│  Live Scan Activity                               │
│ Targets  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ Scans    │  [CRITICAL] SQLi in /api/users?id= - example.com │
│ Findings │  [HIGH] Reflected XSS - api.example.com/search   │
│ Reports  │  [HIGH] SSRF via redirect param - example.com    │
│ Analytics│                                                   │
│ Settings │  Recent Findings ─────────────────────────────── │
│          │  Target           Severity  Type       CVSS      │
│          │  example.com      CRITICAL  SQLi       9.8       │
│          │  api.example.com  HIGH      XSS        7.2       │
└──────────┴───────────────────────────────────────────────────┘
```

**Color coding:**
- 🔴 Red = CRITICAL (CVSS 9.0-10.0)
- 🟠 Orange = HIGH (CVSS 7.0-8.9)
- 🟡 Yellow = MEDIUM (CVSS 4.0-6.9)
- 🔵 Blue = LOW (CVSS 0.1-3.9)
- ⚪ Gray = INFO

### Screen 2: Live Scan Monitor

Real-time view of an active scan:

```
example.com  ●  ATTACK PHASE  ━━━━━━━━━━━━━━━━━━░░░░  68%

Phase: ▓ RECON ▓ CRAWL ▓ MAPPING ▓ ATTACK ░ ANALYSIS ░ REPORT

Live Request Stream:
  200  GET  /api/users?id=1'         15ms  → Analyzing...
  500  GET  /api/users?id=1"         23ms  → SQL ERROR DETECTED ⚠
  200  GET  /search?q=<script>       12ms  → Reflected ✓

New Finding ──────────────────────────────────────────────────
  ⚠ CRITICAL  SQL Injection  /api/users  param: id  CVSS: 9.8

Attack Graph:
  [/api/users SQLi] ──→ [Auth bypass possible] ──→ [Admin access]

Controls: [Pause] [Abort] [Adjust Rate ▼]
```

### Screen 3: Finding Detail

```
┌───────────────────────────────────────────────────────────────┐
│  ⚠ CRITICAL  SQL Injection  CVSS: 9.8  CWE-89               │
├───────────────────────────────────────────────────────────────┤
│  URL: https://example.com/api/users                          │
│  Method: GET  Parameter: id  Type: URL parameter             │
│  Discovered: 2025-01-15 14:23:07 UTC                         │
├───────────────────────────────────────────────────────────────┤
│  EVIDENCE                                                     │
│                                                               │
│  Request:                                                     │
│  GET /api/users?id=1' HTTP/1.1                               │
│  Host: example.com                                            │
│                                                               │
│  Response (excerpt):                                          │
│  You have an error in your SQL syntax near "1'" at line 1   │
├───────────────────────────────────────────────────────────────┤
│  PROOF OF CONCEPT                                             │
│  curl -s "https://example.com/api/users?id=1'"              │
│                                                               │
│  [Copy curl] [Open in Burp] [Download .py PoC]              │
├───────────────────────────────────────────────────────────────┤
│  REMEDIATION                                                  │
│  Use parameterized queries (prepared statements). In PHP:    │
│  $stmt = $pdo->prepare("SELECT * FROM users WHERE id = ?"); │
│  $stmt->execute([$id]);                                       │
│                                                               │
│  Reference: OWASP SQL Injection Prevention Cheat Sheet       │
├───────────────────────────────────────────────────────────────┤
│  [Mark Confirmed] [False Positive] [Accept Risk] [Assign]   │
└───────────────────────────────────────────────────────────────┘
```

---

## 10. Reporting System

### Finding Schema (Complete)

Every finding stored in the database and included in reports contains:

```json
{
  "finding_id": "uuid",
  "scan_id": "uuid",
  "target": {
    "domain": "example.com",
    "ip": "1.2.3.4",
    "port": 443
  },
  "vulnerability": {
    "class": "SQL_INJECTION",
    "name": "Error-Based SQL Injection in user ID parameter",
    "description": "LLM-generated technical description",
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "cvss_score": 9.8,
    "cvss_severity": "CRITICAL",
    "cwe_id": "CWE-89",
    "owasp_category": "A03:2021 Injection"
  },
  "affected": {
    "endpoint": "https://example.com/api/users",
    "method": "GET",
    "parameter": "id",
    "parameter_type": "URL_PARAM"
  },
  "evidence": {
    "payload": "1'",
    "request_raw": "GET /api/users?id=1' HTTP/1.1\nHost: example.com",
    "response_raw": "HTTP/1.1 500\n...",
    "poc_curl": "curl -s 'https://example.com/api/users?id=1%27'",
    "poc_python": "import requests\nr = requests.get('https://example.com/api/users', params={'id': \"1'\"})"
  },
  "remediation": {
    "summary": "Use parameterized queries to separate SQL code from user input",
    "code_example": "$stmt = $pdo->prepare('SELECT * FROM users WHERE id = ?'); $stmt->execute([$id]);",
    "references": [
      "https://owasp.org/www-community/attacks/SQL_Injection",
      "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
    ]
  },
  "metadata": {
    "discovered_at": "2025-01-15T14:23:07Z",
    "confidence": 0.98,
    "false_positive": false,
    "status": "CONFIRMED"
  }
}
```

### Report Templates

| Template | Audience | Content |
|---|---|---|
| **Executive Summary** | CISO, Management | Business risk, financial exposure, severity distribution, trending |
| **Technical Report** | Security Engineers | Full findings with evidence, PoC, raw requests/responses |
| **Developer Remediation** | Dev Teams | Code-level fixes, stack-specific examples, priority queue |
| **Compliance Report** | Auditors | Control mappings to PCI-DSS, SOC 2, HIPAA, ISO 27001 |
| **Differential Report** | Repeat Assessments | New findings vs. previous scan, fixed vs. regressed |
| **Bug Bounty Submission** | HackerOne/Bugcrowd | Pre-formatted submission with CVSS, CWE, PoC |

---

## 11. Bug Bounty Hunting Workflow

### Recommended Workflow for Bug Bounty Programs

**Step 1: Program Selection**
1. Pick a target from HackerOne or Bugcrowd with a broad scope (`*.example.com`)
2. Carefully read the program policy — note out-of-scope assets, restricted test types, and severity eligibility
3. Import program scope directly into AWAP-AI (HackerOne API integration auto-syncs scope)

**Step 2: Initial Recon (AWAP-AI Automated)**
1. Add the program's root domain as the target
2. Run **Standard scan profile** to get an initial attack surface map
3. Review the recon results — look for:
   - Subdomains you didn't know existed
   - Old/staging environments (`staging.`, `dev.`, `test.`, `beta.`)
   - Cloud assets (misconfigured S3 buckets are often in scope and high-value)
   - Technology stack — older versions of frameworks have known CVEs

**Step 3: Authenticated Scan**
1. Create an account on the target application
2. Provide session cookies or login credentials to AWAP-AI
3. Run **Authenticated scan profile** — this tests the post-login attack surface which is often much larger and more interesting

**Step 4: Review Findings**
1. Sort findings by CVSS score — investigate CRITICAL and HIGH first
2. For each finding, manually verify the PoC curl command works
3. Check if the finding is in-scope for the program (use the scope checker)
4. Assess business impact beyond the raw CVSS (does this affect payment data? PII? admin accounts?)

**Step 5: Finding Prioritization for Submission**

Focus on these vulnerability types first for bug bounty — they typically receive the highest payouts and acceptance rates:

| Priority | Vulnerability | Why |
|---|---|---|
| 1 | Account Takeover (ATO) | Highest business impact, guaranteed payout |
| 2 | SSRF to internal systems | Often leads to cloud metadata → credentials |
| 3 | SQL Injection | Data exfiltration risk, regulatory impact |
| 4 | Authentication bypass | Immediate access control violation |
| 5 | Stored XSS in authenticated areas | ATO chain potential |
| 6 | IDOR on sensitive resources | Privacy violation, data exposure |
| 7 | CORS + stored XSS chain | ATO via cross-origin attack |
| 8 | Open Redirect | Often accepted, especially on OAuth flows |

**Step 6: Report Writing**
1. Use AWAP-AI's **Bug Bounty Submission** report template
2. Export as Markdown (most platforms support it)
3. Before submission, manually verify:
   - The vulnerability is reproducible right now
   - The PoC steps work exactly as written
   - No sensitive data was exfiltrated or modified during testing
   - The finding is within scope

**What Makes a Good Bug Bounty Report:**
- Clear title: `[CRITICAL] Unauthenticated SQLi in /api/v2/users?id= leading to database dump`
- CVSS vector string with justification
- Step-by-step reproduction steps that work on the first try
- Request/response evidence (sanitized — remove your session token, replace PII)
- Impact statement explaining what an attacker could do, not just what the vulnerability is
- Suggested fix (optional but appreciated)

---

## 12. Scan Profiles Reference

| Profile | Rate | Depth | Modules | Best For |
|---|---|---|---|---|
| **Quick** | 20 req/s | Shallow | Critical modules only | Initial triage, CI/CD gate |
| **Standard** | 10 req/s | Medium | High severity+ modules | Regular assessments |
| **Full** | 5 req/s | Deep | All modules | Full penetration test |
| **API Only** | 15 req/s | API-focused | API-specific modules | REST/GraphQL API testing |
| **Stealth** | 1 req/s | Deep | All modules | WAF evasion, sensitive targets |
| **Authenticated** | 10 req/s | Deep | All modules | Post-login attack surface |

### Choosing the Right Profile

- **New target, unknown scope** → Start with Quick to get an overview without noise
- **Bug bounty program target** → Standard first, then Authenticated for logged-in testing
- **Pre-engagement in a pentest** → Full scan with Authenticated profile
- **Target has aggressive WAF/rate limiting** → Stealth profile
- **API-only target (mobile app backend)** → API Only profile
- **CI/CD pipeline integration** → Quick profile with critical-only modules

---

## 13. Configuration Reference

### Environment Variables

| Variable | Required | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://awap:pass@localhost:5432/awap` |
| `REDIS_URL` | Yes | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | Yes | JWT signing key (32+ chars) | `openssl rand -hex 32` |
| `LLM_PROVIDER` | Yes | AI provider: `anthropic` or `openai` | `anthropic` |
| `LLM_API_KEY` | Yes | API key for LLM provider | `sk-ant-...` |
| `OAST_SERVER` | Recommended | OOB callback server URL | `https://your-oast.example.com` |
| `SHODAN_API_KEY` | Optional | Shodan OSINT integration | `abc123...` |
| `MINIO_ENDPOINT` | Optional | Object storage for reports | `http://minio:9000` |
| `DEFAULT_RATE_LIMIT` | Optional | Default req/s per target | `10` |
| `MAX_CONCURRENT_SCANS` | Optional | Parallel scan limit | `5` |

### Scan Configuration (per scan)

```json
{
  "profile": "standard",
  "rate_limit": 10,
  "max_pages": 200,
  "max_depth": 5,
  "max_concurrent_requests": 10,
  "attack_modules": ["all"],
  "excluded_modules": ["auth_brute"],
  "session_cookies": {},
  "custom_headers": {},
  "follow_redirects": true,
  "verify_ssl": false,
  "stealth_mode": false,
  "oob_enabled": true,
  "ai_payload_generation": true,
  "ai_classification": true
}
```

---

## 14. Security & Ethical Safeguards

### Non-Optional Hardcoded Constraints

These safeguards cannot be disabled by any user, regardless of permissions:

**1. Authorization Requirement**
- No scan can start without `authorized = true` in the target record
- Authorization confirmation must be logged with timestamp, user ID, and target domain
- Log entries are append-only — they cannot be modified or deleted

**2. Scope Enforcement**
- Every outbound request URL is validated against the target's scope rules before being sent
- If a crawled link falls outside scope, it is recorded but never fetched
- If subdomain enumeration discovers an asset outside the defined wildcard, it is logged but not scanned

**3. Rate Limiting**
- Global floor: minimum 1 request per second (cannot go faster than 50 req/s even in Quick profile)
- Automatic 429 backoff: on receiving HTTP 429, scan automatically throttles and waits
- Business hours mode (optional): restricts scanning to configured off-peak windows

**4. Destructive Operation Protection**
- Read-only mode by default: no POST/PUT/DELETE requests unless explicitly enabled per scan
- SQL injection probes prefer SELECT-based probes over DROP/DELETE
- File upload test files use unique canary names and are attempted for deletion after testing
- DoS payload blocklist: billion laughs, regex ReDoS, recursive XXE, and other DoS payloads are permanently blocked

**5. Data Protection**
- Scan data encrypted at rest (AES-256)
- All communication encrypted in transit (TLS 1.3 minimum)
- Sensitive parameter values (passwords, tokens) are redacted in all logs
- Evidence data stored in tenant-isolated storage

**6. Private Range Protection**
- Scanning of RFC1918 ranges (10.x, 172.16-31.x, 192.168.x) requires explicit `lab_mode=true` flag
- Lab mode requires a separate configuration file confirming isolated environment
- Cloud metadata endpoints (169.254.169.254) are only probed as SSRF payloads against the external target, never directly

---

## 15. DOs and DON'Ts

### ✅ DOs

**Authorization & Scope**
- DO get explicit written authorization (email confirmation, signed rules of engagement, or bug bounty program acceptance) before scanning any target
- DO import scope from HackerOne/Bugcrowd API to ensure scope rules are always current
- DO set conservative rate limits when testing production systems
- DO test against intentionally vulnerable apps (DVWA, WebGoat, Juice Shop, HackTheBox, TryHackMe) to learn the tool's capabilities

**Scanning Strategy**
- DO start with Quick profile and review findings before running Full profile
- DO always run Authenticated scans — the post-login attack surface is where the interesting bugs live
- DO configure out-of-scope exclusions carefully — one mis-scan of an out-of-scope asset can get you banned from a bug bounty program
- DO use Stealth profile on targets with aggressive WAF/rate limiting
- DO provide credentials for multi-role testing (regular user AND admin if accessible)

**Findings & Reporting**
- DO manually verify every CRITICAL/HIGH finding before reporting — run the curl PoC yourself
- DO check whether findings represent the same root cause (deduplicate before submitting)
- DO include full reproduction steps, evidence, and impact assessment in bug bounty submissions
- DO use the differential report when re-scanning a target to find new issues and verify fixes
- DO store reports securely — they contain sensitive vulnerability details

**Operations**
- DO run the health check (`GET /api/health`) before starting a scan session
- DO monitor the Celery dashboard (Flower) during long scans to catch stuck tasks
- DO set up alerting for CRITICAL findings (Slack/Discord webhook integration)
- DO test the platform against DVWA regularly to ensure modules are working

---

### ❌ DON'Ts

**Authorization & Legal**
- DON'T scan any target without explicit written authorization — period
- DON'T scan production systems with Full profile or high rate limits without a maintenance window
- DON'T test systems that are not explicitly listed in a bug bounty program's scope
- DON'T exfiltrate or retain actual sensitive data discovered during testing (user PII, credentials)
- DON'T share scan reports containing vulnerability details with unauthorized parties
- DON'T use AWAP-AI for competitive intelligence, scraping, or any non-security purpose

**Technical Operations**
- DON'T run auth brute-force modules against accounts that aren't test accounts you control
- DON'T enable write operations (POST/PUT/DELETE) on production systems without explicit permission and a rollback plan
- DON'T set rate limits higher than 10 req/s on production targets without the target owner's confirmation
- DON'T ignore rate limit warnings — sustained scanning that impacts availability can be treated as a DoS attack
- DON'T scan from shared IP addresses (VPN exit nodes, Tor) — findings will be hard to attribute and defend
- DON'T run multiple concurrent full scans on the same target simultaneously

**Finding Handling**
- DON'T report low-confidence findings to bug bounty programs without manual verification — false positives destroy your reputation
- DON'T report duplicate findings (check the program's existing submissions first)
- DON'T publicly disclose vulnerabilities before the program's disclosure timeline (typically 90 days)
- DON'T modify or delete application data to "prove" a finding is exploitable
- DON'T chain vulnerabilities into an actual account takeover or data breach to escalate a report — demonstrate impact safely

**Tool Operation**
- DON'T run AWAP-AI on shared infrastructure without tenant isolation
- DON'T store API keys or LLM credentials in the codebase — use environment variables
- DON'T ignore the scan logs — failed tasks silently skipping attack modules means incomplete coverage
- DON'T disable the scope enforcement safeguards — they exist to protect you legally

---

## 16. Troubleshooting & Common Issues

### Scan Never Leaves CREATED State

**Cause:** Celery worker not running or not consuming tasks

**Diagnosis:**
```bash
docker-compose logs worker  # Check for errors
curl http://localhost:5555  # Flower dashboard should show workers
curl http://localhost:8000/api/health  # Check celery status
```

**Fix:** Restart the worker container. Verify Redis is accessible from the worker container. Check for import errors in task modules.

---

### Recon Returns No Subdomains

**Cause:** DNS queries timing out, crt.sh API rate limited, or domain has no subdomains

**Diagnosis:**
```bash
# Test DNS from inside the container
docker-compose exec worker python -c "import dns.resolver; print(dns.resolver.resolve('example.com', 'A'))"

# Test crt.sh API
curl "https://crt.sh/?q=%.example.com&output=json"
```

**Fix:** Check network egress from the worker container. Add DNS fallback servers (8.8.8.8, 1.1.1.1) to the resolver configuration. For crt.sh rate limiting, add exponential backoff retry.

---

### Playwright Crashes or Times Out

**Cause:** Chromium not installed in the container, or missing system dependencies

**Fix:** Ensure the Dockerfile includes:
```dockerfile
RUN pip install playwright==1.40.0
RUN playwright install chromium --with-deps
```

And the scan worker is launched with:
```bash
--args='["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]'
```

---

### WebSocket Connection Drops Immediately

**Cause:** Reverse proxy (Nginx/Traefik) not configured for WebSocket upgrade

**Fix:** Add to Nginx config:
```nginx
location /ws/ {
    proxy_pass http://api:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

---

### No Findings on a Known-Vulnerable Target

**Cause:** Attack modules not running (Celery task chain breaking), payloads being blocked by WAF, or wrong scan profile

**Diagnosis:**
1. Check `scan_logs` table for errors during attack phase
2. Check `endpoints` table — were endpoints discovered?
3. Run against DVWA first to confirm modules work
4. Try Stealth profile if WAF is blocking payloads

---

### LLM API Calls Failing

**Cause:** Invalid API key, rate limit exceeded, or network egress blocked

**Diagnosis:**
```bash
docker-compose exec worker python -c "
import anthropic
client = anthropic.Anthropic(api_key='YOUR_KEY')
msg = client.messages.create(model='claude-opus-4-6', max_tokens=10, messages=[{'role':'user','content':'hi'}])
print(msg)
"
```

**Fix:** Verify `LLM_API_KEY` environment variable is set. Check Anthropic API status. Implement retry with exponential backoff for rate limit errors (HTTP 429).

---

## 17. Vulnerability Reference — CVSS & CWE

### CVSS 3.1 Score Reference

| Score | Severity | Priority | SLA |
|---|---|---|---|
| 9.0 - 10.0 | CRITICAL | P0 | Immediate (4 hours) |
| 7.0 - 8.9 | HIGH | P1 | Same day (24 hours) |
| 4.0 - 6.9 | MEDIUM | P2 | Sprint (72 hours) |
| 0.1 - 3.9 | LOW | P3 | Backlog (2 weeks) |
| 0.0 | INFO | P4 | Documentation |

### Vulnerability Class → CWE → OWASP 2021 Mapping

| Vulnerability | CWE | OWASP 2021 | Typical CVSS |
|---|---|---|---|
| SQL Injection | CWE-89 | A03 Injection | 9.8 CRITICAL |
| Command Injection | CWE-78 | A03 Injection | 9.8 CRITICAL |
| SSTI | CWE-1336 | A03 Injection | 9.8 CRITICAL |
| Deserialization | CWE-502 | A08 | 9.8 CRITICAL |
| Auth Bypass | CWE-287 | A07 Auth Failures | 8.1 HIGH |
| SSRF | CWE-918 | A10 SSRF | 8.6 HIGH |
| HTTP Smuggling | CWE-444 | A07 | 8.1 HIGH |
| XXE | CWE-611 | A05 Misconfig | 7.5 HIGH |
| Path Traversal | CWE-22 | A01 Access Control | 7.5 HIGH |
| JWT Attacks | CWE-287 | A07 Auth Failures | 7.5 HIGH |
| XSS (Stored) | CWE-79 | A03 Injection | 6.1 MEDIUM |
| IDOR | CWE-284 | A01 Access Control | 6.5 MEDIUM |
| CORS Misconfig | CWE-942 | A05 Misconfig | 6.5 MEDIUM |
| Open Redirect | CWE-601 | A01 Access Control | 6.1 MEDIUM |
| CSRF | CWE-352 | A01 Access Control | 6.5 MEDIUM |
| XSS (Reflected) | CWE-79 | A03 Injection | 6.1 MEDIUM |
| Security Headers | CWE-693 | A05 Misconfig | 3.7 LOW |
| TLS Issues | CWE-326 | A02 Crypto Failures | 3.7 LOW |

---

## 18. Legal & Compliance

### Mandatory Legal Requirements

**Before any scan:**
1. You MUST have explicit written authorization from the system owner
2. Authorization must specify: the IP range/domain, the testing methods permitted, the testing window, and the responsible party
3. Bug bounty programs: program participation and program scope acceptance constitutes authorization only for listed in-scope assets
4. All authorization records are maintained in AWAP-AI's audit log permanently

**Relevant Laws:**
- United States: Computer Fraud and Abuse Act (CFAA) — unauthorized access is a federal crime
- United Kingdom: Computer Misuse Act (CMA) — unauthorized access carries up to 10 years imprisonment
- European Union: NIS2 Directive, national cybercrime laws in each member state
- India: Information Technology Act 2000, Section 66 — unauthorized access carries up to 3 years imprisonment

**The platform maintains:**
- Full audit log of all targets added (who, when, what)
- All authorization confirmations with timestamp and user ID
- All scan activity (every request URL logged at DEBUG level)
- All findings (immutable, append-only)

These logs cannot be disabled and cannot be deleted by end users.

### Responsible Disclosure

When findings are discovered through authorized testing:

1. **Critical/High findings** affecting user safety: notify the vendor within 24 hours
2. **Standard disclosure timeline**: 90 days from notification to public disclosure (follow the program's policy)
3. **No public disclosure** before the vendor acknowledges and addresses the finding, unless the timeline expires
4. **Coordinated disclosure**: work with the vendor or bug bounty program to agree on disclosure timing
5. **Data handling**: any user data accessed during testing must not be retained, shared, or used for any purpose

### Bug Bounty Specific

- Submitting findings to HackerOne, Bugcrowd, or similar platforms constitutes disclosure to the program
- Follow each program's specific rules for disclosure timelines, duplicate handling, and severity classification
- Some programs have explicit rules against automated scanning — check the program policy before using AWAP-AI
- AWAP-AI's scope enforcement integrates with HackerOne/Bugcrowd API to auto-enforce program scope

---

*AWAP-AI is a professional security research tool. Use it only on systems you are authorized to test. The authors accept no liability for unauthorized or illegal use.*

*For authorized security research use only.*
