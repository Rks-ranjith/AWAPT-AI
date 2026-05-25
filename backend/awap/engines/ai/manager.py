import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from awap.models.finding import Finding
from awap.core.config import settings
from awap.reporting.report_generator import CWE_BY_VULN

logger = logging.getLogger(__name__)

CVSS_BY_VULN = {
    "SQL_INJECTION": 9.8,
    "XSS": 6.1,
    "XSS_REFLECTED": 6.1,
    "SSRF": 8.6,
    "SSRF_BLIND": 8.6,
    "IDOR": 6.5,
    "PATH_TRAVERSAL": 7.5,
    "CMD_INJECTION": 9.8,
    "NOSQL_INJECTION": 8.1,
    "OPEN_REDIRECT": 4.7,
    "CORS_MISCONFIG": 5.3,
    "JWT_ATTACK": 7.5,
    "SECURITY_HEADERS": 5.0,
    "SUBDOMAIN_TAKEOVER": 7.4,
    "CLOUD_LEAK": 7.5,
    "GRAPHQL_INTROSPECTION": 5.3,
    "PROTOTYPE_POLLUTION": 8.1,
    "LLM_PROMPT_INJECTION": 7.5,
}

SEVERITY_BY_CVSS = [
    (9.0, "CRITICAL"),
    (7.0, "HIGH"),
    (4.0, "MEDIUM"),
    (0.1, "LOW"),
]


def _severity_from_cvss(score: float) -> str:
    for threshold, label in SEVERITY_BY_CVSS:
        if score >= threshold:
            return label
    return "INFO"


def _rule_based_classify(finding: dict) -> dict:
    """Deterministic enrichment when LLM is unavailable."""
    vc = (finding.get("vuln_class") or "UNKNOWN").upper()
    cvss = CVSS_BY_VULN.get(vc, 5.0)
    cwe = CWE_BY_VULN.get(vc, "CWE-200")
    severity = _severity_from_cvss(cvss)
    param = finding.get("param") or "parameter"
    url = finding.get("url") or "the affected endpoint"
    evidence = finding.get("evidence") or "automated scanner signals"

    descriptions = {
        "SQL_INJECTION": (
            f"SQL injection was detected via parameter `{param}` on {url}. "
            f"Evidence: {evidence}."
        ),
        "XSS": (
            f"Cross-site scripting was detected — user input in `{param}` is reflected "
            f"without adequate encoding on {url}."
        ),
        "SSRF": (
            f"Server-Side Request Forgery may allow outbound requests from the server "
            f"via `{param}` on {url}."
        ),
        "IDOR": (
            f"Insecure direct object reference: `{param}` on {url} may allow "
            f"access to unauthorized resources."
        ),
    }
    remediations = {
        "SQL_INJECTION": "Use parameterized queries / prepared statements. Never concatenate user input into SQL.",
        "XSS": "Context-aware output encoding and Content-Security-Policy. Validate input server-side.",
        "SSRF": "Allowlist outbound destinations, block metadata IPs, disable unnecessary URL fetchers.",
        "IDOR": "Enforce authorization on every object access using server-side session identity.",
    }

    desc = descriptions.get(vc) or (
        f"{vc.replace('_', ' ').title()} identified on {url} (parameter: {param}). Evidence: {evidence}."
    )
    fix = remediations.get(vc) or "Apply defense-in-depth: validate input, enforce least privilege, and patch dependencies."

    fp_prob = 0.2
    if not finding.get("evidence") and not finding.get("response_raw"):
        fp_prob = 0.55

    return {
        "vuln_class": vc,
        "severity": severity,
        "cvss_score": cvss,
        "cvss_vector": f"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "cwe_id": cwe,
        "description": desc,
        "remediation": fix,
        "false_positive_probability": fp_prob,
    }


class AIDecisionEngine:
    def __init__(self, api_key: str | None, provider: str = "anthropic"):
        self.api_key = api_key
        self.provider = provider
        if api_key:
            from awap.engines.ai.llm import AILogicEngine
            from awap.core.config import settings
            self.engine = AILogicEngine(
                provider=provider,
                api_key=api_key,
                model=settings.LLM_MODEL,
                base_url=settings.LLM_BASE_URL
            )
        else:
            self.engine = None

    async def classify_finding(self, finding: dict) -> dict:
        if not self.api_key or not self.engine:
            return _rule_based_classify(finding)

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
URL: {finding.get('url')}
Parameter: {finding.get('param')}
Payload used: {finding.get('payload')}
Evidence found: {finding.get('evidence')}
HTTP response snippet: {str(finding.get('response_raw', ''))[:500]}

Return ONLY valid JSON. No markdown, no explanation."""

        try:
            text = await self.engine._dispatch_prompt(
                system_prompt="You are an expert security finding scoring engine. You output ONLY valid, raw JSON.",
                user_prompt=prompt,
                max_tokens=1000
            )
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            logger.error("AI classification error: %s", e)
            return _rule_based_classify(finding)


async def run_ai_analysis(db: AsyncSession, scan_id: str):
    res = await db.execute(select(Finding).filter(Finding.scan_id == scan_id))
    findings = res.scalars().all()

    ai = AIDecisionEngine(api_key=settings.LLM_API_KEY, provider=settings.LLM_PROVIDER)

    for finding in findings:
        fin_dict = {
            "url": finding.url,
            "param": finding.param,
            "payload": finding.payload,
            "evidence": finding.evidence,
            "response_raw": finding.response_raw,
            "vuln_class": finding.vuln_class,
        }

        result = await ai.classify_finding(fin_dict)
        if isinstance(result, dict) and "description" in result:
            finding.description = result.get("description", finding.description)
            finding.remediation = result.get("remediation", finding.remediation)
            finding.cvss_score = result.get("cvss_score", finding.cvss_score)
            finding.cvss_vector = result.get("cvss_vector", finding.cvss_vector)
            finding.cwe_id = result.get("cwe_id", finding.cwe_id)
            finding.impact = result.get("impact") or finding.impact

            fp_prob = float(result.get("false_positive_probability", 0.0))
            if fp_prob > 0.7:
                finding.false_positive = True

            finding.severity = result.get("severity", finding.severity)
            if result.get("vuln_class"):
                finding.vuln_class = result["vuln_class"]

        from awap.core.poc_builder import build_poc_artifacts, _default_impact

        if not finding.impact:
            finding.impact = _default_impact(finding.vuln_class)
        artifacts = build_poc_artifacts({
            "url": finding.url,
            "method": finding.method or "GET",
            "param": finding.param,
            "payload": finding.payload,
            "request_raw": finding.request_raw,
            "response_raw": finding.response_raw,
        })
        finding.poc_artifacts = artifacts
        finding.steps_to_reproduce = artifacts.get("steps_to_reproduce")

    await db.commit()
