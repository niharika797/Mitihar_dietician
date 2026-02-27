import json
import sys

with open("meal_recommendation_output.json", "r") as f:
    plan = json.load(f)

md_content = "# Meal Recommendation Report\n\n"
md_content += f"**User ID:** {plan.get('user_id', 'Unknown')}\n\n"

current_date = None
for meal in plan.get("meals", []):
    if meal.get("Date") != current_date:
        current_date = meal.get("Date")
        md_content += f"## Day: {current_date}\n\n"
    
    md_content += f"### {meal.get('Meal Type', 'Unknown Meal')}\n"
    md_content += f"- **Recipe Options:** {meal.get('Options', 'N/A')}\n"
    md_content += f"- **Calories:** {meal.get('Total Calories', 0)} kcal\n"
    md_content += f"- **Macros:** Pro: {meal.get('Total Protein', 0)}g | Carbs: {meal.get('Total Carbs', 0)}g | Fat: {meal.get('Total Fat', 0)}g\n"
    
    ingredients = meal.get("Ingredients Scaling", {})
    if ingredients:
        md_content += "- **Ingredients Scaling:**\n"
        for ing_name, amount in ingredients.items():
            md_content += f"  - {ing_name}: {amount:.1f}g\n"
    md_content += "\n"

# Add ingredient checklist summary
checklist = plan.get("ingredient_checklist", [])
if checklist:
    md_content += "## Weekly Ingredient Checklist\n\n"
    for item in checklist:
        md_content += f"- {item.get('Ingredient', 'Unknown')}: {float(item.get('Total_Amount_g', 0)):.1f}g\n"

with open(r"c:\Users\Lenovo\.gemini\antigravity\brain\90d0d4bc-fee4-4fe7-8be9-9ca7a3881929\meal_recommendation_report.md", "w") as f:
    f.write(md_content)

print("Report generated.")
