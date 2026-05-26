from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from awap.api.routes import router as api_router
from awap.api.websockets import router as ws_router
from awap.api.oast import router as oast_router
from awap.api.webhooks import router as webhook_router
from awap.core.logging_config import setup_logging
import asyncio

# Industrial Logging Setup
setup_logging()

app = FastAPI(
    title="AWAP-AI Platform API",
    description="Autonomous Web Application Penetration Testing System",
    version="1.1.0",
)

# CORS configuration - Industrial Standard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)
app.include_router(oast_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "awap-ai-core",
        "timestamp": "2026-04-06T22:46:37+05:30"
    }

@app.on_event("startup")
async def startup_event():
    # In a production environment, migrations would be handled by Alembic. 
    # For this advanced setup, we ensure the engine is connected.
    from awap.core.database import engine
    from awap.models.base import Base
    from awap.api.websockets import redis_listener
    from sqlalchemy import text
    
    # Start Redis listener for WebSocket bridge
    app.state.redis_listener_task = asyncio.create_task(redis_listener())
    
    # Optional: Auto-create tables for development if needed, but in async.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE targets ADD COLUMN IF NOT EXISTS name VARCHAR;"))
            await conn.execute(text("ALTER TABLE targets ADD COLUMN IF NOT EXISTS base_url VARCHAR;"))
        except Exception as e:
            pass

    # Ensure default settings row exists
    from awap.core.database import AsyncSessionLocal
    from awap.models.setting import SystemSetting
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        try:
            res = await db.execute(select(SystemSetting).filter(SystemSetting.id == "default"))
            if not res.scalar():
                db.add(SystemSetting(id="default"))
                await db.commit()
        except Exception as e:
            pass

    # Start Telegram bot polling service
    try:
        from awap.core.telegram_bot import start_telegram_bot
        app.state.telegram_bot_task = asyncio.create_task(start_telegram_bot())
    except Exception as e:
        pass
