from datetime import date, datetime, timedelta
from typing import List
from ..core.database import get_database
from ..models.progress import Progress, WeightLog

async def get_today_progress(user_id: str, today: date) -> Progress:
    db = get_database()
    progress_collection = db["progress"]
    progress = await progress_collection.find_one({
        "user_id": user_id,
        "date": {
            "$gte": datetime.combine(today, datetime.min.time()),
            "$lt": datetime.combine(today + timedelta(days=1), datetime.min.time())
        }
    })
    return Progress(**progress) if progress else None

async def get_weekly_progress(user_id: str, start_date: date, end_date: date) -> List[Progress]:
    db = get_database()
    progress_collection = db["progress"]
    progress = await progress_collection.find({
        "user_id": user_id,
        "date": {
            "$gte": datetime.combine(start_date, datetime.min.time()),
            "$lt": datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        }
    }).to_list(length=None)
    return [Progress(**p) for p in progress]

async def add_weight_log(weight_log: WeightLog):
    db = get_database()
    weight_collection = db["weight_logs"]
    await weight_collection.insert_one(weight_log.model_dump())

async def get_weight_history(user_id: str) -> List[WeightLog]:
    db = get_database()
    weight_collection = db["weight_logs"]
    logs = await weight_collection.find(
        {"user_id": user_id},
        sort=[("date", -1)]
    ).to_list(length=None)
    return [WeightLog(**log) for log in logs]