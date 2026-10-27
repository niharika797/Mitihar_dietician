from dotenv import load_dotenv

load_dotenv()  # the import chain reaches app.core.database, which requires DATABASE_URL

from app.services.ingredient_habits import aggregate_habits


def _s(intake=None, dishes=None):
    return {
        "ingredient_intake": {k: {"meals": v} for k, v in (intake or {}).items()},
        "dish_frequency": dishes or [],
    }


def test_habit_from_two_or_more_weeks():
    h = aggregate_habits([_s({"egg": 5}), _s({"egg": 4}), _s({"rice": 9})], set())
    assert "egg" in h.names and h.summary_names == h.names and h.weeks == 3


def test_one_week_gives_no_habits_but_pantry_counts():
    assert aggregate_habits([_s({"egg": 7})], set()).names == frozenset()
    h = aggregate_habits([_s({"egg": 7})], {"paneer"})
    assert h.names == frozenset({"paneer"}) and h.summary_names == frozenset()


def test_newer_week_outranks_older_with_same_count():
    h = aggregate_habits([_s({"oats": 3}), _s({"poha": 3})], set(), top_n=1)
    assert h.names == frozenset({"oats"})


def test_top_n_caps_names():
    h = aggregate_habits([_s({"a": 5, "b": 4, "c": 3}), _s({"a": 5, "b": 4, "c": 3})], set(), top_n=2)
    assert h.names == frozenset({"a", "b"})


def test_preferred_and_avoided_dishes_sum_over_all_weeks():
    w1 = _s(dishes=[{"food_item_id": 1, "times_selected": 1, "times_offered": 3},
                    {"food_item_id": 2, "times_selected": 0, "times_offered": 2}])
    w2 = _s(dishes=[{"food_item_id": 1, "times_selected": 1, "times_offered": 3},
                    {"food_item_id": 2, "times_selected": 0, "times_offered": 2}])
    h = aggregate_habits([w1, w2], set())
    assert h.preferred_food_ids == frozenset({1}) and h.avoided_food_ids == frozenset({2})


def test_usual_names_are_the_top_three():
    h = aggregate_habits([_s({"a": 9, "b": 8, "c": 7, "d": 6}), _s({"a": 9, "b": 8, "c": 7, "d": 6})], set())
    assert h.usual_names == frozenset({"a", "b", "c"}) and h.usual_names <= h.summary_names


def test_no_data_is_empty():
    h = aggregate_habits([], set())
    assert not (h.names or h.summary_names or h.preferred_food_ids or h.avoided_food_ids) and h.weeks == 0


def test_excluded_ubiquitous_names_never_become_habits():
    h = aggregate_habits([_s({"onion": 9, "eggs": 3}), _s({"onion": 9, "eggs": 3})], {"onion", "paneer"},
                         exclude=frozenset({"onion"}))
    assert h.summary_names == frozenset({"eggs"}) and h.names == frozenset({"eggs", "paneer"})
