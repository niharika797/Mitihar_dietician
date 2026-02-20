from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..core.config import settings
from typing import AsyncGenerator

class Database:
    client: AsyncIOMotorClient = None

async def get_database() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
        """
        Get database instance.
        Returns AsyncGenerator to properly handle async context.
        """
        try:
            yield Database.client[settings.DATABASE_NAME]
        finally:
            pass

async def connect_to_mongodb():
    Database.client = AsyncIOMotorClient(settings.MONGO_URI)

async def close_mongodb_connection():
    Database.client.close()