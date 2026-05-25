import asyncio
from awap.core.database import AsyncSessionLocal
from awap.models.target import Target
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Target))
        targets = res.scalars().all()
        print("Database Targets:")
        for t in targets:
            print(f"- ID: {t.id}, Domain: {t.domain}, Authorized: {t.authorized}")

if __name__ == "__main__":
    asyncio.run(run())
