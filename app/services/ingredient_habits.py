"""
app/services/ingredient_habits.py

Ingredient-habit learning (design: docs/superpowers/specs/2026-10-28-ingredient-habit-learning-design.md).

  - build_ingredient_intake(): per-ingredient meals/grams/nutrients for a week's confirmed choices;
    stored in weekly_patient_summary.summary_data by weekly_summary_service.
  - load_habits(): reads the last WEEKS summaries + in-stock pantry and returns the Habits the
    meal generator and /meal-plan/week use. Habits only ever re-order candidates; they never filter.
"""
import math
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import (
    FoodItem, Ingredient, PatientMealChoiceDish, PatientPantry,
    RecipeIngredient, WeeklyPatientSummary,
)
from app.services.meal_generator.meal_generator import is_staple

WEEKS = 6          # summary memory window
DECAY = 0.8        # weight of a week n weeks back = DECAY ** n
TOP_N = 8          # habit ingredients taken from summaries
MIN_WEEKS = 2      # summaries needed before summary-derived habits are used
PANTRY_CAP = 30    # bound on pantry ingredients fed to the generator
USUAL_N = 3         # ingredients that earn the 'Your usual' badge (few, or the badge means nothing)
UBIQUITOUS = 0.15  # an ingredient in more than this share of verified dishes (onion, tomato...) says nothing about taste


def norm_name(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


@dataclass(frozen=True)
class Habits:
    names: frozenset            # summary habits + in-stock pantry (generator boost)
    summary_names: frozenset    # summary habits only
    usual_names: frozenset      # top USUAL_N summary habits (drives is_usual)
    preferred_food_ids: frozenset
    avoided_food_ids: frozenset
    weeks: int                  # summaries available


def aggregate_habits(summaries: list, pantry_names: set, *, top_n: int = TOP_N, decay: float = DECAY,
                     exclude: frozenset = frozenset(), idf: dict | None = None) -> Habits:
    """summaries: summary_data dicts, newest first. `exclude`: ingredient names to ignore (too common to mean
    anything). `idf`: name -> weight, so a rare ingredient eaten daily outranks a common one eaten daily."""
    idf = idf or {}
    score: dict = defaultdict(float)
    sel: dict = defaultdict(int)
    off: dict = defaultdict(int)
    for i, s in enumerate(summaries):
        for name, v in (s.get("ingredient_intake") or {}).items():
            score[name] += float(v.get("meals", 0)) * decay ** i * idf.get(name, 1.0)
        for d in s.get("dish_frequency") or []:
            sel[d["food_item_id"]] += d.get("times_selected", 0)
            off[d["food_item_id"]] += d.get("times_offered", 0)
    ranked = [n for n, sc in sorted(score.items(), key=lambda kv: -kv[1]) if sc > 0 and n not in exclude]
    summary_names = frozenset(ranked[:top_n]) if len(summaries) >= MIN_WEEKS else frozenset()
    return Habits(
        names=summary_names | frozenset(sorted(pantry_names - exclude)[:PANTRY_CAP]),
        summary_names=summary_names,
        usual_names=frozenset(ranked[:USUAL_N]) if summary_names else frozenset(),
        preferred_food_ids=frozenset(f for f, n in sel.items() if n >= 2),
        avoided_food_ids=frozenset(f for f, n in off.items() if n >= 3 and sel[f] == 0),
        weeks=len(summaries),
    )


async def load_habits(session: AsyncSession, patient_id: int) -> Habits:
    rows = await session.execute(
        select(WeeklyPatientSummary.summary_data)
        .where(WeeklyPatientSummary.patient_id == patient_id)
        .order_by(WeeklyPatientSummary.week_start_date.desc())
        .limit(WEEKS)
    )
    summaries = [r[0] for r in rows if r[0]]
    pantry = await session.execute(
        select(Ingredient.name)
        .join(PatientPantry, PatientPantry.ingredient_id == Ingredient.id)
        .where(
            PatientPantry.patient_id == patient_id,
            or_(PatientPantry.quantity_g.is_(None), PatientPantry.quantity_g > 0),   # same rule as routers/meal_plan._PANTRY_IN_STOCK
        )
    )
    pantry_names = {norm_name(r[0]) for r in pantry if not is_staple(r[0])}
    candidates = pantry_names | {n for s in summaries for n in (s.get("ingredient_intake") or {})}
    common, idf = await _dish_rarity(session, candidates)
    return aggregate_habits(summaries, pantry_names, exclude=common, idf=idf)


async def _dish_rarity(session: AsyncSession, names: set) -> tuple:
    """(names in more than UBIQUITOUS of the verified dishes, name -> ln(dishes / dishes containing it))."""
    if not names:
        return frozenset(), {}
    verified = FoodItem.is_verified == True, FoodItem.deleted_at.is_(None)  # noqa: E712
    total = (await session.execute(select(func.count(FoodItem.id)).where(*verified))).scalar() or 1
    key = func.lower(func.trim(Ingredient.name))
    rows = await session.execute(
        select(key, func.count(func.distinct(RecipeIngredient.food_item_id)))
        .join(RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .join(FoodItem, FoodItem.id == RecipeIngredient.food_item_id)
        .where(key.in_(names), *verified)
        .group_by(key)
    )
    counts = {n: c for n, c in rows}
    return (frozenset(n for n, c in counts.items() if c / total > UBIQUITOUS),
            {n: math.log(total / c) for n, c in counts.items()})


_NUTRIENTS = (  # summary key, Ingredient column
    ("protein_g", "protein_per_100g"),
    ("fibre_g", "fiber_per_100g"),
    ("iron_mg", "iron_per_100g"),
    ("calcium_mg", "calcium_per_100g"),
    ("calories", "calories_per_100g"),
)


async def build_ingredient_intake(db: AsyncSession, choices: list) -> dict:
    """Per-ingredient intake for the week's confirmed choices. Staples skipped."""
    if not choices:
        return {"ingredient_intake": {}, "nutrient_totals": {}, "nutrient_data_missing": 0}
    from app.routers.meal_plan import BOWL_FACTORS   # lazy: the router imports services at load time

    bowl = {c.id: BOWL_FACTORS.get(c.bowl_size or "medium", 1.0) for c in choices}
    rows = await db.execute(
        select(
            PatientMealChoiceDish.choice_id, RecipeIngredient.ingredient_id, Ingredient.name,
            RecipeIngredient.quantity_g,
            *[getattr(Ingredient, col) for _, col in _NUTRIENTS],
        )
        .join(RecipeIngredient, RecipeIngredient.food_item_id == PatientMealChoiceDish.food_item_id)
        .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .where(PatientMealChoiceDish.choice_id.in_(list(bowl)))
    )
    intake: dict = {}
    meal_sets: dict = defaultdict(set)
    missing: set = set()
    for choice_id, ing_id, name, qty, *per100 in rows:
        if is_staple(name):
            continue
        key = norm_name(name)
        grams = float(qty or 0) * bowl[choice_id]
        e = intake.setdefault(key, {"ingredient_id": ing_id, "meals": 0, "grams": 0.0,
                                    **{k: 0.0 for k, _ in _NUTRIENTS}})
        e["grams"] += grams
        meal_sets[key].add(choice_id)
        if per100[0] is None:
            missing.add(key)
        for (k, _), v in zip(_NUTRIENTS, per100, strict=True):
            if v is not None:
                e[k] += grams / 100.0 * float(v)
    for key, e in intake.items():
        e["meals"] = len(meal_sets[key])
        for k in e:
            if isinstance(e[k], float):
                e[k] = round(e[k], 2)
    totals = {}
    for k, _ in _NUTRIENTS:
        top = sorted(((n, e[k]) for n, e in intake.items() if e[k] > 0), key=lambda t: -t[1])[:3]
        totals[k] = {"total": round(sum(e[k] for e in intake.values()), 2),
                     "top": [{"name": n, "amount": a} for n, a in top]}
    return {"ingredient_intake": intake, "nutrient_totals": totals, "nutrient_data_missing": len(missing)}
