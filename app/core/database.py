import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client: AsyncIOMotorClient = None

async def connect_to_mongodb():
    global client
    client = AsyncIOMotorClient(settings.MONGO_URI)
    print("Connected to MongoDB")

async def close_mongodb_connection():
    global client
    if client:
        client.close()
        print("Closed MongoDB connection")

def get_database():
    return client[settings.DATABASE_NAME]

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()