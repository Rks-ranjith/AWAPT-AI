"""
Industry-standard proof-of-concept artifact builder (architecture §13.1 evidence block).
"""
from __future__ import annotations

import base64
import json
import urllib.parse
from typing import Any


def build_http_request_raw(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: str | None = None,
) -> str:
    headers = headers or {}
    parsed = urllib.parse.urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    lines = [f"{method.upper()} {path} HTTP/1.1", f"Host: {parsed.netloc}"]
    for k, v in headers.items():
        lines.append(f"{k}: {v}")
    lines.append("")
    if body:
        lines.append(body)
    return "\n".join(lines)


def build_http_response_raw(status_code: int, headers: dict, body: str, max_body: int = 4000) -> str:
    lines = [f"HTTP/1.1 {status_code}"]
    for k, v in list(headers.items())[:20]:
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append((body or "")[:max_body])
    return "\n".join(lines)


def poc_curl(method: str, url: str, param: str | None, payload: str | None) -> str:
    method = method.upper()
    if param and payload is not None:
        if method == "GET":
            sep = "&" if "?" in url else "?"
            enc = urllib.parse.quote(str(payload), safe="")
            return f"curl -s -i -X GET '{url}{sep}{param}={enc}'"
        return (
            f"curl -s -i -X {method} '{url}' "
            f"-H 'Content-Type: application/x-www-form-urlencoded' "
            f"--data-urlencode '{param}={payload}'"
        )
    return f"curl -s -i -X {method} '{url}'"


def poc_python(method: str, url: str, param: str | None, payload: str | None) -> str:
    method = method.upper()
    if param and payload is not None:
        if method == "GET":
            return (
                "import requests\n\n"
                f"url = {url!r}\n"
                f"params = {{\"{param}\": {payload!r}}}\n"
                "r = requests.get(url, params=params, verify=False, timeout=15)\n"
                "print('Status:', r.status_code)\n"
                "print(r.text[:2000])"
            )
        return (
            "import requests\n\n"
            f"url = {url!r}\n"
            f"data = {{\"{param}\": {payload!r}}}\n"
            f"r = requests.request({method!r}, url, data=data, verify=False, timeout=15)\n"
            "print('Status:', r.status_code)\n"
            "print(r.text[:2000])"
        )
    return (
        "import requests\n\n"
        f"r = requests.request({method!r}, {url!r}, verify=False, timeout=15)\n"
        "print('Status:', r.status_code)\n"
        "print(r.text[:2000])"
    )


def poc_burp_base64(method: str, url: str, param: str | None, payload: str | None) -> str:
    """Burp Suite Repeater paste format (base64-wrapped raw HTTP)."""
    body = None
    if param and payload is not None and method.upper() != "GET":
        body = urllib.parse.urlencode({param: payload})
    raw = build_http_request_raw(method, url if method.upper() == "GET" and param and payload else url, body=body)
    if method.upper() == "GET" and param and payload is not None:
        sep = "&" if "?" in url else "?"
        enc = urllib.parse.quote(str(payload), safe="")
        raw = build_http_request_raw("GET", f"{url}{sep}{param}={enc}")
    return base64.b64encode(raw.encode()).decode()


def steps_to_reproduce(
    url: str,
    param: str | None,
    payload: str | None,
    method: str = "GET",
) -> str:
    lines = [
        "## Steps to Reproduce",
        "",
        "1. Open a browser or HTTP client with access to the target (authorized scope only).",
        f"2. Send a **{method.upper()}** request to:",
        f"   `{url}`",
    ]
    if param and payload is not None:
        lines.extend([
            f"3. Set parameter **`{param}`** to:",
            "```",
            str(payload),
            "```",
            "4. Observe the application response for the vulnerability indicator described below.",
        ])
    else:
        lines.append("3. Observe the response for the vulnerability indicator described below.")
    return "\n".join(lines)


def build_poc_artifacts(finding: dict[str, Any]) -> dict[str, Any]:
    """Full evidence + PoC package per architecture finding schema."""
    method = (finding.get("method") or "GET").upper()
    url = finding.get("url") or ""
    param = finding.get("param")
    payload = finding.get("payload")
    request_raw = finding.get("request_raw")
    response_raw = finding.get("response_raw")

    if not request_raw:
        request_raw = build_http_request_raw(method, url)
    if not response_raw and finding.get("response_status"):
        response_raw = build_http_response_raw(
            finding["response_status"],
            finding.get("response_headers") or {},
            str(finding.get("response_body") or ""),
        )

    artifacts = {
        "poc_curl": poc_curl(method, url, param, payload),
        "poc_python": poc_python(method, url, param, payload),
        "poc_burp_base64": poc_burp_base64(method, url, param, payload),
        "request_raw": request_raw,
        "response_raw": (response_raw or "")[:8000],
        "steps_to_reproduce": steps_to_reproduce(url, param, payload, method),
    }
    return artifacts


def bounty_markdown_report(finding: dict[str, Any], program: str = "") -> str:
    """HackerOne-style submission body."""
    art = finding.get("poc_artifacts") or build_poc_artifacts(finding)
    parts = [
        f"# {finding.get('title') or finding.get('vuln_class', 'Security Issue')}",
        "",
        "## Summary",
        finding.get("description") or "A security vulnerability was identified during authorized testing.",
        "",
        art.get("steps_to_reproduce", ""),
        "",
        "## Proof of Concept",
        "",
        "**curl:**",
        "```bash",
        art.get("poc_curl", ""),
        "```",
        "",
        "**Python:**",
        "```python",
        art.get("poc_python", ""),
        "```",
        "",
    ]
    if finding.get("evidence"):
        parts.extend(["## Evidence", "", str(finding["evidence"]), ""])
    if art.get("request_raw"):
        parts.extend(["## HTTP Request", "```http", art["request_raw"][:2500], "```", ""])
    if art.get("response_raw"):
        parts.extend(["## HTTP Response", "```http", art["response_raw"][:2500], "```", ""])
    parts.extend([
        "## Impact",
        finding.get("impact") or _default_impact(finding.get("vuln_class", "")),
        "",
        "## Remediation",
        finding.get("remediation") or "Apply secure development practices and input validation.",
        "",
        f"**Severity:** {finding.get('severity', 'MEDIUM')} | "
        f"**CVSS:** {finding.get('cvss_score', 'N/A')} | "
        f"**CWE:** {finding.get('cwe_id', 'N/A')}",
    ])
    if program:
        parts.append(f"\n---\n*Scope: {program}*")
    return "\n".join(parts)


def _default_impact(vuln_class: str) -> str:
    vc = (vuln_class or "").upper()
    if "SQL" in vc:
        return "Attackers may read, modify, or delete database records, leading to data breach."
    if "XSS" in vc:
        return "Attackers may execute scripts in victims' browsers, enabling session hijacking."
    if "SSRF" in vc:
        return "Attackers may coerce the server to access internal resources or cloud metadata."
    if "IDOR" in vc:
        return "Attackers may access other users' data without proper authorization."
    return "This issue may compromise confidentiality, integrity, or availability of the application."
