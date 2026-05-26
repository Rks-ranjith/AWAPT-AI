import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)

from awap.core.config import settings

# SMTP configurations from settings config
SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SMTP_USER
SMTP_PASSWORD = settings.SMTP_PASSWORD
SMTP_FROM = settings.SMTP_FROM

from typing import List, Union

def send_scan_email(
    to_email: Union[str, List[str]],
    target_name: str,
    target_url: str,
    scan_id: str,
    severity_counts: dict,
    pdf_report_path: str = None
):
    """
    Sends a scan completion email with attachment, or logs it locally if SMTP is not configured.
    """
    subject = f"[AWAP-Ai] Scan Completed: {target_name} ({target_url})"
    
    # HTML Content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #0d0f12;
                color: #e2e8f0;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background: #151922;
                border: 1px solid #1e293b;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            }}
            .header {{
                background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                color: #ffffff;
                font-size: 24px;
                font-weight: 900;
                letter-spacing: -0.025em;
            }}
            .content {{
                padding: 30px;
            }}
            .meta-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 25px;
            }}
            .meta-table td {{
                padding: 10px;
                border-bottom: 1px solid #1e293b;
            }}
            .meta-label {{
                font-weight: bold;
                color: #94a3b8;
                width: 30%;
            }}
            .meta-value {{
                color: #e2e8f0;
                font-family: monospace;
            }}
            .stats-grid {{
                display: grid;
                grid-template-cols: repeat(4, 1fr);
                gap: 10px;
                margin-bottom: 25px;
                text-align: center;
            }}
            .stat-card {{
                padding: 12px;
                border-radius: 12px;
                background: #0d0f12;
                border: 1px solid #1e293b;
            }}
            .stat-count {{
                font-size: 20px;
                font-weight: 800;
            }}
            .crit {{ color: #ef4444; border-top: 3px solid #ef4444; }}
            .high {{ color: #f97316; border-top: 3px solid #f97316; }}
            .med  {{ color: #eab308; border-top: 3px solid #eab308; }}
            .low  {{ color: #3b82f6; border-top: 3px solid #3b82f6; }}
            .footer {{
                background: #0d0f12;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #64748b;
                border-top: 1px solid #1e293b;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AWAP-Ai Security Intelligence</h1>
            </div>
            <div class="content">
                <p>Hello Admin,</p>
                <p>An automated security scan has successfully completed. Below is the telemetry summary of findings:</p>
                
                <table class="meta-table">
                    <tr>
                        <td class="meta-label">Friendly Name</td>
                        <td class="meta-value">{target_name}</td>
                    </tr>
                    <tr>
                        <td class="meta-label">Target Endpoint</td>
                        <td class="meta-value">{target_url}</td>
                    </tr>
                    <tr>
                        <td class="meta-label">Scan Run ID</td>
                        <td class="meta-value">{scan_id}</td>
                    </tr>
                </table>

                <h3 style="margin-top: 0; color: #94a3b8;">Vulnerability Severity Distribution</h3>
                <div class="stats-grid">
                    <div class="stat-card crit">
                        <div class="stat-count">{severity_counts.get("CRITICAL", 0)}</div>
                        <div style="font-size: 10px; font-weight: bold; margin-top: 4px;">CRITICAL</div>
                    </div>
                    <div class="stat-card high">
                        <div class="stat-count">{severity_counts.get("HIGH", 0)}</div>
                        <div style="font-size: 10px; font-weight: bold; margin-top: 4px;">HIGH</div>
                    </div>
                    <div class="stat-card med">
                        <div class="stat-count">{severity_counts.get("MEDIUM", 0)}</div>
                        <div style="font-size: 10px; font-weight: bold; margin-top: 4px;">MEDIUM</div>
                    </div>
                    <div class="stat-card low">
                        <div class="stat-count">{severity_counts.get("LOW", 0)}</div>
                        <div style="font-size: 10px; font-weight: bold; margin-top: 4px;">LOW</div>
                    </div>
                </div>

                <p>The detailed technical penetration testing report is attached to this email. You can also view details and initiate attacks in the Platform Engine Control Web UI.</p>
            </div>
            <div class="footer">
                AWAP-Ai Security System · Local Time: 2026-05-26
            </div>
        </div>
    </body>
    </html>
    """

    # If SMTP is not configured, fall back to logging the email to backend/logs/emails.log
    if not SMTP_HOST:
        os.makedirs("logs", exist_ok=True)
        log_path = os.path.join("logs", "emails.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"=== EMAIL ALERT SENT ===\n")
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Attached Report: {pdf_report_path}\n")
            f.write(f"HTML Content:\n{html_content}\n")
            f.write(f"========================\n\n")
        logger.warning(f"SMTP not configured. Email logged to {log_path}")
        return True

    # Real SMTP send
    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        # Normalize recipient list
        if isinstance(to_email, (list, tuple)):
            recipients = ", ".join(to_email)
        else:
            # Split comma/semicolon separated string into list
            recipients = ", ".join([addr.strip() for addr in to_email.replace(";", ",").split(",") if addr.strip()])
        msg["To"] = recipients

        # Create alternative container for body content
        body = MIMEMultipart("alternative")
        text_body = f"Hello Admin,\n\nAn automated security scan has successfully completed.\n\nTarget Name: {target_name}\nTarget URL: {target_url}\nScan ID: {scan_id}\n\nPlease find the detailed technical report attached.\n\nAWAP-Ai Security System"
        body.attach(MIMEText(text_body, "plain"))
        body.attach(MIMEText(html_content, "html"))
        msg.attach(body)

        # Attach PDF report if present
        if pdf_report_path and os.path.exists(pdf_report_path):
            filename = os.path.basename(pdf_report_path)
            with open(pdf_report_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={filename}",
                )
                msg.attach(part)

        # Connect and send — sendmail needs a list of individual addresses
        recipient_list = [addr.strip() for addr in recipients.split(",") if addr.strip()]
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            if SMTP_PORT == 587:
                server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, recipient_list, msg.as_string())
        logger.info(f"Email alert successfully sent to {recipients}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert via SMTP: {e}")
        # Log to file as absolute fallback
        os.makedirs("logs", exist_ok=True)
        log_path = os.path.join("logs", "emails.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"=== EMAIL FAILED (Logged as fallback) ===\n")
            f.write(f"Error: {e}\n")
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"HTML Content:\n{html_content}\n")
            f.write(f"=========================================\n\n")
        return False
