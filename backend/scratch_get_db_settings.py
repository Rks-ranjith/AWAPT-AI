import asyncio
from sqlalchemy import select
from awap.core.database import AsyncSessionLocal
from awap.models.setting import SystemSetting

async def view_settings():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SystemSetting))
        settings = result.scalars().all()
        print("Total settings rows:", len(settings))
        for s in settings:
            print(f"ID: {s.id}")
            print(f"  Email Enabled: {s.email_enabled}")
            print(f"  Email Alert (Recipient): {s.email_alert}")
            print(f"  Slack Enabled: {s.slack_enabled}")
            print(f"  Slack Webhook: {s.slack_webhook}")
            print(f"  Telegram Enabled: {s.telegram_enabled}")
            print(f"  Telegram Token: {s.telegram_token}")
            print(f"  Telegram Chat ID: {s.telegram_chat_id}")

if __name__ == "__main__":
    asyncio.run(view_settings())
