from typing import List

# Keys are exact strings stored in patients.medical_conditions (from onboarding UI).
# Values are exact tag strings present in food_items.avoid_tags / prefer_tags.
# avoid_pcos and avoid_gout are included but currently have 0 food_items — no-op until Layer 2 adds them.

CONDITION_AVOID_TAGS: dict[str, list[str]] = {
    "Type 2 Diabetes":  ["avoid_diabetes"],
    "Pre-diabetes":     ["avoid_diabetes"],
    "Hypertension":     ["avoid_hypertension"],
    "High Cholesterol": ["avoid_highchol"],
    "PCOS/PCOD":        ["avoid_pcos"],
    "Hypothyroidism":   ["avoid_hypothyroid"],
    "Hyperthyroidism":  ["avoid_hyperthyroid"],
    "Heart Disease":    ["avoid_heart"],
    "Kidney Disease":   ["avoid_kidney", "avoid_hypertension"],  # sodium restriction clinically indicated for CKD regardless of stage
    "Fatty Liver":      ["avoid_fattyliver"],
    "IBS/IBD":          ["avoid_ibs"],
    "Celiac Disease":   ["avoid_gluten"],
    "Gout":             ["avoid_gout"],
    "Osteoporosis":     [],
    "Anemia":           [],
}

CONDITION_PREFER_TAGS: dict[str, list[str]] = {
    "Type 2 Diabetes":  ["diabetes_friendly"],
    "Pre-diabetes":     ["diabetes_friendly"],
    "Hypertension":     ["heart_friendly"],
    "High Cholesterol": ["cholesterol_friendly"],
    "PCOS/PCOD":        ["pcos_friendly"],
    "Hypothyroidism":   ["thyroid_support"],
    "Hyperthyroidism":  [],
    "Heart Disease":    ["heart_friendly"],
    "Kidney Disease":   [],
    "Fatty Liver":      ["liver_friendly"],
    "IBS/IBD":          ["gut_friendly"],
    "Celiac Disease":   ["gluten_free"],
    "Gout":             [],
    "Osteoporosis":     ["calcium_rich"],
    "Anemia":           ["iron_rich"],
}


# Derived from the two dicts above — single source of truth; import this in validators
VALID_TAGS: frozenset[str] = frozenset(
    tag
    for tags in list(CONDITION_AVOID_TAGS.values()) + list(CONDITION_PREFER_TAGS.values())
    for tag in tags
)


def get_avoid_tags(conditions: List[str]) -> List[str]:
    """Return deduplicated union of avoid tags for a patient's conditions."""
    seen: set[str] = set()
    result: list[str] = []
    for condition in conditions:
        for tag in CONDITION_AVOID_TAGS.get(condition, []):
            if tag not in seen:
                seen.add(tag)
                result.append(tag)
    return result


def get_prefer_tags(conditions: List[str]) -> List[str]:
    """Return deduplicated union of prefer tags for a patient's conditions."""
    seen: set[str] = set()
    result: list[str] = []
    for condition in conditions:
        for tag in CONDITION_PREFER_TAGS.get(condition, []):
            if tag not in seen:
                seen.add(tag)
                result.append(tag)
    return result
