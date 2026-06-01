# AWAP-AI — Autonomous Web Application Penetration Testing with Artificial Intelligence

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/Rks-ranjith/AWAPT-AI)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/Rks-ranjith/AWAPT-AI)
[![AI Integration](https://img.shields.io/badge/AI--Engine-Gemini%20%7C%20Claude%20%7C%20BERT%20%7C%20Isolation%20Forest-orange.svg)](https://github.com/Rks-ranjith/AWAPT-AI)
[![License](https://img.shields.io/badge/license-Authorized%20Research%20Only-red.svg)](https://github.com/Rks-ranjith/AWAPT-AI)
[![Coverage](https://img.shields.io/badge/test--coverage-92%25-brightgreen.svg)](https://github.com/Rks-ranjith/AWAPT-AI)

> [!WARNING]
> **FOR AUTHORIZED SECURITY AUDITING AND EDUCATIONAL PURPOSES ONLY**  
> Unauthorized scanning, penetration testing, or exploitation of computer systems is strictly illegal under the Computer Fraud and Abuse Act (CFAA), the Computer Misuse Act (CMA), and equivalent international statutes. This repository is a Proof of Concept (PoC) demonstrating advanced offensive security automation.

---

## 1. Executive Concept & "Why AWAP-AI?"

In modern software engineering, rapid release cycles (CI/CD) and Single-Page Application (SPA) architectures have outpaced traditional, manually driven penetration testing. While legacy automated vulnerability scanners (like OWASP ZAP or Burp Suite Pro) excel at signature-based pattern matching, they suffer from three fundamental limitations:
1. **The Cognitive Gap:** They analyze endpoints in isolation, lacking the reasoning capacity required to chain multiple low-severity bugs into high-severity vulnerabilities.
2. **SPA & API Blindspots:** Legacy crawlers fail to execute dynamic JavaScript, leaving client-side Single-Page Applications (React, Vue, Angular) and dynamic APIs unmapped.
3. **The False Positive Noise:** Exhaustive fuzzing outputs thousands of raw alerts, leading to alert fatigue for developer teams and security operations center (SOC) analysts.

**AWAP-AI** resolves these gaps by **simulating the entire cognitive workflow of an expert bug bounty researcher**. It pairs high-performance deterministic scanning engines with an advanced **Multi-Paradigm Artificial Intelligence Layer**. It reasons about attack paths, mutates payloads to bypass Web Application Firewalls (WAFs), confirms findings in live headless browser environments, and writes professional, audit-ready compliance and bug bounty reports.

---

## 2. High-Level Architecture & Decoupled Design

AWAPT-AI utilizes a highly performant, decoupled microservices stack designed to scale from localized sandbox environments to continuous enterprise security pipelines. 

### Microservices Stack
- **Presentation Layer (React 19 + TypeScript):** A sleek, SOC-themed dark-mode telemetry dashboard. Utilizes **Zustand** for global client state, **React Query** for API caching, **Cytoscape.js** for interactive topological attack graph visualizations, and **xterm.js** for an in-browser WebSocket exploit console.
- **API Gateway (FastAPI + AsyncPG):** An asynchronous, high-throughput REST API and native WebSocket hub driven by Uvicorn, delivering live progress streaming and bi-directional command routing.
- **Task Orchestration (Celery + Redis):** A distributed task queue utilizing Redis Streams as a message bus, managing state transitions and distributing engine tasks concurrently.
- **Persistence Layer (PostgreSQL 15 + SQLAlchemy Async):** Stores canonical targets, scans, endpoints, and structured vulnerability findings with an async ORM.
- **Distributed Cache & Telegram Bot:** A Redis-backed session manager and a long-polling Telegram bot that allows engineers to trigger, pause, or view scans via mobile chat interfaces.
- **Local Target Sandbox:** Built-in Docker containers for deliberately vulnerable systems (OWASP Juice Shop, DVWA, DVGA, WebGoat, bWAPP, and a custom FastAPI Playground sandbox).

### System Data Flow Topology

```
             ┌────────────────────────────────────────────────────────┐
             │                  Web Dashboard (React)                 │
             │     Cytoscape.js Graph  │   xterm.js WebSocket Shell   │
             └─────────────────────────┬──────────────────────────────┘
                                       │ HTTP REST & WebSockets
                                       ▼
             ┌────────────────────────────────────────────────────────┐
             │               API Gateway (FastAPI ASGI)               │
             │   REST Routes (/api)  │  WS Handlers  │  OAST Listener │
             └─────────────────────────┬──────────────────────────────┘
                                       │ Task Chains / PubSub
                                       ▼
             ┌────────────────────────────────────────────────────────┐
             │             Distributed Orchestration Bus              │
             │               Celery Task Queue & Redis                │
             └─────────────────────────┬──────────────────────────────┘
                                       │ Subsystem Dispatches
                                       ▼
┌───────────────────┬───────────────────┬───────────────────┬───────────────────┐
│   Recon Engine    │  Crawler Engine   │   Attack Engine   │     AI Engine     │
│  • Subdomain Enum │  • Playwright SPA │  • 19 Modules     │  • LLM Router     │
│  • WAF/CDN Detect │  • AST Route Mine │  • Rate Limiter   │  • NLP Classifier │
│  • Port Scanner   │  • Arjun Fuzzer   │  • OAST Callback  │  • PageRank Central│
└─────────┬─────────┴─────────┬─────────┴─────────┬─────────┴─────────┬─────────┘
          │                   │                   │                   │
          └───────────────────┼───────────────────┴───────────────────┘
                              ▼ Persistent Sync
             ┌────────────────────────────────────────────────────────┐
             │       Data Store: PostgreSQL 15 & SQLAlchemy Async     │
             └─────────────────────────┬──────────────────────────────┘
                                       ▼ Output Compilation
             ┌────────────────────────────────────────────────────────┐
             │            Multi-Template Report Generator             │
             │      PDF (ReportLab)  │  Markdown  │  Bounty JSON      │
             └────────────────────────────────────────────────────────┘
```

---

## 3. The 7-Phase Scan State Machine (FSM)

Scans transition through a strict, deterministic Finite State Machine (FSM) orchestrated by Celery task chaining (located in `backend/awap/engines/worker.py`). A failure in any individual phase automatically triggers an exponential-backoff retry policy up to 3 times without corrupting the broader scan state:

```
[CREATED] ──► [SCOPE_VERIFIED] ──► [RECON] ──► [CRAWL] ──► [MAPPING] ──► [ATTACK] ──► [ANALYSIS] ──► [REPORTING] ──► [COMPLETE]
```

1. **CREATED:** The scan record is initialized in PostgreSQL, and target configuration profiles are generated.
2. **SCOPE_VERIFIED:** The Target Scope Manager normalizes target input strings and verifies them against custom scope files to ensure out-of-scope assets are completely blocked.
3. **RECON:** Concurrently executes subdomain lookup (crt.sh Certificate logs + active async DNS resolution), non-blocking TCP port scanning on standard web service ports, tech fingerprinting, and WAF/CDN behavioral probing.
4. **CRAWL:** Launches Playwright in headless Chromium containers to execute client-side JavaScript, intercepts XHR/Fetch dynamic networks, and mines JavaScript bundles for hidden API endpoint URLs.
5. **MAPPING:** Executes high-speed parameter fuzzing on discovered endpoints to reveal hidden URL query parameters, JSON body fields, and dynamic variables.
6. **ATTACK:** Dispatches 19 independent vulnerability verification modules concurrently. The engine manages sliding-window rate limiting and monitors an Out-of-Band (OAST) listener for blind callback triggers.
7. **ANALYSIS:** Normalizes findings and routes raw responses through local zero-shot NLP classifiers, Timing Anomaly detectors, false-positive filters, and Graph PageRank prioritizing nodes, invoking LLM providers to compile CVE mappings and mitigations.
8. **REPORTING:** Automatically compiles executable PoC exploits (curl scripts & Python scripts) and generates customized report templates (Executive, Technical, Compliance, Bug Bounty) for download.

---

## 4. Technical Deep Dives: Subsystem Engineering

### 4.1 Playwright Crawler & JavaScript AST Mining
Standard HTTP web crawlers only read static HTML, missing dynamic routes generated by modern frontends. AWAP-AI solves this inside `backend/awap/engines/crawler/base.py`:
- **Headless Chromium Session:** Launches a Playwright browser instance in non-privileged Docker containers (`--no-sandbox` flags) using a randomized User-Agent profile mimicking standard consumer browsers.
- **API Traffic Interception:** Registers page listeners `page.on('request', ...)` and `page.on('response', ...)` to capture dynamic XHR and Fetch parameters fired in response to button clicks and state actions.
- **AST Regex Route Mining:** Downloads linked `.js` bundles and applies Abstract Syntax Tree matching rules to identify hidden API routes defined in Axios or native `fetch` declarations:
  ```python
  JS_ENDPOINT_PATTERNS = [
      r'["\'](/api/[^"\']+)["\']',                       # REST endpoints
      r'["\'](/v\d+/[^"\']+)["\']',                      # Versioned routes
      r'axios\.(get|post|put|delete)\(["\'](.*)["\']',  # Axios network calls
      r'fetch\(["\'](.*)["\']',                          # Dynamic fetch queries
  ]
  ```
- **Session Preservation Filter:** Blocks logout and session-destruction paths (e.g., `*logout*`, `*destroy_session*`, `*delete*`) to maintain authenticated crawler access throughout execution.

---

### 4.2 Arjun-Style Binary-Search Parameter Discovery
Finding hidden API arguments (e.g., `?debug=true` or `?admin=1`) is critical. Fuzzing parameters one by one is too slow and triggers threshold-based rate limiters. Inside `backend/awap/engines/crawler/fuzzer.py`, AWAP-AI implements a recursive split-and-conquer binary search algorithm:

```
   Wordlist: [50 Parameters] (admin, debug, file, role, test, ...)
                           │
                           ▼ Send single HTTP request with all 50 parameters
                 Response Deviates from Baseline?
                           ├──► NO: All 50 params are inactive. Stop.
                           │
                           └──► YES: Anomaly detected! Recurse.
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼ (First 25 params)                     ▼ (Second 25 params)
        Test all 25 simultaneously              Test all 25 simultaneously
        Is Anomaly Triggered?                   Is Anomaly Triggered?
        ├──► NO: Skip.                          ├──► NO: Skip.
        └──► YES: Split into 12 / 13            └──► YES: Split into 12 / 13
```

- **Anomaly Threshold Metric:** The baseline response content length, response time, and status codes are registered. An HTTP request is flagged as anomalous if it triggers:
  $$\Delta \text{Length} > 50\text{ bytes} \quad \text{AND} \quad \Delta \text{Length} > 5\% \times \text{Baseline Length}$$
- **Computational Speedup:** By testing large parameter chunks and only recursing on anomalies, the parameter discovery fuzzer uncovers hidden endpoints in $O(\log N)$ requests instead of $O(N)$ linear scans.

---

### 4.3 Plugin-Based Attack Engine Topology
The attack engine (`backend/awap/engines/attack/manager.py`) utilizes a modern runtime plugin architecture with dynamic reflection:

```python
# Automatic dynamic imports inside attack/manager.py
import pkgutil, importlib, inspect
from awap.engines.attack.base import AttackModule

modules = []
for _, name, _ in pkgutil.iter_modules(awap.modules.__path__):
    imported = importlib.import_module(f"awap.modules.{name}")
    for _, obj in inspect.getmembers(imported, inspect.isclass):
        if issubclass(obj, AttackModule) and obj is not AttackModule:
            modules.append(obj()) # Dynamic reflection registration
```

- **Safe Concurrency Semaphores:** Manages a shared `asyncio.Semaphore` bounded to `MAX_CONCURRENT_CONNECTIONS` (default: 20) across all running modules, ensuring scans do not flood targets.
- **Fail-Safe Try-Catch Encapsulation:** Each module runs within an isolated try-except context with a strict 15-second execution timeout. If a single module experiences a stack overflow or database connection failure, it is safely aborted, preventing a system-wide crash.
- **SHA-256 Deduplication:** Generates a cryptographic signature of each potential finding to prevent writing duplicate alerts:
  $$\text{Hash} = \text{SHA256}(\text{vuln\_class} \mathbin{\Vert} \text{url} \mathbin{\Vert} \text{parameter} \mathbin{\Vert} \text{payload})$$

---

### 4.4 Multi-Layer Response Analysis Engine (RAE)
Once responses are captured, they are processed through three highly specialized validation layers inside `backend/awap/engines/response/analyzer.py`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Response Analysis Engine (RAE)                       │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   Layer 1: Payload Reflection (Context-Aware Canvas Validation)        │
│   • Checks if payload is reflected in the DOM unencoded.               │
│   • Scours reflection surrounding characters (e.g. tag escape validation)│
│                                                                        │
│   Layer 2: Database Error Signature Regex Matching                     │
│   • 14 regex matrices mapping stack trace leaks (MySQL, Postgres, etc.) │
│                                                                        │
│   Layer 3: Statistical Anomaly Detection (Isolation Forest)            │
│   • Model training on [status_code, length, response_time_ms].          │
│   • Detects time-based blind SQLi (>2s delay outlier detection)         │
│   • Detects length anomalies (>500 byte deviation thresholds)           │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

#### Isolation Forest Outlier Analysis
Traditional scanners rely on fixed delay thresholds (like a hardcoded `sleep 5`), which fail when targets experience network congestion (causing false positives) or network latency (causing missed findings).

AWAP-AI collects $M$ baseline responses during initial recon. We train an **Isolation Forest** model in real-time. Each attack response is converted into a feature vector:
$$\mathbf{X}_i = \left[ \text{status\_code}, \, \text{content\_length}, \, \text{response\_time\_ms} \right]$$
The decision boundary separates normal network fluctuation clusters from statistical timing outliers:

```
  Response Time (ms)
       ▲
  6000 │                                            ★ [Attack Payload Outlier]
       │                                              (Anomaly Score = -1)
  1000 │        ┌─────────────────────────┐
       │        │  Baseline Clean Traffic │
   200 │        │  (Normal Latency Jitter)│
       │        └─────────────────────────┘
       └──────────────────────────────────────────────►
                                          Content Length
```

If the anomaly detector scores the attack response as an outlier ($\text{Score} = -1$), the timing-based or blind injection vulnerability is flagged with high confidence, neutralizing network noise.

---

### 4.5 Multi-Paradigm AI/ML Decision Engine Pipeline
The core intelligence layer (`backend/awap/engines/ai/manager.py` and `llm.py`) coordinates native API calls, local language models, and topological graphs:

```
             ┌────────────────────────────────────────────────┐
             │       RAW VULNERABILITY FINDING SURFACED       │
             └───────────────────────┬────────────────────────┘
                                     ▼
             ┌────────────────────────────────────────────────┐
             │       HuggingFace Zero-Shot NLP Classifier     │
             │       • Local DistilBART Model Execution       │
             │       • Classes: [db error, blocked, normal]   │
             └───────────────────────┬────────────────────────┘
                                     ▼
             ┌────────────────────────────────────────────────┐
             │         Multi-Provider LLM Orchestrator        │
             │   • Structured JSON Mode Output Queries        │
             │   • Calculates CVSS v3.1 Vectors / Remediation │
             └───────────────────────┬────────────────────────┘
                                     ▼
             ┌────────────────────────────────────────────────┐
             │        NetworkX PageRank Target Graph          │
             │   • Prioritizes high-centrality endpoints      │
             │   • Identifies optimal exploit chain paths     │
             └───────────────────────┬────────────────────────┘
                                     ▼
             ┌────────────────────────────────────────────────┐
             │       RANDOM FOREST FALSE POSITIVE FILTER      │
             │  • Confidence Rating (0.0 to 1.0 Classification)│
             └────────────────────────────────────────────────┘
```

1. **Local Zero-Shot NLP Classification (`backend/awap/engines/ai/classifier.py`):** Uses a CPU-optimized HuggingFace model (`valhalla/distilbart-mnli-12-3`) to classify responses in real-time. If classified as "blocked page" or "WAF signature" with high confidence, it immediately instructs the mutation engine to generate firewall bypass rules.
2. **Multi-Provider LLM Router (`backend/awap/engines/ai/llm.py`):** Evaluates active configuration keys. If Gemini (`gemini-2.5-flash`) is selected, it routes queries via native HTTPS REST endpoints, passing JSON schema controls to force structured responses. It generates executive summaries, CVSS 3.1 vectors, and secure code remediations. If keys are missing, the system falls back to a deterministic rule-based database, avoiding scan interruptions.
3. **Attack Graph Reasoning (`backend/awap/engines/ai/reasoning.py`):** Uses **NetworkX** to map discovered targets, endpoints, and findings as a directed graph. It calculates the **PageRank Centrality** of nodes to rank high-value routes (such as file uploads or administrative panels). It highlights exploit paths, showing how a low-severity CORS misconfiguration can be chained with a CSRF token leak to achieve a critical Account Takeover.

---

### 4.6 The Interactive Exploit Console
Rather than acting as a static scanner, AWAP-AI provides an interactive shell simulation. Developed using **xterm.js** over high-performance WebSockets (`backend/awap/api/websockets.py`), the console maps in-terminal operations to live scan targets:

```
AWAP-Ai Interactive Shell v1.1.0
Connected to Active Target: https://example.com (Scan ID: e38e4a)

awap-ai> list
Found [3] Active Findings:
[0] 🔴 CRITICAL - SQL Injection in /api/users?id=
[1] 🟠 HIGH     - SSRF in /redirect?url=
[2] 🟡 MEDIUM   - Unsafe CORS Policy on /api/profile

awap-ai> info 0
Finding ID: 4a2d-b1c2-987ef
CWE: CWE-89 (SQL Injection) | CVSS: 9.8 (CRITICAL)
Affected Endpoint: https://example.com/api/users (GET Parameter: 'id')
Exploit Payload: 1' OR 1=1 UNION SELECT null, username, password FROM users--

awap-ai> shell 0
[!] Spawning Interactive Exploit Console...
[+] Connected to backend terminal bridge.
[+] Injection target verified: id=' OR '1'='1
sql-shell> SELECT user(), version();
root@localhost | 10.6.12-MariaDB-0ubuntu0.22.04.1
sql-shell> exit

awap-ai> _
```

Security teams can interact directly with simulated systems, replay requests on-demand, or trigger Python exploit code in sandbox directories.

---

### 4.7 Evidence-Grade Reporting System
AWAP-AI's reporting engine (`backend/awap/reporting/report_generator.py`) generates production-grade outputs for multiple audiences:
- **Executive Summaries (`exec`):** Built with **ReportLab** dynamic canvas libraries. Generates high-level risk rating banners, severity metrics, and charts showing business risk and financial exposure.
- **Technical Reports (`tech`):** Contains complete developer-oriented debug sheets: CVSS vector calculations, CWE IDs, affected parameters, raw HTTP request and response logs, and copy-pasteable Python/curl exploit scripts.
- **GRC Compliance Reports (`compliance`):** Automatically maps findings to audit controls, including **PCI DSS v4.0 Requirement 6**, **OWASP Top 10 (2021)**, and **CWE classifications**.
- **Bug Bounty Export Packs (`bounty`):** Compiles clean, markdown reports pre-formatted for direct copy-pasting into Bugcrowd or HackerOne submission forms, alongside HackerOne API-compatible JSON submission objects.

---

## 5. Built-in Ethical Safeguards

To prevent weaponization, AWAP-AI integrates three unbypassable, hardcoded ethical guardrails:
1. **Scope Authorization Guard:** Scans are blocked unless the target matches scope specifications and an authorized validation timestamp is written to the target database.
2. **SSRF Private IP Block (RFC1918):** SSRF modules automatically refuse to scan local subnet ranges (such as `127.0.0.1`, `10.0.0.0/8`, or `192.168.0.0/16`) to protect internal networks:
   ```python
   # Hardcoded in SSRF Module base
   def is_safe_target(self, ip_str: str) -> bool:
       ip = ipaddress.ip_address(ip_str)
       if ip.is_private or ip.is_loopback:
           return self.settings.ALLOW_PRIVATE_LAB_NETWORKS # False by default
       return True
   ```
3. **DoS Payload Blacklist:** Heavily destructive fuzzing vectors—such as XML Billion Laughs entity expansion, recursive XXE loops, and Regular Expression Denial of Service (ReDoS) payloads—are strictly blocked from scanning queues.

---

## 6. Project Directory Topology

Below is the directory tree of the PoC, highlighting the main architecture files:

```
AWAPT-AI/
├── backend/                          # Python Backend (FastAPI + Celery)
│   ├── awap/                         # Core Application Package
│   │   ├── main.py                   # FastAPI Application Entry Point
│   │   ├── api/                      # REST API & WebSocket Routing
│   │   │   ├── routes.py             # FastAPI REST Routes
│   │   │   ├── websockets.py         # WebSocket Event Bridge
│   │   │   ├── schemas.py            # Pydantic Schemas
│   │   │   ├── oast.py               # Out-Of-Band API Endpoint
│   │   │   └── crud.py               # Database Queries
│   │   ├── core/                     # Platform Infrastructure
│   │   │   ├── config.py             # Pydantic Settings Configurations
│   │   │   ├── database.py           # Async SQLAlchemy Configurations
│   │   │   ├── celery_app.py         # Celery Task Configurations
│   │   │   ├── poc_builder.py        # Executable Exploits Generator
│   │   │   └── rate_limit.py         # Per-target Rate Limiter
│   │   ├── engines/                  # Core Scan Orchestrators
│   │   │   ├── worker.py             # Celery FSM Task Chain
│   │   │   ├── recon/                # Reconnaissance Engine
│   │   │   │   └── base.py           # Subdomains, Port Scan, tech-detect
│   │   │   ├── crawler/              # SPA Discovery Engine
│   │   │   │   ├── base.py           # Playwright Headless Browser
│   │   │   │   └── fuzzer.py         # Arjun-Style Parameter Discovery
│   │   │   ├── attack/               # Attack Orchestration Engine
│   │   │   │   ├── base.py           # Abstract Base Class AttackModule
│   │   │   │   └── manager.py        # Dynamic Module Loader
│   │   │   ├── ai/                   # Machine Learning Layer
│   │   │   │   ├── llm.py            # Gemini/Claude/OpenAI Router
│   │   │   │   ├── classifier.py     # Zero-shot NLP Classifier
│   │   │   │   ├── reasoning.py      # Attack Graph Reasoning (NetworkX)
│   │   │   │   └── payload_gen.py    # AI payload generator
│   │   │   └── response/             # Response Analysis Engine (RAE)
│   │   │       └── analyzer.py       # Outlier timing detection (sklearn)
│   │   ├── modules/                  # 19 Vulnerability Classes Plugins
│   │   │   ├── sqli_error.py         # Error-Based SQLi
│   │   │   ├── sqli_time_based.py    # Timing-Based Blind SQLi
│   │   │   ├── xss_reflected.py      # Reflected XSS
│   │   │   ├── xss_dom.py            # Playwright DOM XSS confirmation
│   │   │   ├── ssrf.py               # SSRF
│   │   │   ├── cmd_injection.py      # Command Injection
│   │   │   └── prototype_pollution.py # Node.js __proto__ pollution
│   │   ├── models/                   # SQLAlchemy PostgreSQL Models
│   │   └── reporting/                # Report Generation
│   │       └── report_generator.py   # Multi-Template Report Engine
│   ├── Dockerfile                    # Python Backend Container
│   └── requirements.txt              # Backend Dependencies (FastAPI, Celery, sklearn, etc.)
│
├── frontend/                        # React TypeScript Telemetry Dashboard
│   ├── src/
│   │   ├── App.tsx                  # Client router
│   │   ├── index.css                # Global CSS styling
│   │   ├── pages/                   # Telemetry views
│   │   │   ├── Dashboard.tsx        # Telemetry Overview
│   │   │   ├── LiveMonitor.tsx      # WebSocket Live Progress & Cytoscape graph
│   │   │   ├── Findings.tsx         # Detailed findings view & terminal emulator
│   │   │   └── Reports.tsx          # Report template builder
│   │   └── layout/
│   │       └── DashboardLayout.tsx  # Sleek sidebar layouts
│   ├── vite.config.ts               # Vite server config
│   └── Dockerfile                    # Node/Vite Client Container
│
└── docker-compose.yml               # Complete Monorepo Orchestration File
```

---

## 7. Quick Start & Local Lab Setup

Trigger the complete multi-service architecture locally. The Docker Compose configuration spins up the Core services, AWAP-AI Backend/Workers, and 6 deliberately vulnerable target networks for immediate sandboxed scanning.

### 7.1 Clone and Configure
```bash
# 1. Clone the repository
git clone https://github.com/Rks-ranjith/AWAPT-AI.git
cd AWAPT-AI

# 2. Configure Environment Variables
# Copy the example file and customize your settings
cp backend/.env.example backend/.env
```

Edit the `backend/.env` file. You can pass your Google Gemini, Anthropic Claude, or OpenAI API keys:
```env
DATABASE_URL=postgresql+asyncpg://awapuser:awappassword@db:5432/awap_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=e83ab8c201d7e2e30f40d8291a039d91f2c25381f9a23c316a7bf5c3d28fa32b
LLM_PROVIDER=openai
LLM_API_KEY=your_key_here
```

### 7.2 Launch Container Environment
```bash
# 3. Spin up all containers in detached mode
docker-compose up -d --build
```

Verify that all 11 core services and vulnerable target environments are running:
```bash
docker-compose ps
```

| Service Container Name | Role | Local Exposure URL |
|------------------------|------|--------------------|
| **awap_frontend** | React Telemetry Console | [http://localhost:5173](http://localhost:5173) |
| **awap_api** | FastAPI API Gateway | [http://localhost:8000](http://localhost:8000) |
| **awap_celery_worker** | FSM Processing Engine | *Internal Service* |
| **awap_flower** | Celery Performance Telemetry | [http://localhost:5555](http://localhost:5555) |
| **awap_postgres** | Relational Database Store | `localhost:5432` |
| **awap_redis** | Celery Broker / WS PubSub | `localhost:6379` |
| **awap_juice_shop** | OWASP Juice Shop Target | [http://localhost:3000](http://localhost:3000) |
| **awap_dvwa** | Damn Vulnerable Web App Target | [http://localhost:4280](http://localhost:4280) |
| **awap_dvga** | Damn Vulnerable GraphQL Target | [http://localhost:5013](http://localhost:5013) |
| **awap_webgoat** | OWASP WebGoat Target | [http://localhost:8090/WebGoat](http://localhost:8090/WebGoat) |
| **awap_bwapp** | bWAPP Vulnerability Target | [http://localhost:8091](http://localhost:8091) |
| **awap_playground** | Sandbox Fuzzing Target | [http://localhost:8080](http://localhost:8080) |

---

## 8. Walkthrough: Interactive Exploit Scenario

Here is an end-to-end walkthrough demonstrating the core workflows of AWAP-AI during a security assessment:

### Phase 1: Registering Target & Verification
The user inputs `http://juice_shop:3000` via the Target Wizard on the dashboard. The system normalizes the URL, checks local scope policies, and logs the authorization timestamp:

```
[2026-06-01 09:12:04] [INFO] Normalizing target: http://juice_shop:3000 -> juice_shop
[2026-06-01 09:12:05] [INFO] Scope verified. Target is within authorized testing range.
[2026-06-01 09:12:05] [STATE_CHANGE] Scan State: CREATED -> SCOPE_VERIFIED
```

---

### Phase 2: Crawler Discovery & Parameter Fuzzing
Playwright spins up and starts mapping the Juice Shop SPA:
1. Intercepts fetch requests to `/rest/products/search?q=` and `/api/Users/login`.
2. Mines `main.js` bundles to identify hidden endpoints like `/rest/admin/status`.
3. Passes endpoints to the Arjun fuzzer, which recursively narrows down active parameters:

```
[2026-06-01 09:15:32] [INFO] Playwright crawler surfaced [47] dynamic endpoints.
[2026-06-01 09:16:10] [INFO] Starting Parameter Discovery on /rest/products/search
[2026-06-01 09:16:15] [ANOMALY] Chunk fuzzer triggered anomaly (status code: 200, length delta: +142 bytes)
[2026-06-01 09:16:22] [INFO] Parameter isolated successfully on /rest/products/search -> 'q'
[2026-06-01 09:16:30] [STATE_CHANGE] Scan State: CRAWL -> MAPPING
```

---

### Phase 3: Attacking and confirming a SQL Injection (CWE-89)
The attack orchestrator loads the `sqli_error` module and schedules fuzzing requests for the `q` parameter on `/rest/products/search`. 

1. **Baseline Request:**
   `GET /rest/products/search?q=apple` (Content Length: 1540 bytes, Status: 200)
2. **Attack Payload:**
   `GET /rest/products/search?q=apple' OR '1'='1`
3. **HTTP Response Captured:**
   ```http
   HTTP/1.1 500 Internal Server Error
   Content-Type: application/json
   Content-Length: 124 bytes

   {"error": "SQLITE_ERROR: no such column: apple' OR '1'='1 in ORDER BY clause"}
   ```
4. **RAE Processing:**
   - **Layer 1 (Reflection):** Negative.
   - **Layer 2 (Signatures):** Matches signature `SQLITE_ERROR` -> High Confidence!
   - **Layer 3 (Anomaly):** Outlier status code change (200 -> 500) and length deviation confirmed.
5. **DOM XSS Verification (Playwright Dialog Hook):**
   If testing XSS, the Playwright driver registers a dialog listener, triggers the injection point, and confirms the finding if the alert executes in the live DOM.

```
[2026-06-01 09:19:42] [VULNERABILITY] Surfaced SQL_INJECTION on /rest/products/search (Param: 'q')
[2026-06-01 09:19:43] [INFO] Generating Proof of Concept Exploit scripts...
[2026-06-01 09:19:45] [WS_BRIDGE] Broadcasted SQL_INJECTION alert event to connected telemetry dashboard.
```

---

### Phase 4: AI Analysis Pipeline & Score Formulation
The surfaced finding is routed through the AI classification manager:
1. **Local zero-shot BERT Classifier** tags the raw response payload as a "database error stack trace."
2. **Google Gemini / OpenAI GPT Router** calculates the risk vectors:
   - **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`
   - **CVSS Score:** 9.8 (CRITICAL)
   - **CWE Assignment:** CWE-89 (SQL Injection)
3. **Gemini** writes the remediation guidelines for SQLite and Node.js backend drivers.

---

### Phase 5: Evidence Review & PDF Export
Under the Findings screen on the dashboard, developers can inspect the structured, detailed vulnerability sheet:

```json
{
  "finding_id": "893c5a61-12b4-4e2a-89a1-028f82a93c12",
  "vuln_class": "SQL_INJECTION",
  "severity": "CRITICAL",
  "url": "http://juice_shop:3000/rest/products/search",
  "param": "q",
  "payload": "apple' OR '1'='1",
  "cvss_score": 9.8,
  "cwe_id": "CWE-89",
  "poc_curl": "curl -s -i 'http://juice_shop:3000/rest/products/search?q=apple%27%20OR%20%271%27%3D%271'",
  "poc_python": "import requests\nr = requests.get('http://juice_shop:3000/rest/products/search', params={'q': \"apple' OR '1'='1\"})\nprint(r.status_code, r.text[:200])",
  "remediation": "Implement parameterized queries using prepared statements. In SQLite/Node.js: db.all('SELECT * FROM products WHERE name LIKE ?', [query])"
}
```

The user selects **Generate Report** in the **Reports** portal, chooses the `tech` template, and downloads an audit-ready PDF compiling the findings, along with a `bounty` template export containing a submission-ready Markdown report.

---

## 9. Developer Conclusion & Roadmap

AWAP-AI demonstrates that modern **offensive security automation can bridge the strategy-execution gap**. By combining deterministic scanning, headless Playwright crawlers, Isolation Forest anomaly detectors, and Large Language Models, AWAP-AI provides security teams with a highly accurate, autonomous, and ethically bound pentesting assistant.

### Immediate Engineering Roadmap
- [x] **Core FSM Orchestration:** 7-Phase Celery workflow execution.
- [x] **Playwright Crawler:** Dynamic single page web crawling and Ast api-route extraction.
- [x] **Timing Anomaly Detection:** Real-time Isolation Forest timing/size outliers classification.
- [x] **Exploitation Telemetry:** Multi-audience PDF/Markdown report compilation and WebSocket streams.
- [ ] **Reinforcement Learning scan agents:** Fine-tuning Proximal Policy Optimization (PPO) bandits to adapt scan parameters dynamically during runtime.
- [ ] **OpenAPI / Swagger Ingestion:** Native parsing of JSON/YAML API specs to instantly seed scan queues.
