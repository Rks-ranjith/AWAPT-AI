import asyncio
import logging
import os
import urllib.parse
import httpx
from sqlalchemy import select, desc
from datetime import datetime
import uuid

from awap.core.database import AsyncSessionLocal
from awap.models.setting import SystemSetting
from awap.models.target import Target
from awap.models.scan import Scan
from awap.api import crud

logger = logging.getLogger(__name__)

async def start_telegram_bot():
    """
    Asynchronous background task that polls the Telegram Bot API.
    """
    logger.info("Initializing Telegram Bot background service...")
    offset = 0
    current_token = None
    
    while True:
        try:
            # 1. Load Telegram settings from DB
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(SystemSetting).filter(SystemSetting.id == "default"))
                settings = result.scalar()
                
            if not settings or not settings.telegram_enabled or not settings.telegram_token:
                current_token = None
                await asyncio.sleep(10)
                continue
                
            # If token changed, reset offset f
            if settings.telegram_token != current_token:
                logger.info("Telegram Bot token updated/detected. Reconnecting bot...")
                current_token = settings.telegram_token
                offset = 0
                
            # 2. Poll for updates
            url = f"https://api.telegram.org/bot{current_token}/getUpdates"
            params = {"offset": offset, "timeout": 8}
            
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    updates = response.json()
                    if updates.get("ok"):
                        for update in updates.get("result", []):
                            offset = update["update_id"] + 1
                            # Process update in background task to avoid blocking polling loop
                            asyncio.create_task(handle_telegram_update(update, current_token))
                elif response.status_code == 401:
                    logger.error("Telegram token is unauthorized. Please verify your Bot Token.")
                    await asyncio.sleep(30)
                else:
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Error in Telegram bot polling task: {e}")
            await asyncio.sleep(5)


async def handle_telegram_update(update: dict, token: str):
    """
    Processes incoming messages and callback queries.
    """
    try:
        # A. Handle Inline Keyboard Button Callback Queries
        if "callback_query" in update:
            await handle_callback_query(update["callback_query"], token)
            return

        # B. Handle Text Messages
        if "message" not in update or "text" not in update["message"]:
            return

        message = update["message"]
        chat_id = str(message["chat"]["id"])
        text = message["text"].strip()
        
        # Check and auto-pair chat ID if admin settings is empty
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SystemSetting).filter(SystemSetting.id == "default"))
            settings = result.scalar()
            if settings and settings.telegram_enabled and not settings.telegram_chat_id:
                settings.telegram_chat_id = chat_id
                await db.commit()
                await send_telegram_message(token, chat_id, f"✅ **Admin Chat ID successfully paired!**\nYour chat ID `{chat_id}` has been linked for scan alerts and reports.")

        # Command Dispatcher
        if text.startswith("/start") or text.startswith("/help"):
            await handle_help_command(token, chat_id)
        elif text.startswith("/status"):
            await handle_status_command(token, chat_id)
        elif text.startswith("/scan"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                await send_telegram_message(token, chat_id, "⚠️ **Usage:** `/scan <endpoint_url>`\nExample: `/scan http://localhost:4280/` or send the URL directly.")
            else:
                await trigger_scan_workflow(token, chat_id, parts[1])
        elif text.startswith("http://") or text.startswith("https://"):
            # Auto-trigger scan if direct URL is sent
            await trigger_scan_workflow(token, chat_id, text)
        else:
            await send_telegram_message(token, chat_id, "🤖 **Unknown command.**\nType `/help` to see list of valid options.")

    except Exception as e:
        logger.error(f"Error handling Telegram update: {e}")


async def handle_help_command(token: str, chat_id: str):
    help_text = (
        "🤖 **AWAP-AI Security Audit Bot**\n\n"
        "Commands:\n"
        "• `/scan <url>` — Index target and initiate scan immediately.\n"
        "• `/status` — View status of recent scan pipelines.\n"
        "• `/help` — Display this command menu.\n\n"
        "💡 *Tip:* You can also send the target endpoint URL directly (e.g. `http://localhost:4280/login.php`) to start a scan."
    )
    await send_telegram_message(token, chat_id, help_text)


async def handle_status_command(token: str, chat_id: str):
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Scan).order_by(desc(Scan.created_at)).limit(3))
        scans = res.scalars().all()
        
    if not scans:
        await send_telegram_message(token, chat_id, "📭 No scans found in system database.")
        return
        
    msg_parts = ["📋 **Recent Scan Runs:**\n"]
    for s in scans:
        # Fetch target domain
        async with AsyncSessionLocal() as db:
            target = await db.scalar(select(Target).filter(Target.id == s.target_id))
            target_name = target.name if target else "Unknown Target"
            
        progress_bar = "▓" * (s.progress // 10) + "░" * (10 - (s.progress // 10))
        msg_parts.append(
            f"• **Target:** {target_name}\n"
            f"  **ID:** `{str(s.id)[:8]}`\n"
            f"  **State:** `{s.state}`\n"
            f"  **Progress:** `{s.progress}%` [{progress_bar}]\n"
        )
    await send_telegram_message(token, chat_id, "\n".join(msg_parts))


async def trigger_scan_workflow(token: str, chat_id: str, url: str):
    """
    Validates URL, creates/updates target scope, auto-authorizes, and kicks off Celery task.
    """
    clean_url = url.strip()
    parsed = urllib.parse.urlparse(clean_url)
    if not parsed.scheme or not parsed.netloc:
        await send_telegram_message(token, chat_id, "❌ **Error:** Invalid URL format. Scheme and domain are required (e.g., `http://localhost:4280/`).")
        return

    await send_telegram_message(token, chat_id, f"🔍 Indexing and authorizing target: `{clean_url}`...")
    
    # 1. Target creation/upsert
    async with AsyncSessionLocal() as db:
        domain = parsed.netloc
        db_target = await db.scalar(select(Target).filter(Target.domain == domain))
        if db_target:
            db_target.base_url = clean_url
            db_target.authorized = True
            db_target.authorized_at = datetime.utcnow()
            target_id = db_target.id
        else:
            new_t = Target(
                domain=domain,
                name=domain,
                base_url=clean_url,
                authorized=True,
                authorized_at=datetime.utcnow()
            )
            db.add(new_t)
            await db.commit()
            await db.refresh(new_t)
            target_id = new_t.id
            
        # 2. Scan creation
        new_scan = Scan(
            target_id=target_id,
            state="CREATED",
            profile="standard",
            progress=0
        )
        db.add(new_scan)
        await db.commit()
        await db.refresh(new_scan)
        scan_id = new_scan.id
        
        await db.commit()

    # 3. Trigger worker task
    try:
        from awap.engines.worker import run_scope_task
        run_scope_task.delay(str(scan_id), str(target_id))
        
        status_msg = (
            f"🚀 **Scan Pipeline Kicked Off!**\n\n"
            f"**Target URL:** `{clean_url}`\n"
            f"**Scan ID:** `{scan_id}`\n"
            f"**Initial Phase:** `CREATED`\n\n"
            f"You will receive an alert summary and report download buttons once the fuzzer completes."
        )
        await send_telegram_message(token, chat_id, status_msg)
    except Exception as e:
        logger.error(f"Failed to start scan via Celery: {e}")
        await send_telegram_message(token, chat_id, f"❌ **Error:** Failed to enqueue scan task: {e}")


async def handle_callback_query(callback_query: dict, token: str):
    """
    Handles report downloads from inline button selections.
    """
    chat_id = str(callback_query["message"]["chat"]["id"])
    callback_id = callback_query["id"]
    data = callback_query["data"]
    
    # Format: download:format:template:scan_id
    # Examples:
    # download:pdf:tech:scan_id
    # download:md:tech:scan_id
    # download:csv:all:scan_id
    try:
        parts = data.split(":")
        if len(parts) < 4 or parts[0] != "download":
            return
            
        fmt = parts[1]
        tpl = parts[2]
        scan_id = parts[3]
        
        # Determine path
        out_dir = os.path.join("reports", scan_id)
        file_path = None
        caption = ""
        
        if fmt == "pdf":
            file_path = os.path.join(out_dir, f"report_{tpl}.pdf")
            caption = f"AWAP-Ai {tpl.title()} PDF Report"
        elif fmt == "md":
            file_path = os.path.join(out_dir, f"report_{tpl}.md")
            caption = f"AWAP-Ai {tpl.title()} Markdown Report"
        elif fmt == "csv":
            file_path = os.path.join(out_dir, "findings.csv")
            caption = f"AWAP-Ai Findings CSV"
            
        # Fallback to legacy PDF if not found
        if fmt == "pdf" and (not file_path or not os.path.exists(file_path)):
            legacy = f"reports/AWAP_Scan_Report_{scan_id}.pdf"
            if os.path.exists(legacy):
                file_path = legacy
                
        # Fallback to legacy CSV if not found
        if fmt == "csv" and (not file_path or not os.path.exists(file_path)):
            legacy = f"reports/AWAP_Scan_Report_{scan_id}.csv"
            if os.path.exists(legacy):
                file_path = legacy

        # Answer callback first (prevents spinner on Telegram client)
        await answer_callback_query(token, callback_id, "Preparing report file...")

        if not file_path or not os.path.exists(file_path):
            # Generate report on-demand
            try:
                from awap.core.database import AsyncSessionLocal
                from awap.models.scan import Scan
                from sqlalchemy import select
                from awap.reporting.report_generator import generate_reports
                
                async with AsyncSessionLocal() as db:
                    scan = await db.scalar(select(Scan).filter(Scan.id == scan_id))
                    if scan:
                        generate_reports(str(scan_id), str(scan.target_id), template=tpl)
            except Exception as ex:
                logger.error(f"Failed to generate report on-demand: {ex}")

        if not file_path or not os.path.exists(file_path):
            await send_telegram_message(token, chat_id, f"⚠️ **File not found:** The requested report file does not exist on disk.")
            return

        # Upload document
        await send_telegram_document(token, chat_id, file_path, caption)
        
    except Exception as e:
        logger.error(f"Error handling report download callback: {e}")
        await send_telegram_message(token, chat_id, f"❌ **Error:** Failed to process report download: {e}")


async def send_telegram_message(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(url, json=payload)


async def answer_callback_query(token: str, callback_query_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id, "text": text}
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(url, json=payload)


async def send_telegram_document(token: str, chat_id: str, file_path: str, caption: str):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    async with httpx.AsyncClient(timeout=45.0) as client:
        with open(file_path, "rb") as f:
            files = {"document": (os.path.basename(file_path), f)}
            data = {"chat_id": chat_id, "caption": caption}
            response = await client.post(url, data=data, files=files)
            if response.status_code != 200:
                logger.error(f"Document upload failed: {response.text}")
