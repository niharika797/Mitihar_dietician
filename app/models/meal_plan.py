from pydantic import BaseModel

class MealPlanInput(BaseModel):
    daily_target: int
    actual_intake: int
    activity: int

class MealPlanResponse(BaseModel):
    calories: dict[str, float]