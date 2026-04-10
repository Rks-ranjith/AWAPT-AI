from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from datetime import datetime
import os
import tempfile

def generate_scan_report(db: Session, scan, target, findings) -> str:
    """Generates a PDF report for a given scan and returns the file path."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    
    doc = SimpleDocTemplate(path, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph(f"AWAP-AI Security Scan Report", title_style))
    elements.append(Spacer(1, 12))
    
    # Target Info
    elements.append(Paragraph(f"<b>Target:</b> {target.base_url}", normal_style))
    elements.append(Paragraph(f"<b>Scan Date:</b> {scan.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}", normal_style))
    status_text = scan.status
    if scan.end_time:
         status_text += f" (completed at {scan.end_time.strftime('%H:%M:%S UTC')})"
    elements.append(Paragraph(f"<b>Status:</b> {status_text}", normal_style))
    elements.append(Spacer(1, 24))
    
    # Summary Table
    # Count severities
    severities = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        sev = f.severity.upper()
        if sev in severities:
            severities[sev] += 1
            
    elements.append(Paragraph("<b>Executive Summary</b>", styles['Heading2']))
    summary_data = [
        ["Severity", "Count"],
        ["CRITICAL", str(severities["CRITICAL"])],
        ["HIGH", str(severities["HIGH"])],
        ["MEDIUM", str(severities["MEDIUM"])],
        ["LOW", str(severities["LOW"])],
    ]
    t = Table(summary_data, colWidths=[100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 24))
    
    # Finding Details
    elements.append(Paragraph("<b>Detailed Findings & AI Intelligence</b>", styles['Heading2']))
    for f in findings:
        elements.append(Paragraph(f"<b>Vulnerability:</b> {f.vuln_class}", normal_style))
        elements.append(Paragraph(f"<b>Severity:</b> {f.severity}", normal_style))
        elements.append(Paragraph(f"<b>Confidence:</b> {f.confidence}%", normal_style))
        
        if f.ai_summary:
            elements.append(Paragraph(f"<b>AI Insight:</b> {f.ai_summary}", normal_style))
            
        elements.append(Paragraph(f"<b>Endpoint:</b> {f.endpoint_url}", normal_style))
        elements.append(Paragraph(f"<b>Method:</b> {f.method}", normal_style))
        elements.append(Paragraph(f"<b>Payload Snippet:</b>", normal_style))
        
        req_snippet = (f.request_raw[:300] + '...') if f.request_raw and len(f.request_raw) > 300 else str(f.request_raw)
        
        code_style = ParagraphStyle('Code', parent=normal_style, fontName='Courier', fontSize=7, backColor=colors.lightgrey, textColor=colors.black)
        elements.append(Paragraph(req_snippet, code_style))
        elements.append(Spacer(1, 15))
        
    # Compliance Section
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Compliance & Regulation Context</b>", styles['Heading2']))
    compliance_text = """
    This report identifies technical vulnerabilities that may impact compliance with standards such as PCI-DSS (Requirement 6.5), 
    OWASP Top 10 (2021), and GDPR (Article 32 - Security of Processing). The AI-driven verification engine has confirmed 
    these findings to reduce false-positive noise for remediation teams.
    """
    elements.append(Paragraph(compliance_text, normal_style))
        
    doc.build(elements)
    return path
