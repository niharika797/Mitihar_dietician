from app.services.meal_generator.calculations import calculate_bmi, calculate_bmr, calculate_tdee, calculate_macronutrients

def test_calculate_bmi():
    # height 175cm, weight 70kg
    bmi = calculate_bmi(175, 70)
    assert round(bmi, 2) == 22.86

def test_calculate_bmr_male():
    # gender male, weight 70kg, height 175cm, age 25
    bmr = calculate_bmr('male', 70, 175, 25)
    assert round(bmr, 2) == 1735.78 # 66.5 + 962.5 + 875.525 - 168.75

def test_calculate_tdee():
    # bmr 1735.78, MA (1.55)
    tdee = calculate_tdee(1735.78, 'MA')
    assert round(tdee, 2) == 2690.46

def test_calculate_macronutrients_healthy():
    tdee = 2000
    protein, carbs, fiber, fat = calculate_macronutrients(tdee, 'Healthy')
    assert protein == (2000 * 0.2) / 4
    assert carbs == (2000 * 0.55) / 4
    assert fat == (2000 * 0.25) / 9
    assert fiber == (2000 * 14) / 1000
