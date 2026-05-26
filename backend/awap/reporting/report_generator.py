"""
Production report generator for AWAP-Ai.
Supports executive, technical, compliance, and bug-bounty (HackerOne-style) templates.
"""
from __future__ import annotations

import csv
import json
import os
import urllib.parse
from datetime import datetime, timezone
from io import StringIO
from typing import Any
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# CWE / OWASP / PCI mappings for compliance and bounty exports
CWE_BY_VULN: dict[str, str] = {
    "SQL_INJECTION": "CWE-89",
    "XSS": "CWE-79",
    "XSS_REFLECTED": "CWE-79",
    "XSS_DOM": "CWE-79",
    "SSRF": "CWE-918",
    "SSRF_BLIND": "CWE-918",
    "IDOR": "CWE-639",
    "PATH_TRAVERSAL": "CWE-22",
    "CMD_INJECTION": "CWE-78",
    "NOSQL_INJECTION": "CWE-943",
    "OPEN_REDIRECT": "CWE-601",
    "CORS_MISCONFIG": "CWE-942",
    "JWT_ATTACK": "CWE-347",
    "GRAPHQL_INTROSPECTION": "CWE-200",
    "PROTOTYPE_POLLUTION": "CWE-1321",
    "SECURITY_HEADERS": "CWE-693",
    "SUBDOMAIN_TAKEOVER": "CWE-350",
    "CLOUD_LEAK": "CWE-200",
    "LLM_PROMPT_INJECTION": "CWE-74",
}

OWASP_BY_VULN: dict[str, str] = {
    "SQL_INJECTION": "A03:2021 Injection",
    "XSS": "A03:2021 Injection",
    "XSS_REFLECTED": "A03:2021 Injection",
    "SSRF": "A10:2021 SSRF",
    "IDOR": "A01:2021 Broken Access Control",
    "PATH_TRAVERSAL": "A01:2021 Broken Access Control",
    "CMD_INJECTION": "A03:2021 Injection",
    "SECURITY_HEADERS": "A05:2021 Security Misconfiguration",
}

PCI_CONTROLS: dict[str, str] = {
    "SQL_INJECTION": "PCI DSS 6.5.1 — Injection flaws",
    "XSS": "PCI DSS 6.5.7 — Cross-site scripting",
    "SSRF": "PCI DSS 6.5.10 — Broken authentication and session management",
    "IDOR": "PCI DSS 7.1 — Restrict access to cardholder data",
    "SECURITY_HEADERS": "PCI DSS 6.5.10 — Secure configurations",
}

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

VALID_TEMPLATES = frozenset({"exec", "tech", "compliance", "bounty"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def poc_curl(finding: dict[str, Any]) -> str:
    url = finding.get("url", "")
    param = finding.get("param")
    payload = finding.get("payload") or ""
    if not url:
        return "# No URL available"
    if param:
        sep = "&" if "?" in url else "?"
        encoded = urllib.parse.quote(str(payload), safe="")
        return f"curl -s -i '{url}{sep}{param}={encoded}'"
    return f"curl -s -i '{url}'"


def poc_python(finding: dict[str, Any]) -> str:
    url = finding.get("url", "")
    param = finding.get("param")
    payload = finding.get("payload") or ""
    if param:
        return (
            "import requests\n"
            f"r = requests.get({url!r}, params={{\"{param}\": {payload!r}}})\n"
            "print(r.status_code, r.text[:500])"
        )
    return f"import requests\nr = requests.get({url!r})\nprint(r.status_code, r.text[:500])"


def _title_for_finding(f: dict[str, Any], target: str) -> str:
    vc = (f.get("vuln_class") or "Vulnerability").replace("_", " ").title()
    param = f.get("param")
    if param:
        return f"{vc} in `{param}` parameter on {target}"
    return f"{vc} on {target}"


def finding_to_record(f: Any, target_domain: str) -> dict[str, Any]:
    """Normalize ORM finding into architecture §13.1 finding schema."""
    from awap.core.poc_builder import build_poc_artifacts, bounty_markdown_report

    if hasattr(f, "vuln_class"):
        vuln_class = f.vuln_class
        severity = f.severity
        url = f.url
        method = getattr(f, "method", None) or "GET"
        param = f.param
        parameter_type = getattr(f, "parameter_type", None) or "URL_PARAM"
        payload = f.payload
        evidence = f.evidence
        request_raw = f.request_raw
        response_raw = f.response_raw
        description = f.description
        remediation = f.remediation
        impact = getattr(f, "impact", None)
        steps = getattr(f, "steps_to_reproduce", None)
        poc_artifacts = getattr(f, "poc_artifacts", None)
        cvss_score = f.cvss_score
        cvss_vector = f.cvss_vector
        cwe_id = f.cwe_id
        confidence = f.confidence
        false_positive = f.false_positive
        confirmed = f.confirmed
        finding_id = str(f.id)
        discovered_at = f.discovered_at.isoformat() if f.discovered_at else _utc_now_iso()
    else:
        vuln_class = f.get("vuln_class", "UNKNOWN")
        severity = f.get("severity", "INFO")
        url = f.get("url", "")
        method = f.get("method", "GET")
        param = f.get("param")
        parameter_type = f.get("parameter_type", "URL_PARAM")
        payload = f.get("payload")
        evidence = f.get("evidence")
        request_raw = f.get("request_raw")
        response_raw = f.get("response_raw")
        description = f.get("description")
        remediation = f.get("remediation")
        impact = f.get("impact")
        steps = f.get("steps_to_reproduce")
        poc_artifacts = f.get("poc_artifacts")
        cvss_score = f.get("cvss_score")
        cvss_vector = f.get("cvss_vector")
        cwe_id = f.get("cwe_id")
        confidence = f.get("confidence", 0.8)
        false_positive = f.get("false_positive", False)
        confirmed = f.get("confirmed", False)
        finding_id = str(f.get("id", ""))
        discovered_at = f.get("discovered_at", _utc_now_iso())

    cwe = cwe_id or CWE_BY_VULN.get(vuln_class.upper(), "CWE-200")
    base = {
        "finding_id": finding_id,
        "vuln_class": vuln_class,
        "severity": severity,
        "url": url,
        "method": method,
        "param": param,
        "parameter_type": parameter_type,
        "payload": payload,
        "evidence": evidence,
        "request_raw": request_raw,
        "response_raw": (response_raw or "")[:8000] if response_raw else None,
        "description": description,
        "remediation": remediation,
        "impact": impact,
        "steps_to_reproduce": steps,
        "cvss_score": cvss_score,
        "cvss_vector": cvss_vector,
        "cwe_id": cwe,
        "owasp_category": OWASP_BY_VULN.get(vuln_class.upper(), "A06:2021 Vulnerable Components"),
        "pci_control": PCI_CONTROLS.get(vuln_class.upper()),
        "confidence": confidence,
        "false_positive": false_positive,
        "confirmed": confirmed,
        "discovered_at": discovered_at,
        "title": None,
    }
    if not base.get("method"):
        base["method"] = "GET"
    artifacts = poc_artifacts if poc_artifacts else build_poc_artifacts(base)
    base["poc_artifacts"] = artifacts
    base["poc_curl"] = artifacts.get("poc_curl") or poc_curl(base)
    base["poc_python"] = artifacts.get("poc_python") or poc_python(base)
    base["steps_to_reproduce"] = base.get("steps_to_reproduce") or artifacts.get("steps_to_reproduce")
    base["impact"] = base.get("impact") or _impact_text(base)
    base["title"] = _title_for_finding(base, target_domain)
    base["bounty_markdown"] = bounty_markdown_report(base, target_domain)
    return base


def bounty_submission(f: dict[str, Any], program: str = "") -> dict[str, Any]:
    """HackerOne / Bugcrowd compatible submission object."""
    sev = (f.get("severity") or "medium").lower()
    rating_map = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "info": "none",
    }
    impact = _impact_text(f)
    body = _bounty_markdown_single(f, program)
    return {
        "title": f.get("title"),
        "severity_rating": rating_map.get(sev, "medium"),
        "weakness": {"id": f.get("cwe_id", "CWE-200")},
        "asset": f.get("url"),
        "vulnerability_information": body,
        "impact": impact,
        "cvss_vector": f.get("cvss_vector"),
        "cvss_score": f.get("cvss_score"),
        "metadata": {
            "generated_by": "AWAP-Ai",
            "finding_id": f.get("finding_id"),
            "confidence": f.get("confidence"),
            "false_positive": f.get("false_positive"),
        },
    }


def _impact_text(f: dict[str, Any]) -> str:
    vc = (f.get("vuln_class") or "").upper()
    impacts = {
        "SQL_INJECTION": "An attacker may read, modify, or delete database records, potentially exposing sensitive user or payment data.",
        "XSS": "An attacker may execute arbitrary JavaScript in victims' browsers, enabling session hijacking or account takeover.",
        "SSRF": "An attacker may force the server to request internal resources, potentially accessing cloud metadata or internal services.",
        "IDOR": "An attacker may access or modify resources belonging to other users without authorization.",
        "RCE": "Remote code execution may allow full server compromise.",
    }
    for key, text in impacts.items():
        if key in vc:
            return text
    return (
        f"A successful exploitation of this {f.get('vuln_class', 'issue')} could compromise "
        "confidentiality, integrity, or availability of the affected application."
    )


def _bounty_markdown_single(f: dict[str, Any], program: str = "") -> str:
    from awap.core.poc_builder import bounty_markdown_report
    if f.get("bounty_markdown"):
        return f["bounty_markdown"]
    return bounty_markdown_report(f, program)


async def fetch_scan_report_data(scan_id: str, target_id: str) -> dict[str, Any] | None:
    from sqlalchemy import select

    from awap.core.database import AsyncSessionLocal
    from awap.models.finding import Finding
    from awap.models.scan import Scan
    from awap.models.target import Target

    async with AsyncSessionLocal() as db:
        scan = await db.scalar(select(Scan).filter(Scan.id == scan_id))
        target = await db.scalar(select(Target).filter(Target.id == target_id))
        if not scan or not target:
            return None
        from sqlalchemy import desc, nulls_last
        res = await db.execute(
            select(Finding)
            .filter(Finding.scan_id == scan_id, Finding.false_positive == False)
            .order_by(nulls_last(desc(Finding.cvss_score)))
        )
        findings = res.scalars().all()

    records = [finding_to_record(f, target.domain) for f in findings]
    records.sort(
        key=lambda x: (
            SEVERITY_ORDER.get((x.get("severity") or "INFO").upper(), 5),
            -(x.get("cvss_score") or 0),
        )
    )
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for r in records:
        sev = (r.get("severity") or "INFO").upper()
        if sev in counts:
            counts[sev] += 1

    return {
        "scan_id": str(scan.id),
        "target_id": str(target.id),
        "target": target.domain,
        "scan_state": scan.state,
        "scan_profile": scan.profile,
        "generated_at": _utc_now_iso(),
        "severity_counts": counts,
        "findings": records,
        "bounty_submissions": [bounty_submission(r) for r in records],
    }


class ReportGenerator:
    def __init__(self, scan_result: dict[str, Any], template: str = "tech"):
        self.data = scan_result
        self.template = template if template in VALID_TEMPLATES else "tech"

    def generate_json(self, output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2, default=str)

    def generate_bounty_json(self, output_path: str) -> None:
        payload = {
            "program": self.data.get("target", ""),
            "generated_at": self.data.get("generated_at"),
            "scan_id": self.data.get("scan_id"),
            "submissions": self.data.get("bounty_submissions", []),
        }
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)

    def generate_csv(self, output_path: str) -> None:
        fields = [
            "finding_id",
            "severity",
            "vuln_class",
            "cwe_id",
            "cvss_score",
            "url",
            "param",
            "payload",
            "confidence",
            "description",
            "remediation",
            "poc_curl",
        ]
        with open(output_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in self.data.get("findings", []):
                writer.writerow(row)

    def generate_markdown(self, output_path: str) -> None:
        content = self._build_markdown()
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def _build_markdown(self) -> str:
        d = self.data
        tpl = self.template
        counts = d.get("severity_counts", {})
        lines = [
            f"# AWAP-Ai Security Report — {d.get('target', 'Unknown')}",
            f"\n**Scan ID:** `{d.get('scan_id')}`  ",
            f"**Generated:** {d.get('generated_at')}  ",
            f"**Template:** {tpl}\n",
        ]
        if tpl == "exec":
            lines.extend([
                "## Executive Summary\n",
                f"This assessment identified **{len(d.get('findings', []))}** validated findings: "
                f"{counts.get('CRITICAL', 0)} Critical, {counts.get('HIGH', 0)} High, "
                f"{counts.get('MEDIUM', 0)} Medium.\n",
                "Immediate remediation is recommended for Critical and High severity issues "
                "to reduce risk of data breach, service disruption, and regulatory exposure.\n",
            ])
            for f in d.get("findings", [])[:10]:
                lines.append(
                    f"- **{f.get('severity')}** — {f.get('title')} (CVSS {f.get('cvss_score', 'N/A')})"
                )
            return "\n".join(lines)

        if tpl == "compliance":
            lines.append("## Compliance Mapping (PCI-DSS)\n")
            lines.append("| Finding | Severity | CWE | PCI Control |")
            lines.append("|---------|----------|-----|-------------|")
            for f in d.get("findings", []):
                pci = f.get("pci_control") or "General security hardening"
                lines.append(
                    f"| {f.get('vuln_class')} | {f.get('severity')} | {f.get('cwe_id')} | {pci} |"
                )
            lines.append("\n## OWASP Top 10 Mapping\n")
            for f in d.get("findings", []):
                lines.append(f"- **{f.get('vuln_class')}** → {f.get('owasp_category')}")
            return "\n".join(lines)

        if tpl == "bounty":
            lines.append("## Bug Bounty Submission Pack\n")
            lines.append(
                "Copy each section below into HackerOne, Bugcrowd, or your program's submission form.\n"
            )
            for i, f in enumerate(d.get("findings", []), 1):
                lines.append(f"\n---\n\n# Submission {i}: {f.get('title')}\n")
                lines.append(_bounty_markdown_single(f, d.get("target", "")))
            return "\n".join(lines)

        # tech (default)
        lines.append("## Technical Findings\n")
        for f in d.get("findings", []):
            lines.extend([
                f"\n### {f.get('title')}\n",
                f"- **Severity:** {f.get('severity')} | **CVSS:** {f.get('cvss_score')} | **CWE:** {f.get('cwe_id')}\n",
                f"- **URL:** `{f.get('url')}`\n",
                f"- **Parameter:** `{f.get('param') or 'N/A'}`\n",
                f"\n**Description:** {f.get('description') or 'N/A'}\n",
                f"\n**Remediation:** {f.get('remediation') or 'Apply secure coding practices and input validation.'}\n",
                "\n**PoC (curl):**\n```bash\n" + (f.get("poc_curl") or "") + "\n```\n",
            ])
            if f.get("request_raw"):
                lines.append("**Request:**\n```http\n" + f["request_raw"][:1200] + "\n```\n")
        return "\n".join(lines)

    def generate_pdf(self, output_path: str) -> None:
        doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch, leftMargin=0.75 * inch, rightMargin=0.75 * inch)
        styles = getSampleStyleSheet()
        
        # Define clean, modern typography styles
        code_style = ParagraphStyle(
            "Code", parent=styles["Code"], fontSize=6.5, leading=8.5, wordWrap="CJK", textColor=colors.HexColor("#a5b4fc")
        )
        body_style = ParagraphStyle(
            "BodyTextCustom", parent=styles["BodyText"], fontSize=9, leading=13, textColor=colors.HexColor("#1e293b")
        )
        h1_style = ParagraphStyle(
            "Heading1Custom", parent=styles["Heading1"], fontSize=18, leading=22, textColor=colors.HexColor("#1e3a5f")
        )
        h2_style = ParagraphStyle(
            "Heading2Custom", parent=styles["Heading2"], fontSize=13, leading=16, textColor=colors.HexColor("#7f1d1d")
        )
        h3_style = ParagraphStyle(
            "Heading3Custom", parent=styles["Heading3"], fontSize=10, leading=12, textColor=colors.HexColor("#334155")
        )
        meta_style = ParagraphStyle(
            "MetaText", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#64748b")
        )
        bold_normal = ParagraphStyle(
            "BoldNormal", parent=styles["Normal"], fontSize=9, leading=12, fontName="Helvetica-Bold"
        )
        
        story = []
        d = self.data
        findings = d.get("findings", [])
        counts = d.get("severity_counts", {})

        def html_escape(text: str) -> str:
            return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def make_code_box(title: str, content: str):
            escaped = html_escape(content or "")
            content_display = escaped[:1500]
            if len(content or "") > 1500:
                content_display += "\n... [TRUNCATED FOR PDF PRINTING] ..."
            formatted = content_display.replace("\n", "<br/>").replace(" ", "&nbsp;")
            p = Paragraph(formatted, code_style)
            t = Table([[p]], colWidths=[480])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
            ]))
            return t

        # =========================================================================
        # 1. EXECUTIVE SUMMARY TEMPLATE (High-Level Business Posture)
        # =========================================================================
        if self.template == "exec":
            story.append(Paragraph("AWAP-Ai Executive Security Assessment Report", h1_style))
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"Target: <b>{d.get('target', '')}</b>", body_style))
            story.append(Paragraph(f"Scan ID: {d.get('scan_id')} | Generated: {d.get('generated_at')}", meta_style))
            story.append(Spacer(1, 20))

            # Risk Rating Banner
            max_sev = "LOW"
            banner_color = colors.HexColor("#15803d") # Green
            if counts.get("CRITICAL", 0) > 0:
                max_sev = "CRITICAL"
                banner_color = colors.HexColor("#7f1d1d")
            elif counts.get("HIGH", 0) > 0:
                max_sev = "HIGH"
                banner_color = colors.HexColor("#c2410c")
            elif counts.get("MEDIUM", 0) > 0:
                max_sev = "MEDIUM"
                banner_color = colors.HexColor("#1d4ed8")
                
            risk_p = Paragraph(f"<font color='white'><b>OVERALL PLATFORM RISK RATING: {max_sev}</b></font>", bold_normal)
            risk_table = Table([[risk_p]], colWidths=[480])
            risk_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), banner_color),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(risk_table)
            story.append(Spacer(1, 16))

            story.append(Paragraph("Executive Overview", h2_style))
            exec_intro = (
                f"AWAP-Ai conducted an automated vulnerability and security assessment on "
                f"the target domain <b>{d.get('target', '')}</b>. The objective of this assessment was to identify "
                f"exposed security vulnerabilities, input-validation weaknesses, and server-side misconfigurations "
                f"that present business risks to operations, compliance posture, and data security."
            )
            story.append(Paragraph(exec_intro, body_style))
            story.append(Spacer(1, 10))
            
            exec_posture = (
                f"A total of <b>{len(findings)}</b> validated vulnerabilities were discovered. "
                f"The highest severity finding resolved is evaluated at a level of <b>{max_sev}</b>. "
                f"It is highly recommended that immediate remediation schedules be implemented to address any Critical "
                f"and High risk areas to prevent potential unauthorized access, data leaks, or service disruptions."
            )
            story.append(Paragraph(exec_posture, body_style))
            story.append(Spacer(1, 16))

            story.append(Paragraph("Findings Breakdown By Severity", h3_style))
            story.append(Spacer(1, 6))
            table_data = [
                ["Severity Class", "Count", "Recommended Action Plan"],
                ["Critical", str(counts.get("CRITICAL", 0)), "Immediate Patching (Within 24 Hours)"],
                ["High", str(counts.get("HIGH", 0)), "Schedules Hotfix (Within 7 Days)"],
                ["Medium", str(counts.get("MEDIUM", 0)), "Standard Remediation Cycle (Within 30 Days)"],
                ["Low", str(counts.get("LOW", 0)), "Include in standard maintenance tasks"]
            ]
            t = Table(table_data, colWidths=[110, 60, 310])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(t)
            story.append(Spacer(1, 20))

            story.append(Paragraph("Top Business Risk Findings Summary", h2_style))
            story.append(Spacer(1, 8))
            for i, f in enumerate(findings[:8], 1):
                f_title = Paragraph(f"<b>{i}. {f.get('title')}</b> ({f.get('severity')} - CVSS {f.get('cvss_score', 'N/A')})", bold_normal)
                story.append(f_title)
                story.append(Paragraph(f"URL: <font face='Helvetica-Oblique'>{f.get('url')}</font>", meta_style))
                story.append(Paragraph(f"Impact: {f.get('impact')}", body_style))
                story.append(Spacer(1, 8))

            doc.build(story)
            return

        # =========================================================================
        # 2. PCI-DSS & COMPLIANCE TEMPLATE (Regulatory Audits)
        # =========================================================================
        if self.template == "compliance":
            story.append(Paragraph("AWAP-Ai Compliance & Regulatory Report", h1_style))
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"Regulatory Audit Target: <b>{d.get('target', '')}</b>", body_style))
            story.append(Paragraph(f"Scope: PCI DSS v4.0 & OWASP Top 10 Mappings", meta_style))
            story.append(Paragraph(f"Scan ID: {d.get('scan_id')} | Generated: {d.get('generated_at')}", meta_style))
            story.append(Spacer(1, 16))

            story.append(Paragraph("Compliance Overview", h2_style))
            story.append(Paragraph(
                "This report details compliance mappings for PCI DSS (Payment Card Industry Data Security Standard) "
                "v4.0 Requirement 6 (Develop and Maintain Secure Systems and Software) and OWASP Top 10 guidelines. "
                "A 'FAIL' status is assigned to any control violation with Medium, High, or Critical severity.",
                body_style
            ))
            story.append(Spacer(1, 16))

            story.append(Paragraph("PCI-DSS Requirements Mappings", h3_style))
            story.append(Spacer(1, 8))
            
            rows = [["Control ID", "PCI DSS Requirement", "Vulnerability Class", "Severity", "Audit Status"]]
            for f in findings:
                status = "FAIL" if f.get("severity") in ("CRITICAL", "HIGH", "MEDIUM") else "PASS"
                pci = f.get("pci_control") or "Requirement 6.2.4 — Software development rules"
                rows.append([
                    pci.split("—")[0].strip(),
                    pci.split("—")[-1].strip(),
                    f.get("vuln_class", ""),
                    f.get("severity", ""),
                    status
                ])
                
            if len(rows) > 1:
                t = Table(rows, colWidths=[90, 160, 120, 60, 50])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("ALIGN", (4, 1), (4, -1), "CENTER"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ]))
                story.append(t)
            story.append(Spacer(1, 20))

            story.append(Paragraph("Detailed Regulatory Violations & Control Mappings", h2_style))
            story.append(Spacer(1, 10))
            for i, f in enumerate(findings, 1):
                pci = f.get("pci_control") or "PCI DSS 6.2.4 — Secure software guidelines"
                owasp = f.get("owasp_category") or "A06:2021 Vulnerable Components"
                
                story.append(Paragraph(f"<b>Violation #{i}: {f.get('title')}</b>", bold_normal))
                story.append(Paragraph(f"<b>Control Link:</b> {pci} | <b>OWASP Link:</b> {owasp}", meta_style))
                story.append(Paragraph(f"<b>Audit Threat Description:</b> The application endpoint at <font face='Helvetica-Oblique'>{f.get('url')}</font> was fuzzed and verified to contain a {f.get('vuln_class')} vulnerability. An auditor will flag this as a critical deviation from Requirement 6 standard.", body_style))
                story.append(Paragraph(f"<b>Remediation Requirement:</b> {f.get('remediation')}", body_style))
                story.append(Spacer(1, 12))

            doc.build(story)
            return

        # =========================================================================
        # 3. BUG BOUNTY EXPORT TEMPLATE (Submission Ready Templates)
        # =========================================================================
        if self.template == "bounty":
            story.append(Paragraph("AWAP-Ai Bug Bounty Submission Report", h1_style))
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"Bounty Program Target: <b>{d.get('target', '')}</b>", body_style))
            story.append(Paragraph(f"Format: HackerOne & Bugcrowd Ready Submissions", meta_style))
            story.append(Paragraph(f"Total Exported Submissions: {len(findings)}", meta_style))
            story.append(Spacer(1, 20))

            for i, f in enumerate(findings, 1):
                if i > 1:
                    story.append(PageBreak())
                story.append(Paragraph(f"Submission #{i}: {f.get('title')}", h2_style))
                story.append(Spacer(1, 10))

                story.append(Paragraph("Description", h3_style))
                story.append(Paragraph(f.get("description") or "No description", body_style))
                story.append(Spacer(1, 10))

                story.append(Paragraph("Steps to Reproduce", h3_style))
                steps = f.get("steps_to_reproduce") or "No reproduction steps available."
                story.append(Paragraph(steps.replace("\n", "<br/>"), body_style))
                story.append(Spacer(1, 10))

                story.append(Paragraph("Proof of Concept (PoC) curl Command", h3_style))
                story.append(Spacer(1, 4))
                story.append(make_code_box("curl", f.get("poc_curl", "")))
                story.append(Spacer(1, 10))

                story.append(Paragraph("Exploit Impact Description", h3_style))
                story.append(Paragraph(f.get("impact") or "No impact listed.", body_style))
                story.append(Spacer(1, 10))

                story.append(Paragraph("Suggested Remediation", h3_style))
                story.append(Paragraph(f.get("remediation") or "Remediate code input verification.", body_style))

            doc.build(story)
            return

        # =========================================================================
        # 4. TECHNICAL DEEP-DIVE TEMPLATE (Default - Full Logs, PoCs and Details)
        # =========================================================================
        story.append(Paragraph("AWAP-Ai Technical Vulnerability Report", h1_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"Target URL: <b>{d.get('target', '')}</b>", body_style))
        story.append(Paragraph(f"Scan ID: {d.get('scan_id')} | Generated: {d.get('generated_at')}", meta_style))
        story.append(Spacer(1, 16))

        story.append(Paragraph("Executive Summary", h2_style))
        story.append(
            Paragraph(
                f"Total findings: {len(findings)} — "
                f"Critical: {counts.get('CRITICAL', 0)}, High: {counts.get('HIGH', 0)}, "
                f"Medium: {counts.get('MEDIUM', 0)}, Low: {counts.get('LOW', 0)}",
                body_style,
            )
        )
        story.append(Spacer(1, 12))

        story.append(Paragraph("Findings Overview Table", h2_style))
        story.append(Spacer(1, 6))
        table_data = [["Severity", "Vulnerability Class", "CWE ID", "CVSS", "Target Endpoint URL"]]
        for f in findings:
            table_data.append([
                f.get("severity", ""),
                f.get("vuln_class", "")[:24],
                f.get("cwe_id", ""),
                str(f.get("cvss_score") or ""),
                (f.get("url") or "")[:55],
            ])
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[60, 90, 55, 40, 220])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7f1d1d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]))
            story.append(table)

        # Detailed Technical Sheets for Developers
        for f in findings:
            story.append(PageBreak())
            story.append(Paragraph(f.get("title", "Finding"), h2_style))
            story.append(Spacer(1, 6))
            
            # Metadata Summary Table
            meta_rows = [
                ["Severity:", f.get("severity"), "CVSS v3.1:", str(f.get("cvss_score") or "N/A")],
                ["CWE ID:", f.get("cwe_id"), "Parameter:", f.get("param") or "N/A"],
                ["Method:", f.get("method"), "Param Location:", f.get("parameter_type") or "URL_PARAM"]
            ]
            meta_tbl = Table(meta_rows, colWidths=[70, 150, 90, 170])
            meta_tbl.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#334155")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ]))
            story.append(meta_tbl)
            story.append(Spacer(1, 12))

            if f.get("description"):
                story.append(Paragraph("Vulnerability Description", h3_style))
                story.append(Paragraph(f.get("description"), body_style))
                story.append(Spacer(1, 10))

            if f.get("impact"):
                story.append(Paragraph("Impact Analysis", h3_style))
                story.append(Paragraph(f.get("impact"), body_style))
                story.append(Spacer(1, 10))

            story.append(Paragraph("Proof of Concept (PoC) Exploitation", h3_style))
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Copy-Pasteable cURL Script:</b>", body_style))
            story.append(Spacer(1, 2))
            story.append(make_code_box("curl", f.get("poc_curl", "")))
            
            story.append(Spacer(1, 8))
            story.append(Paragraph("<b>Copy-Pasteable Python Replay:</b>", body_style))
            story.append(Spacer(1, 2))
            story.append(make_code_box("python", f.get("poc_python", "")))
            story.append(Spacer(1, 12))

            # Include Raw HTTP request/response payloads if captured
            if f.get("request_raw"):
                story.append(Paragraph("Raw Captured HTTP Request", h3_style))
                story.append(Spacer(1, 4))
                story.append(make_code_box("request", f.get("request_raw")))
                story.append(Spacer(1, 12))

            if f.get("response_raw"):
                story.append(Paragraph("Raw Captured HTTP Response (Headers & Payload)", h3_style))
                story.append(Spacer(1, 4))
                story.append(make_code_box("response", f.get("response_raw")))
                story.append(Spacer(1, 12))

            if f.get("remediation"):
                story.append(Paragraph("Remediation & Secure Coding Guidelines", h3_style))
                story.append(Paragraph(f.get("remediation"), body_style))

        doc.build(story)


def _report_dir(scan_id: str) -> str:
    path = os.path.join("reports", str(scan_id))
    os.makedirs(path, exist_ok=True)
    return path


def generate_reports(scan_id: str, target_id: str, template: str = "tech") -> dict[str, str]:
    """Sync entry point for Celery worker."""
    import asyncio
    import concurrent.futures

    def _sync_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(fetch_scan_report_data(scan_id, target_id))
        finally:
            loop.close()

    try:
        loop = asyncio.get_running_loop()
        # Active loop detected: run in a separate thread with its own event loop to prevent loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as pool:
            data = pool.submit(_sync_runner).result()
    except RuntimeError:
        # No active running loop: run directly in this thread
        data = _sync_runner()

    if not data:
        return {}

    out_dir = _report_dir(scan_id)
    paths: dict[str, str] = {}
    templates = [template] if template in VALID_TEMPLATES else ["tech"]
    if template == "all":
        templates = list(VALID_TEMPLATES)

    rg_base = ReportGenerator(data)
    rg_base.generate_json(os.path.join(out_dir, "findings.json"))
    rg_base.generate_csv(os.path.join(out_dir, "findings.csv"))
    rg_base.generate_bounty_json(os.path.join(out_dir, "bounty_submissions.json"))
    paths["json"] = os.path.join(out_dir, "findings.json")
    paths["csv"] = os.path.join(out_dir, "findings.csv")
    paths["bounty_json"] = os.path.join(out_dir, "bounty_submissions.json")

    for tpl in templates:
        gen = ReportGenerator(data, template=tpl)
        pdf_path = os.path.join(out_dir, f"report_{tpl}.pdf")
        md_path = os.path.join(out_dir, f"report_{tpl}.md")
        gen.generate_pdf(pdf_path)
        gen.generate_markdown(md_path)
        paths[f"pdf_{tpl}"] = pdf_path
        paths[f"md_{tpl}"] = md_path

    # Backward-compatible legacy path
    legacy_pdf = f"reports/AWAP_Scan_Report_{scan_id}.pdf"
    os.makedirs("reports", exist_ok=True)
    ReportGenerator(data, template=template if template in VALID_TEMPLATES else "tech").generate_pdf(
        legacy_pdf
    )
    paths["pdf_legacy"] = legacy_pdf
    legacy_csv = f"reports/AWAP_Scan_Report_{scan_id}.csv"
    ReportGenerator(data).generate_csv(legacy_csv)
    paths["csv_legacy"] = legacy_csv

    return paths
