import asyncio
from datetime import date
from app.core.database import AsyncSessionLocal
from app.services.weekly_summary_service import compute_weekly_summary

async def test():
    async with AsyncSessionLocal() as db:
        result = await compute_weekly_summary(db, patient_id=2, week_start=date(2026, 6, 18))
        print("week_start:", result.get("week_start"))
        print("week_end:", result.get("week_end"))
        print("confirmed_slots:", result["confirmed_slots"])
        print("dish_frequency count:", len(result["dish_frequency"]))
        preferred = result["pattern"]["preferred_dishes"]
        never = result["pattern"]["never_selected_dishes"]
        print("preferred_dishes:", preferred)
        print("never_selected_dishes count:", len(never))
        if never:
            print("never_selected sample:", never[:3])
        print()
        for d in result["dish_frequency"]:
            if d["times_selected"] >= 2:
                print("  PREFERRED:", d["recipe_name"],
                      "selected=", d["times_selected"],
                      "offered=", d["times_offered"])
            if d["times_offered"] >= 3 and d["times_selected"] == 0:
                print("  AVOIDED:", d["recipe_name"],
                      "offered=", d["times_offered"],
                      "selected=", d["times_selected"])

asyncio.run(test())
