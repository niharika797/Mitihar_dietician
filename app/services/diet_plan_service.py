from typing import Dict, List, Optional
from datetime import datetime
from ..models.diet_plan import DietPlan, Meal
from ..core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from enum import Enum
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .meal_generator.meal_generator import MealGenerator

class ActivityLevel(str, Enum):
    SEDENTARY = "S"
    LIGHTLY_ACTIVE = "LA"
    MODERATELY_ACTIVE = "MA"
    VERY_ACTIVE = "VA"
    SUPER_ACTIVE = "SA"

class DietType(str, Enum):
    VEGETARIAN = "Vegetarian"
    NON_VEGETARIAN = "Non Vegetarian"

class HealthCondition(str, Enum):
    HEALTHY = "Healthy"
    DIABETIC = "Diabetic-Friendly"
    GYM="Gym-Friendly"

class region(str, Enum):
    East = "East"
    South = "South"
    West = "West"
    North = "North"
    none = "none"
# Service class for diet plan generation and storage
class DietPlanService:
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.client[settings.DATABASE_NAME]
        self.diet_plans = self.db.diet_plans
        self.meals = self.db.meals


    async def generate_diet_plan(self, user_data: Dict) -> DietPlan:
        """Generate personalized diet plan using nutritional science principles."""
        # Validate inputs
        generator = MealGenerator(user_data)
        meal_plan = generator.generate_meal_plan()
        return DietPlan(
            user_id=user_data["id"],
            created_at=datetime.now(),
            meals=meal_plan
        )



    # Keep existing CRUD methods (store_diet_plan, get_diet_plan, etc.)
    async def store_diet_plan(self, diet_plan: DietPlan) -> str:
        """Store diet plan in database."""
        result = await self.diet_plans.insert_one(diet_plan.dict())
        return str(result.inserted_id)

    async def get_diet_plan(self, user_id: str) -> DietPlan:
        """Retrieve diet plan for a user."""
        plan = await self.diet_plans.find_one({"user_id": user_id})
        return DietPlan(**plan) if plan else None

    async def update_diet_plan(self, user_id: str, updated_plan: DietPlan) -> bool:
        """Update existing diet plan."""
        result = await self.diet_plans.update_one(
            {"user_id": user_id},
            {"$set": updated_plan.model_dump(exclude={"id"})}
        )
        return result.modified_count > 0
    
    async def delete_diet_plan(self, user_id: str) -> bool:
        """Delete a diet plan for a user."""
        result = await self.diet_plans.delete_one({"user_id": user_id})
        return result.deleted_count > 0