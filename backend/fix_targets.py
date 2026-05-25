import asyncio
from awap.core.database import AsyncSessionLocal
from sqlalchemy import update
from awap.models.target import Target

async def run():
    async with AsyncSessionLocal() as db:
        await db.execute(update(Target).values(authorized=True))
        await db.commit()
        print('Authorized all existing targets!')

if __name__ == "__main__":
    asyncio.run(run())
