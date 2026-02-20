from fastapi import APIRouter, Depends
from ..services.user_service import get_current_user
from ..models.user import User
from datetime import datetime, timedelta
import random

router = APIRouter()

# Simulated data store with more realistic tracking
user_progress = {}

def generate_daily_data(base_calories):
    return {
        "calories": base_calories,
        "protein": random.randint(20, 30),
        "carbs": random.randint(60, 70),
        "fat": random.randint(80, 90),
        "meals": {
            "breakfast": base_calories * 0.3,
            "lunch": base_calories * 0.4,
            "dinner": base_calories * 0.3
        },
        "water_intake": random.randint(6, 8),
        "steps": random.randint(8000, 10000)
    }

@router.get("/today")
async def get_today_stats(current_user: User = Depends(get_current_user)):
    user_id = str(current_user.id)
    if user_id not in user_progress:
        user_progress[user_id] = generate_daily_data(1284)
    
    return {
        "calories": {
            "consumed": user_progress[user_id]["calories"],
            "target": 2000,
            "remaining": 2000 - user_progress[user_id]["calories"]
        },
        "macros": {
            "protein_percentage": user_progress[user_id]["protein"],
            "carbs_percentage": user_progress[user_id]["carbs"],
            "fat_percentage": user_progress[user_id]["fat"]
        },
        "meals": user_progress[user_id]["meals"],
        "water_intake": {
            "glasses": user_progress[user_id]["water_intake"],
            "target": 8
        },
        "activity": {
            "steps": user_progress[user_id]["steps"],
            "target_steps": 10000
        }
    }

@router.get("/weekly")
async def get_weekly_stats(current_user: User = Depends(get_current_user)):
    user_id = str(current_user.id)
    today = datetime.now()
    
    # Generate past week's data
    weekly_data = []
    for i in range(7):
        day = today - timedelta(days=i)
        daily_calories = random.randint(1200, 1800)
        weekly_data.append({
            "date": day.strftime("%Y-%m-%d"),
            "stats": generate_daily_data(daily_calories)
        })
    
    return {
        "current_week": {
            "daily_data": weekly_data,
            "summary": {
                "avg_calories": sum(day["stats"]["calories"] for day in weekly_data) / 7,
                "avg_protein": sum(day["stats"]["protein"] for day in weekly_data) / 7,
                "avg_carbs": sum(day["stats"]["carbs"] for day in weekly_data) / 7,
                "avg_fat": sum(day["stats"]["fat"] for day in weekly_data) / 7,
                "total_steps": sum(day["stats"]["steps"] for day in weekly_data),
                "water_intake_completion": sum(day["stats"]["water_intake"] for day in weekly_data) / (8 * 7) * 100
            }
        },
        "trends": {
            "calories_trend": "maintaining",
            "weight_trend": "stable",
            "activity_trend": "improving"
        }
    }

@router.get("/weight")
async def get_weight(current_user: User = Depends(get_current_user)):
    # Generate some historical weight data
    today = datetime.now()
    history = []
    current_weight = current_user.weight
    
    for i in range(30):
        day = today - timedelta(days=i)
        # Small random fluctuations in weight
        weight = current_weight + random.uniform(-0.5, 0.5)
        history.append({
            "date": day.strftime("%Y-%m-%d"),
            "weight": round(weight, 1)
        })
    
    return {
        "current_weight": current_user.weight,
        "history": history,
        "trend": {
            "monthly_change": round(history[0]["weight"] - history[-1]["weight"], 1),
            "direction": "maintaining"
        }
    }