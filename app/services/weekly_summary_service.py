"""
app/services/weekly_summary_service.py

Computes and caches the weekly adherence + dish-frequency summary for one patient-week.
Called by:
  - GET /doctor/patients/{id}/weekly-summary (on-demand, R-7A)
  - complete_expired_plans() cron (end-of-week, R-7A)
  - auto_generate_weekly_plans() cron (reads prior summary, R-7C)
"""
import logging
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.models.db_models import (
    WeeklyPatientSummary, PatientMealChoice, PatientMealChoiceDish,
    WeeklyCombo, Recommendation, FoodItem,
)

_log = logging.getLogger(__name__)


async def compute_weekly_summary(
    db: AsyncSession,
    patient_id: int,
    week_start: "date | None" = None,
) -> dict:
    """
    Compute dish-frequency + adherence summary for a patient's given week.
    Writes result to weekly_patient_summary (upsert). Returns summary_data dict.

    week_start is floored to Monday. Safe to call mid-week or post-week.
    Never raises — writes "error" key into summary_data on failure.
    """
    try:
        return await _compute(db, patient_id, week_start)
    except Exception as exc:
        _log.error(
            "compute_weekly_summary: unhandled error patient_id=%s week_start=%s: %s",
            patient_id, week_start, exc, exc_info=True,
        )
        return {"error": str(exc), "week_start": week_start.isoformat() if week_start else "unknown"}


async def _compute(db: AsyncSession, patient_id: int, week_start: "date | None") -> dict:
    # 1. Find rec
    if week_start is not None:
        # Explicit week_start: pin to that week's rec regardless of is_active
        rec_result = await db.execute(
            select(Recommendation)
            .where(
                Recommendation.patient_id == patient_id,
                Recommendation.generation_version == 2,
                Recommendation.week_start_date == week_start,
            )
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        rec = rec_result.scalar_one_or_none()
        week_end = week_start + timedelta(days=6)
        recommendation_id = rec.id if rec else None
    else:
        # No explicit week_start — active rec first, fuzzy historical fallback
        rec_result = await db.execute(
            select(Recommendation)
            .where(
                Recommendation.patient_id == patient_id,
                Recommendation.generation_version == 2,
                Recommendation.is_active == True,
            )
            .limit(1)
        )
        rec = rec_result.scalar_one_or_none()

        if rec:
            week_start = rec.week_start_date
            week_end   = week_start + timedelta(days=6)
            recommendation_id = rec.id
        else:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_end   = week_start + timedelta(days=6)
            recommendation_id = None
            # Try historical rec within ±6 days of today's Monday
            hist_result = await db.execute(
                select(Recommendation)
                .where(
                    Recommendation.patient_id == patient_id,
                    Recommendation.generation_version == 2,
                    Recommendation.week_start_date.between(
                        week_start - timedelta(days=6), week_start + timedelta(days=6)
                    ),
                )
                .order_by(Recommendation.id.desc())
                .limit(1)
            )
            hist_rec = hist_result.scalar_one_or_none()
            if hist_rec:
                recommendation_id = hist_rec.id

    # 2. Fetch all patient_meal_choices for this patient-week
    choices_result = await db.execute(
        select(PatientMealChoice)
        .where(
            PatientMealChoice.patient_id == patient_id,
            PatientMealChoice.date >= week_start,
            PatientMealChoice.date <= week_end,
        )
    )
    choices = choices_result.scalars().all()

    # 3. Build per-day map (keyed by ISO date string)
    per_day_map: dict = {}
    for c in choices:
        day_str = c.date.isoformat()
        if day_str not in per_day_map:
            per_day_map[day_str] = {
                "date": day_str,
                "breakfast_confirmed": False,
                "lunch_confirmed": False,
                "dinner_confirmed": False,
                "confirmed_calories": 0.0,
                "planned_calories": 0.0,
                "bowl_size_breakdown": {"small": 0, "medium": 0, "large": 0, "none": 0},
            }
        slot_key = f"{c.meal_type.lower()}_confirmed"
        if slot_key in per_day_map[day_str]:
            per_day_map[day_str][slot_key] = True
        per_day_map[day_str]["confirmed_calories"] += float(
            c.actual_calories if c.actual_calories is not None else (c.calories or 0)
        )
        bowl = getattr(c, "bowl_size", None)
        key = bowl if bowl in ("small", "medium", "large") else "none"
        per_day_map[day_str]["bowl_size_breakdown"][key] += 1

    # 4. Fill planned_calories from weekly_combos (combo_index=0 as plan baseline)
    if rec:
        combos_result = await db.execute(
            select(WeeklyCombo.slot_date, WeeklyCombo.meal_type,
                   func.avg(WeeklyCombo.total_calories).label("avg_planned"))
            .where(
                WeeklyCombo.recommendation_id == rec.id,
                WeeklyCombo.combo_index == 0,
            )
            .group_by(WeeklyCombo.slot_date, WeeklyCombo.meal_type)
        )
        for row in combos_result.all():
            day_str = row.slot_date.isoformat()
            if day_str not in per_day_map:
                per_day_map[day_str] = {
                    "date": day_str,
                    "breakfast_confirmed": False,
                    "lunch_confirmed": False,
                    "dinner_confirmed": False,
                    "confirmed_calories": 0.0,
                    "planned_calories": 0.0,
                    "bowl_size_breakdown": {"small": 0, "medium": 0, "large": 0, "none": 0},
                }
            per_day_map[day_str]["planned_calories"] += float(row.avg_planned or 0)

    # Enrich per_day with derived fields
    per_day = []
    for d in sorted(per_day_map.values(), key=lambda x: x["date"]):
        d["meals_confirmed"] = sum(1 for k in ("breakfast_confirmed", "lunch_confirmed", "dinner_confirmed") if d[k])
        d["meals_total"] = 3
        per_day.append(d)

    # 5. Aggregate totals
    total_slots     = 21
    confirmed_slots = sum(d["meals_confirmed"] for d in per_day)
    days_all_confirmed = sum(1 for d in per_day if d["meals_confirmed"] == 3)
    adherence_pct = round((confirmed_slots / total_slots) * 100, 1) if total_slots else 0.0

    # Bowl average for week_totals
    bowl_counter: dict = {"small": 0, "medium": 0, "large": 0}
    for d in per_day:
        for size in ("small", "medium", "large"):
            bowl_counter[size] += d["bowl_size_breakdown"].get(size, 0)
    if max(bowl_counter.values(), default=0) > 0:
        top = max(bowl_counter.values())
        tied = [k for k, v in bowl_counter.items() if v == top]
        avg_bowl_size = tied[0] if len(tied) == 1 else "mixed"
    else:
        avg_bowl_size = "none"

    # 6. Dish frequency
    dish_freq: dict[int, dict] = {}

    # 6a. times_selected from patient_meal_choice_dishes
    if choices:
        choice_ids = [c.id for c in choices]
        dishes_result = await db.execute(
            select(
                PatientMealChoiceDish.food_item_id,
                FoodItem.recipe_name,
                func.count(PatientMealChoiceDish.food_item_id).label("times_selected"),
            )
            .join(FoodItem, FoodItem.id == PatientMealChoiceDish.food_item_id)
            .where(PatientMealChoiceDish.choice_id.in_(choice_ids))
            .group_by(PatientMealChoiceDish.food_item_id, FoodItem.recipe_name)
        )
        for row in dishes_result.all():
            dish_freq[row.food_item_id] = {
                "food_item_id": row.food_item_id,
                "recipe_name": row.recipe_name,
                "times_selected": row.times_selected,
                "times_offered": 0,
                "bowl_sizes": [],
            }

    # 6b. times_offered from weekly_combos JSONB
    if recommendation_id:
        try:
            offered_result = await db.execute(
                text("""
                    SELECT
                        (dish->>'food_id')::int AS food_item_id,
                        COUNT(*) AS times_offered
                    FROM weekly_combos wc,
                         jsonb_array_elements(wc.dishes) AS dish
                    WHERE wc.recommendation_id = :rec_id
                    GROUP BY (dish->>'food_id')::int
                """),
                {"rec_id": recommendation_id},
            )
            for row in offered_result.all():
                fid = row.food_item_id
                if fid is None:
                    continue
                if fid not in dish_freq:
                    fi_result = await db.execute(
                        select(FoodItem.recipe_name).where(FoodItem.id == fid)
                    )
                    name = fi_result.scalar_one_or_none() or f"dish_{fid}"
                    dish_freq[fid] = {
                        "food_item_id": fid,
                        "recipe_name": name,
                        "times_selected": 0,
                        "times_offered": int(row.times_offered),
                        "bowl_sizes": [],
                    }
                else:
                    dish_freq[fid]["times_offered"] = int(row.times_offered)
        except Exception as exc:
            _log.warning("compute_weekly_summary: times_offered query failed: %s", exc)

    # 6c. bowl_sizes per dish from confirmed combos
    for c in choices:
        combo_id = getattr(c, "weekly_combo_id", None)
        if not combo_id:
            continue
        try:
            combo_result = await db.execute(
                select(WeeklyCombo.dishes).where(WeeklyCombo.id == combo_id)
            )
            combo_dishes = combo_result.scalar_one_or_none() or []
            bowl = getattr(c, "bowl_size", None)
            if bowl:
                for dish in combo_dishes:
                    fid = dish.get("food_id")
                    if fid and fid in dish_freq:
                        dish_freq[fid]["bowl_sizes"].append(bowl)
        except Exception as exc:
            _log.warning("compute_weekly_summary: bowl_sizes query failed combo_id=%s: %s", combo_id, exc)

    dish_frequency = sorted(
        dish_freq.values(),
        key=lambda x: (-x["times_selected"], -x["times_offered"]),
    )

    # 7. Pattern summary
    selected_dishes = [d for d in dish_frequency if d["times_selected"] > 0]
    never_selected  = [d for d in dish_frequency if d["times_selected"] == 0 and d["times_offered"] >= 3]
    preferred       = [d for d in dish_frequency if d["times_selected"] >= 2]
    most_selected   = selected_dishes[0]  if selected_dishes else None
    least_selected  = selected_dishes[-1] if len(selected_dishes) > 1 else None

    # 8. Assemble summary_data
    summary_data = {
        "week_start":               week_start.isoformat(),
        "week_end":                 week_end.isoformat(),
        "total_slots":              total_slots,
        "confirmed_slots":          confirmed_slots,
        "days_with_all_confirmed":  days_all_confirmed,
        "adherence_pct":            adherence_pct,
        "per_day":                  per_day,
        "dish_frequency":           dish_frequency,
        "pattern": {
            "preferred_dishes":      [{"food_item_id": d["food_item_id"], "recipe_name": d["recipe_name"]} for d in preferred],
            "never_selected_dishes": [{"food_item_id": d["food_item_id"], "recipe_name": d["recipe_name"]} for d in never_selected],
            "most_selected_dish":    most_selected,
            "least_selected_dish":   least_selected,
        },
        # week_totals kept for backward compat with WeeklySummaryTab footer
        "week_totals": {
            "planned_calories":   round(sum(d["planned_calories"]   for d in per_day), 2),
            "confirmed_calories": round(sum(d["confirmed_calories"] for d in per_day), 2),
            "avg_bowl_size":      avg_bowl_size,
        },
    }

    # 9. Upsert into weekly_patient_summary
    if recommendation_id:
        existing = await db.execute(
            select(WeeklyPatientSummary).where(
                WeeklyPatientSummary.patient_id == patient_id,
                WeeklyPatientSummary.week_start_date == week_start,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.summary_data = summary_data
            # generated_at updates via server_default on next read; force it via func.now()
            from sqlalchemy import update as sa_update
            await db.execute(
                sa_update(WeeklyPatientSummary)
                .where(WeeklyPatientSummary.id == row.id)
                .values(summary_data=summary_data, generated_at=func.now())
            )
        else:
            db.add(WeeklyPatientSummary(
                patient_id        = patient_id,
                recommendation_id = recommendation_id,
                week_start_date   = week_start,
                summary_data      = summary_data,
            ))
        await db.commit()

    return summary_data
