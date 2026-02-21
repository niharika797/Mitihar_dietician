from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

class ProgressService:
    def __init__(self):
        self.collection_name = "progress"

    def get_collection(self, db: AsyncIOMotorDatabase):
        return db[self.collection_name]

    async def log_meal(self, user_id: str, meal_data: dict, db: AsyncIOMotorDatabase):
        collection = self.get_collection(db)
        log_entry = {
            "user_id": user_id,
            "type": "meal",
            "data": meal_data,
            "timestamp": datetime.utcnow()
        }
        await collection.insert_one(log_entry)
        return True

    async def log_water(self, user_id: str, glasses: int, db: AsyncIOMotorDatabase):
        collection = self.get_collection(db)
        log_entry = {
            "user_id": user_id,
            "type": "water",
            "data": {"glasses": glasses},
            "timestamp": datetime.utcnow()
        }
        await collection.insert_one(log_entry)
        return True

    async def log_steps(self, user_id: str, steps: int, db: AsyncIOMotorDatabase):
        collection = self.get_collection(db)
        log_entry = {
            "user_id": user_id,
            "type": "steps",
            "data": {"steps": steps},
            "timestamp": datetime.utcnow()
        }
        await collection.insert_one(log_entry)
        return True

    async def log_weight(self, user_id: str, weight: float, db: AsyncIOMotorDatabase):
        collection = self.get_collection(db)
        log_entry = {
            "user_id": user_id,
            "type": "weight",
            "data": {"weight": weight},
            "timestamp": datetime.utcnow()
        }
        await collection.insert_one(log_entry)
        return True

    async def get_daily_logs(self, user_id: str, date: datetime, db: AsyncIOMotorDatabase):
        collection = self.get_collection(db)
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59)
        
        cursor = collection.find({
            "user_id": user_id,
            "timestamp": {"$gte": start_of_day, "$lte": end_of_day}
        })
        return await cursor.to_list(length=100)

progress_service = ProgressService()
