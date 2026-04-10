from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from awap.core.config import settings

# Adjust URL for asyncpg if not already present
db_url = settings.DATABASE_URL

engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
