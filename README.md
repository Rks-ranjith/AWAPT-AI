# AWAP-AI — AI-Driven Automated Web Application Penetration Testing System

> **FOR AUTHORIZED SECURITY RESEARCH USE ONLY**
> This system must only be used against targets explicitly authorized for security testing.
> Unauthorized use is illegal under CFAA, CMA, and equivalent statutes globally.

---

## What This Is

AWAP-AI is a full-stack autonomous web application penetration testing platform. It combines classical pentesting methodology (PTES + OWASP Testing Guide) with an AI layer that reasons about attack paths, generates context-aware payloads, classifies vulnerabilities, and produces professional reports — without manual intervention between phases.

The design philosophy: **simulate the complete cognitive workflow of an expert bug bounty researcher** — not just "scan and report" but "think, hypothesize, probe, and chain."

---

## Tech Stack

### Backend
- **Python 3.11+** — FastAPI (async REST API)
- **Celery + Redis Streams** — distributed task queue + inter-service message bus
- **Playwright** — headless Chromium for SPA crawling + authenticated sessions
- **HTTPX** — async HTTP client for all scan requests
- **SQLAlchemy + Alembic** — ORM + migrations
- **PostgreSQL 16** — primary data store (targets, scans, findings, endpoints)
- **Redis 7** — task queues, session cache, rate limit counters
- **MinIO (S3-compatible)** — object storage for screenshots, evidence, reports

### AI / ML
- **HuggingFace Transformers** — BERT fine-tuned on CVE + HackerOne data for vuln classification
- **PyTorch** — LSTM for response timing/sequence anomaly detection
- **scikit-learn** — Isolation Forest (anomaly detection), Random Forest (false positive reduction)
- **DGL (Deep Graph Library)** — Graph Neural Network for attack chain modeling
- **FAISS** — vector similarity search for finding deduplication
- **Stable-Baselines3** — Thompson Sampling bandit for adaptive scan prioritization
- **Anthropic Claude API / OpenAI GPT-4** — payload generation + natural language report writing

### Frontend
- **React 18 + TypeScript**
- **Tailwind CSS** — dark SOC-aesthetic UI, high information density
- **Zustand + React Query** — global state + API caching
- **Recharts + D3.js** — scan metrics, severity charts
- **Cytoscape.js** — attack graph visualization
- **WebSocket (native)** — live scan progress streaming
- **Prism.js** — syntax highlighting for HTTP evidence + PoC code

### Infrastructure
- **Docker Compose** (local dev) / **Kubernetes + Helm** (production)
- **Traefik / Nginx** — reverse proxy + TLS termination
- **Prometheus + Grafana** — platform metrics
- **Loki** — log aggregation
- **GitHub Actions** — CI/CD

---

## Repository Structure

```
awap-ai/
├── backend/
│   ├── awap/
│   │   ├── api/           # FastAPI routes, schemas, dependencies
│   │   ├── core/          # Config, database, security, celery
│   │   ├── engines/
│   │   │   ├── recon/     # Subdomain enum, OSINT, fingerprinting
│   │   │   ├── crawler/   # Playwright crawler, JS analyzer, param discovery
│   │   │   ├── attack/    # Attack orchestrator, module runner
│   │   │   ├── response/  # Response analysis engine (RAE)
│   │   │   └── ai/        # AI decision engine, classifier, attack graph
│   │   ├── modules/       # Individual attack modules (one file per vuln class)
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── payloads/      # Payload databases + generation engine
│   │   └── reporting/     # PDF/DOCX/JSON/Markdown report generation
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/           # Tests against DVWA / Juice Shop
│   ├── alembic/           # DB migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/         # Dashboard, Targets, LiveScan, Findings, Reports, Analytics
│   │   ├── hooks/
│   │   ├── store/         # Zustand stores
│   │   └── api/           # Axios API client
│   ├── Dockerfile
│   └── package.json
├── ml/
│   ├── training/          # Model training scripts
│   ├── models/            # Serialized .pt / .pkl model files
│   └── data/              # Training datasets (CVE + HackerOne labeled)
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   ├── kubernetes/        # Helm chart
│   └── terraform/         # AWS/GCP/Azure deployment modules
└── docs/
```

---

## Database Schema (PostgreSQL)

```sql
-- Core tables needed on day 1

targets         (id, domain, ip_ranges, scope_rules, authorized_at, created_by)
scans           (id, target_id, status, profile, started_at, completed_at, config_json)
endpoints       (id, scan_id, url, method, params_json, content_type, discovered_at)
findings        (id, scan_id, endpoint_id, vuln_class, severity, cvss_score, cvss_vector,
                 cwe_id, payload, request_raw, response_raw, screenshot_url,
                 confidence, false_positive, status, assigned_to, created_at)
recon_data      (id, scan_id, type, data_json, created_at)
audit_log       (id, user_id, action, target_id, scan_id, timestamp, ip_address)
users           (id, email, hashed_password, role, api_key, created_at)
```

---

## Environment Variables

```env
# Required
DATABASE_URL=postgresql://user:password@localhost:5432/awapai
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=                        # openssl rand -hex 32
LLM_PROVIDER=anthropic             # anthropic | openai
LLM_API_KEY=                       # Your API key

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=

# OSINT APIs (optional but recommended)
SHODAN_API_KEY=
CENSYS_API_ID=
CENSYS_API_SECRET=
VIRUSTOTAL_API_KEY=
SECURITYTRAILS_API_KEY=

# OOB callback server (for blind vuln detection)
OAST_SERVER=https://your-oast-server.io

# Scan limits
MAX_CONCURRENT_SCANS=5
DEFAULT_RATE_LIMIT=10              # requests/second per target
MAX_CONCURRENT_CONNECTIONS=20
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-org/awap-ai.git && cd awap-ai

# 2. Configure
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, REDIS_PASSWORD, LLM_API_KEY, SECRET_KEY

# 3. Launch all services
docker-compose up -d

# 4. Run migrations
docker-compose exec api alembic upgrade head

# 5. Create admin user
docker-compose exec api python -m awap.cli create-admin

# 6. Open dashboard
open http://localhost:5173
```

---

## Deliberately Vulnerable Targets (Local Testbed)

To test the scanning capabilities locally, the Docker Compose environment includes pre-configured vulnerable target applications:

| Target Application | Local URL | Container Name | Vulnerability Focus |
|---|---|---|---|
| **OWASP Juice Shop** | `http://localhost:3000` | `awap_juice_shop` | Modern OWASP Top 10 (Node.js/Angular) |
| **DVWA** | `http://localhost:4280` | `awap_dvwa` | Classic Web Vulnerabilities (PHP/MySQL) |
| **DVGA** | `http://localhost:5013` | `awap_dvga` | GraphQL Vulnerabilities |
| **OWASP WebGoat** | `http://localhost:8090/WebGoat` | `awap_webgoat` | Java Web Security & Lessons |
| **bWAPP** | `http://localhost:8091` | `awap_bwapp` | Extensive web vulnerabilities (PHP/MySQL) |
| **AWAP Playground** | `http://localhost:8080` | `awap_playground` | Custom local sandbox target |

---

## Core Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   AWAP-AI PLATFORM                       │
│                                                          │
│  Web UI (React)  ←→  REST API (FastAPI)  ←→  CLI         │
│                          │                               │
│               Scan Orchestrator (Celery)                 │
│                          │                               │
│            Redis Streams (Task Bus)                      │
│       ┌──────────┬───────┴──────┬──────────┐─────┐       │
│  Recon Engine  Crawler Engine  Attack Engine  AI Engine  │
│       │              │              │            │       │
│  Subdomain     JS Analyzer    Payload Gen   Classifier   │
│  Port Scan     Param Disc     Fuzzer        Risk Score   │
│  OSINT         Auth Handler   Response Anal Attack Graph │
│                                                          │
│         PostgreSQL │ Redis │ MinIO                       │
│                                                          │
│              Report Generator                            │
│         PDF │ DOCX │ JSON │ Markdown                     │
└──────────────────────────────────────────────────────────┘
```

---

## Scan Workflow (State Machine)

```
CREATED → SCOPE_VERIFIED → RECON → CRAWL → MAPPING → ATTACK → ANALYSIS → REPORTING → COMPLETE
                                                              ↕
                                                           PAUSED
                                                           ABORTED
```

**Phase 1 — Scope Verification:** Normalize target, parse scope file, log authorization confirmation.

**Phase 2 — Reconnaissance:** Certificate logs, subdomain brute-force, DNS records (A/AAAA/MX/TXT/NS), tech fingerprinting, port scanning, OSINT APIs (Shodan, Censys, VirusTotal), cloud asset discovery (S3/Azure/GCP), GitHub secret scanning.

**Phase 3 — Crawl & Mapping:** Playwright headless crawler (SPA + JS execution), authenticated session crawling, AJAX endpoint harvesting, JS bundle unpacking + AST endpoint extraction, GraphQL introspection, WebSocket enumeration, parameter discovery.

**Phase 4 — Attack Execution:** AI-prioritized attack plan, parallel module execution, rate-limited request pool, adaptive payload refinement loop, OOB callback monitoring.

**Phase 5 — AI Analysis:** ML classification, CVSS scoring, attack graph chaining, LLM-generated explanations, false positive filtering.

**Phase 6 — Reporting:** CVSS-sorted findings, PoC generation (curl + Python), executive summary, multi-format export.

---

## Attack Modules

Each module is an independent Python class implementing `AttackModule`. Add new modules without touching core engine.

```python
class AttackModule(ABC):
    module_id: str          # e.g. 'sqli_error'
    vuln_class: VulnClass   # SQLI | XSS | SSRF | RCE | ...
    severity: Severity      # CRITICAL | HIGH | MEDIUM | LOW | INFO
    requires: List[str]     # ['endpoints', 'params']

    @abstractmethod
    def run(self, target: Target, context: ScanContext) -> List[Finding]: ...

    @abstractmethod
    def verify(self, finding: Finding, context: ScanContext) -> bool: ...
```

### Module Catalog

| Module | Severity | Detection Method |
|---|---|---|
| sqli_error | CRITICAL | DB error signature matching |
| sqli_blind_boolean | CRITICAL | True/false response length diff |
| sqli_time_based | HIGH | Sleep/delay statistical confirmation |
| sqli_oob | CRITICAL | DNS/HTTP OOB callback |
| xss_reflected | HIGH | Canary reflection + sink context |
| xss_stored | HIGH | Inject-retrieve-confirm sequence |
| xss_dom | HIGH | DOM sink analysis + headless execution |
| cmd_injection | CRITICAL | Output reflection + OOB callback |
| ssrf_internal | HIGH | Internal IP / cloud metadata response |
| ssrf_oob | HIGH | DNS/HTTP blind callback |
| xxe_classic | HIGH | Entity expansion + file read |
| xxe_blind_oob | HIGH | OOB DNS/HTTP entity reference |
| ssti | CRITICAL | Template expression evaluation |
| idor | HIGH | Cross-account resource diff |
| auth_bypass | CRITICAL | JWT alg confusion, session fixation |
| file_upload_rce | CRITICAL | Polyglot upload + path traversal |
| path_traversal | HIGH | Directory traversal + filter bypass |
| http_smuggling | HIGH | CL.TE / TE.CL desync probes |
| cors_misconfig | MEDIUM | Origin reflection + credential inclusion |
| deserialization | CRITICAL | ysoserial/marshalsec gadget chains |
| prototype_pollution | HIGH | Node.js `__proto__` sink injection |
| jwt_attacks | HIGH | alg:none, RS256→HS256, weak secrets |
| csrf | MEDIUM | Token absence + cross-origin submission |
| security_headers | INFO | Missing CSP, HSTS, X-Frame-Options |

---

## Payload Generation Engine

Five generation layers, applied in order:

1. **Static Baseline** — 250,000+ categorized payloads from SecLists + PayloadsAllTheThings + proprietary DB
2. **Mutation Engine** — URL/double-URL/HTML/Unicode/Base64/hex/null-byte encoding; case, whitespace, comment mutations applied combinatorially
3. **Context-Aware Generation** — resolves injection point (URL param, JSON body, XML attr, HTTP header, cookie) + reflection context (HTML attr, JS string, SQL query, shell) to synthesize targeted payloads
4. **LLM-Assisted Generation** — sends structured context to Claude/GPT-4 with WAF signature + blocked pattern; receives novel bypass payloads ranked by estimated success probability
5. **Adaptive Refinement** — contextual bandit (Thompson Sampling) adjusts payload selection probabilities based on response signals in real time

---

## AI Components

| Component | Technology | Function |
|---|---|---|
| Payload Generator | Claude API + fine-tune | Context-aware attack string synthesis |
| Anomaly Detector | Isolation Forest + LSTM | Flags statistical response outliers |
| Vuln Classifier | BERT (fine-tuned CVE/HackerOne) | Assigns class + CVSS estimate |
| Attack Graph | GNN (DGL) | Models vuln relationships, suggests chains |
| FP Reducer | Random Forest + behavioral rules | Confirms findings before reporting |
| Report Writer | Claude API | Natural language vuln explanations |
| Scan Prioritizer | Multi-armed bandit (Thompson Sampling) | Adaptive scan resource allocation |

---

## UI Screens

**Dashboard** — active scan count, severity badges (CRITICAL/HIGH/MEDIUM/LOW), live finding stream, sparklines.

**Target Management** — target list with status badges, Add Target wizard (URL → scope → profile → auth confirm), HackerOne/Bugcrowd program sync.

**Live Scan Monitor** — phase indicator, scrolling request stream, real-time finding feed with severity badges, live Cytoscape.js attack graph, scan controls (Pause / Resume / Abort / Adjust Rate).

**Finding Detail** — CVSS vector + score, affected endpoint + parameter, HTTP request/response with syntax highlighting, PoC (curl + Python requests), remediation guidance, Burp Suite import.

**Security Analytics** — vuln class distribution, severity trend chart, attack surface treemap, top vulnerable endpoints, scan velocity metrics.

**Report Builder** — template selector (Executive / Technical / Compliance / Developer / Bug Bounty), finding multi-select, logo upload, live preview, export buttons (PDF / DOCX / JSON / Markdown / CSV).

---

## Finding Schema

```json
{
  "finding_id": "uuid",
  "scan_id": "uuid",
  "target": { "domain": "", "ip": "", "port": 0 },
  "vulnerability": {
    "class": "SQL_INJECTION",
    "name": "Blind SQL Injection in search parameter",
    "description": "LLM-generated technical description",
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "cvss_score": 9.8,
    "cvss_severity": "CRITICAL",
    "cwe_id": "CWE-89",
    "owasp_category": "A03:2021 Injection"
  },
  "affected": {
    "endpoint": "https://target.com/search",
    "method": "GET",
    "parameter": "q",
    "parameter_type": "URL"
  },
  "evidence": {
    "payload": "' AND SLEEP(5)--",
    "request_raw": "GET /search?q=...",
    "response_raw": "HTTP/1.1 200 OK ...",
    "screenshot_url": "https://minio/evidence/...",
    "poc_curl": "curl -v '...'",
    "poc_python": "import requests ..."
  },
  "remediation": {
    "summary": "Use parameterized queries / prepared statements",
    "code_example": "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
    "references": ["https://owasp.org/...", "https://cwe.mitre.org/data/definitions/89.html"]
  },
  "metadata": {
    "discovered_at": "2025-01-01T00:00:00Z",
    "confidence": 0.97,
    "false_positive": false,
    "status": "confirmed"
  }
}
```

---

## Report Templates

| Template | Audience | Focus |
|---|---|---|
| Executive Summary | CISO / Board | Business risk, financial exposure, trend |
| Technical Report | Security Engineers | Full findings + evidence + PoC |
| Developer Remediation | Dev Teams | Code-level fixes, stack-specific guidance |
| Compliance Report | Auditors | PCI-DSS / SOC 2 / HIPAA control mappings |
| Differential Report | Repeat Assessments | New findings vs. last scan |
| Bug Bounty Submission | HackerOne / Bugcrowd | Program submission format |

---

## Scan Profiles

| Profile | Rate | Depth | Modules | Use Case |
|---|---|---|---|---|
| Quick Scan | 20 req/s | Shallow | Critical only | CI/CD gate |
| Standard | 10 req/s | Medium | High+ | Regular assessment |
| Full Scan | 5 req/s | Deep | All | Full pentest |
| API Only | 15 req/s | API-focused | API modules | API security review |
| Stealth | 1 req/s | Deep | All | WAF evasion mode |
| Authenticated | 10 req/s | Deep | All | Post-auth testing |

---

## Security Safeguards (Hardcoded — Cannot Be Disabled)

- **Scope enforcement** — scan cannot begin without explicit in-scope target list + logged authorization confirmation
- **RFC1918 protection** — private IP ranges blocked unless isolated lab mode explicitly enabled
- **Default rate limit** — 10 req/s per target, max 20 concurrent connections; auto-backoff on 429
- **Read-only mode** — conservative profile avoids write operations (no POST/PUT/DELETE) by default
- **DoS payload blocklist** — billion laughs, regex ReDoS, recursive XXE blocked
- **Data encryption** — AES-256 at rest, TLS 1.3 in transit
- **Sensitive param masking** — passwords, tokens, API keys redacted in all logs
- **Full audit log** — every scan action timestamped with user ID

---

## Adding a New Attack Module

```python
# 1. Create backend/awap/modules/my_vuln.py

from awap.engines.attack import AttackModule, Finding
from awap.core.types import VulnClass, Severity

class MyVulnModule(AttackModule):
    module_id = 'my_vuln'
    vuln_class = VulnClass.CUSTOM
    severity = Severity.HIGH
    requires = ['endpoints', 'params']

    def run(self, target, context) -> List[Finding]:
        findings = []
        for endpoint in context.endpoints:
            for payload in self.payload_engine.get(self.vuln_class):
                response = self.request(endpoint, payload)
                if self.analyze(response):
                    findings.append(self.build_finding(endpoint, payload, response))
        return findings

    def verify(self, finding, context) -> bool:
        return True  # Confirmation logic here

# 2. Register in backend/awap/modules/__init__.py
from .my_vuln import MyVulnModule
MODULES.append(MyVulnModule)
```

---

## Running Tests

```bash
# Unit tests
cd backend && pytest tests/unit/ -v

# Integration tests (requires running services)
pytest tests/integration/ -v

# End-to-end against DVWA / Juice Shop
docker-compose -f docker-compose.test.yml up -d dvwa
pytest tests/e2e/ -v --target=http://localhost:4280

# Coverage
pytest --cov=awap --cov-report=html tests/
```

---

## CVSS Severity SLA Reference

| Score | Severity | SLA |
|---|---|---|
| 9.0–10.0 | CRITICAL | 4 hours |
| 7.0–8.9 | HIGH | 24 hours |
| 4.0–6.9 | MEDIUM | 72 hours |
| 0.1–3.9 | LOW | 2 weeks |
| 0.0 | INFO | Next release |

---

## 30-Day Build Roadmap

**Week 1 (Days 1–7):** Monorepo setup, PostgreSQL schema, JWT auth, Target Input Manager, Recon Engine (DNS + crt.sh + Shodan), Playwright crawler v1.

**Week 2 (Days 8–14):** Payload Engine + mutation layer, parameter discovery, core attack modules (SQLi, XSS, CMDi, SSRF, XXE, CORS), Response Analysis Engine.

**Week 3 (Days 15–21):** BERT vuln classifier, CVSS estimator, Isolation Forest + LSTM anomaly detection, LLM API integration (payload gen + report writing), Attack Graph Engine.

**Week 4 (Days 22–30):** React dashboard (all 6 screens), WebSocket live scan streaming, PDF/DOCX/JSON reporting, security hardening, E2E tests against DVWA/WebGoat/Juice Shop, Docker Compose + Helm chart, release v1.0.0.

---

## Legal

**MANDATORY:** Explicit written permission from the target system owner is required before use. Unauthorized scanning is a criminal offense under the Computer Fraud and Abuse Act (CFAA), Computer Misuse Act (CMA), and equivalent statutes globally. The platform maintains full audit logs of all scanning activity.

- Always operate within your authorized scope
- Never test production systems without a signed rules-of-engagement document
- Respect bug bounty program disclosure timelines
- Do not retain sensitive data discovered during testing
- Report critical findings promptly to protect users of vulnerable systems
