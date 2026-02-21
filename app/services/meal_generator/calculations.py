from typing import Optional

def calculate_bmi(height: float, weight: float) -> float:
    height_m = height / 100
    return weight / (height_m ** 2)

def calculate_bmr(gender: str, weight: float, height: float, age: int) -> float:
    if gender == 'male' or gender =='Male':
        return 66.5 + (13.75 * weight) + (5.003 * height) - (6.75 * age)
    elif gender =='female' or gender =='Female':
        return 655.1 + (9.563 * weight) + (1.850 * height) - (4.676 * age)
    return 0.0

def calculate_tdee(bmr: float, activity_level: str) -> float:
    multipliers = {
        'S': 1.2, 'LA': 1.375,
        'MA': 1.55, 'VA': 1.725, 'SA': 1.9
    }
    return bmr * multipliers.get(activity_level, 1.2)

def calculate_macronutrients(tdee: float, health_condition: Optional[str] = None, diabetes_status: Optional[str] = None):
    # Initialize with default values to avoid UnboundLocalError
    protein = (tdee * 0.2) / 4
    carbs = (tdee * 0.55) / 4
    fat = (tdee * 0.25) / 9
    
    if health_condition == 'Healthy':
        pass # Using defaults
    elif health_condition == 'Gym-Friendly': 
        if diabetes_status == 'weight_loss':
            protein = (tdee * 0.45) / 4
            carbs = (tdee * 0.35) / 4
            fat = (tdee * 0.2) / 9
        elif diabetes_status == 'muscle_gain':
            protein = (tdee * 0.4) / 4
            carbs = (tdee * 0.4) / 4
            fat = (tdee * 0.2) / 9
        elif diabetes_status == 'maintenance':
            protein = (tdee * 0.35) / 4
            carbs = (tdee * 0.4) / 4
            fat = (tdee * 0.25) / 9
    elif health_condition == 'Diabetic-Friendly':
        if diabetes_status == 'controlled':
            protein = (tdee * 0.25) / 4
            carbs = (tdee * 0.45) / 4
            fat = (tdee * 0.25) / 9
        elif diabetes_status == 'uncontrolled':
            protein = (tdee * 0.3) / 4
            carbs = (tdee * 0.4) / 4
            fat = (tdee * 0.25) / 9
    
    fiber = (tdee * 14) / 1000
    
    return protein, carbs, fiber, fat