import asyncio
from awap.core.database import AsyncSessionLocal
from sqlalchemy import select
from awap.models.endpoint import Endpoint
from awap.models.scan import Scan

async def run():
    async with AsyncSessionLocal() as db:
        scan = (await db.execute(select(Scan).order_by(Scan.started_at.desc()))).scalars().first()
        eps = (await db.execute(select(Endpoint).filter(Endpoint.scan_id == scan.id))).scalars().all()
        print('Endpoints:', len(eps), [e.url for e in eps])

asyncio.run(run())
