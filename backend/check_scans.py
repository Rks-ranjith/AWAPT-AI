import asyncio
from awap.core.database import AsyncSessionLocal
from awap.models.scan import Scan
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Scan))
        scans = res.scalars().all()
        print("Database Scans:")
        for s in scans:
            print(f"- Scan ID: {s.id}, Target ID: {s.target_id}, State: {s.state}, Progress: {s.progress}")

if __name__ == "__main__":
    asyncio.run(run())
