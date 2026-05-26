import logging
import os
import httpx
from sqlalchemy import select, func
from awap.core.database import AsyncSessionLocal
from awap.models.scan import Scan
from awap.models.target import Target
from awap.models.finding import Finding
from awap.models.setting import SystemSetting
from awap.core.mailer import send_scan_email

logger = logging.getLogger(__name__)

async def dispatch_scan_complete_alerts(scan_id: str, target_id: str):
    """
    Orchestrates notifications for scan completion (Email, Telegram, Slack).
    """
    logger.info(f"Dispatching completion alerts for scan {scan_id}")
    
    async with AsyncSessionLocal() as db:
        # 1. Fetch Target, Scan, and Settings
        target = await db.scalar(select(Target).filter(Target.id == target_id))
        scan = await db.scalar(select(Scan).filter(Scan.id == scan_id))
        settings_res = await db.execute(select(SystemSetting).filter(SystemSetting.id == "default"))
        settings = settings_res.scalar()
        
        if not target or not scan:
            logger.error(f"Target {target_id} or Scan {scan_id} not found in database for alerting")
            return
            
        if not settings:
            logger.warning("No SystemSetting found in database. Using default unconfigured notifications.")
            return

        # 2. Query findings severity distribution
        crit_count = await db.scalar(select(func.count(Finding.id)).filter(Finding.scan_id == scan_id, Finding.severity == "CRITICAL"))
        high_count = await db.scalar(select(func.count(Finding.id)).filter(Finding.scan_id == scan_id, Finding.severity == "HIGH"))
        med_count = await db.scalar(select(func.count(Finding.id)).filter(Finding.scan_id == scan_id, Finding.severity == "MEDIUM"))
        low_count = await db.scalar(select(func.count(Finding.id)).filter(Finding.scan_id == scan_id, Finding.severity == "LOW"))
        info_count = await db.scalar(select(func.count(Finding.id)).filter(Finding.scan_id == scan_id, Finding.severity == "INFO"))
        
        severity_counts = {
            "CRITICAL": crit_count or 0,
            "HIGH": high_count or 0,
            "MEDIUM": med_count or 0,
            "LOW": low_count or 0,
            "INFO": info_count or 0,
        }
        
        total_vulns = sum(severity_counts.values())
        target_name = target.name or target.domain
        target_url = target.base_url or target.domain

        # Determine report path
        pdf_report_path = os.path.join("reports", scan_id, "report_tech.pdf")
        if not os.path.exists(pdf_report_path):
            legacy_pdf = f"reports/AWAP_Scan_Report_{scan_id}.pdf"
            if os.path.exists(legacy_pdf):
                pdf_report_path = legacy_pdf
            else:
                pdf_report_path = None

        # 3. Accumulate Alert Tasks for concurrent execution
        alert_tasks = []

        if settings.email_enabled and settings.email_alert:
            import asyncio
            loop = asyncio.get_event_loop()
            # Run blocking send_scan_email in executor
            alert_tasks.append(
                loop.run_in_executor(
                    None,
                    send_scan_email,
                    settings.email_alert,
                    target_name,
                    target_url,
                    scan_id,
                    severity_counts,
                    pdf_report_path
                )
            )

        # 4. Slack Notification
        if settings.slack_enabled and settings.slack_webhook:
            alert_tasks.append(
                send_slack_alert(settings.slack_webhook, target_name, target_url, scan_id, severity_counts, total_vulns)
            )

        # 5. Telegram Notification
        if settings.telegram_enabled and settings.telegram_token and settings.telegram_chat_id:
            alert_tasks.append(
                send_telegram_alert(settings.telegram_token, settings.telegram_chat_id, target_name, target_url, scan_id, severity_counts, total_vulns)
            )

        # 6. Execute all alerts concurrently to minimize latency
        if alert_tasks:
            import asyncio
            results = await asyncio.gather(*alert_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Alert task {i} raised an exception: {result}", exc_info=result)


async def send_slack_alert(webhook_url: str, target_name: str, target_url: str, scan_id: str, severity_counts: dict, total_vulns: int):
    payload = {
        "text": f"🚨 *AWAP-Ai Security Scan Completed!*\n"
                f"*Target:* {target_name} ({target_url})\n"
                f"*Scan ID:* `{scan_id}`\n\n"
                f"*Severity Summary:* ({total_vulns} total findings)\n"
                f"• 🔴 *CRITICAL:* {severity_counts.get('CRITICAL', 0)}\n"
                f"• 🟠 *HIGH:* {severity_counts.get('HIGH', 0)}\n"
                f"• 🟡 *MEDIUM:* {severity_counts.get('MEDIUM', 0)}\n"
                f"• 🔵 *LOW:* {severity_counts.get('LOW', 0)}\n\n"
                f"Detailed reports are available on the Platform Dashboard."
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code != 200:
                logger.error(f"Slack webhook failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")


async def send_telegram_alert(token: str, chat_id: str, target_name: str, target_url: str, scan_id: str, severity_counts: dict, total_vulns: int):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    text = (
        f"🚨 **AWAP-Ai Security Scan Completed!**\n\n"
        f"**Target:** {target_name}\n"
        f"**Endpoint:** `{target_url}`\n"
        f"**Scan Run ID:** `{scan_id}`\n\n"
        f"📊 **Vulnerabilities Discovered ({total_vulns} total):**\n"
        f"• 🔴 Critical: `{severity_counts.get('CRITICAL', 0)}`\n"
        f"• 🟠 High: `{severity_counts.get('HIGH', 0)}`\n"
        f"• 🟡 Medium: `{severity_counts.get('MEDIUM', 0)}`\n"
        f"• 🔵 Low: `{severity_counts.get('LOW', 0)}`\n"
        f"• ⚪ Info: `{severity_counts.get('INFO', 0)}`\n\n"
        f"Select a report format below to download it directly:"
    )

    # Inline Keyboard for report downloads
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "📄 Technical Report (PDF)", "callback_data": f"download:pdf:tech:{scan_id}"},
                {"text": "📊 Executive Report (PDF)", "callback_data": f"download:pdf:exec:{scan_id}"}
            ],
            [
                {"text": "🛡️ Compliance Report (PDF)", "callback_data": f"download:pdf:compliance:{scan_id}"},
                {"text": "💰 Bounty Report (PDF)", "callback_data": f"download:pdf:bounty:{scan_id}"}
            ],
            [
                {"text": "📝 Technical Report (MD)", "callback_data": f"download:md:tech:{scan_id}"},
                {"text": "📂 CSV Findings", "callback_data": f"download:csv:all:{scan_id}"}
            ]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.error(f"Telegram alert failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
