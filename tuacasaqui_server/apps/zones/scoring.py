"""
Converts raw zone data + user preferences into normalised percentage scores
and a weighted fit score (0-100).

Priority weights map:
    "Not"       → 0
    "Somewhat"  → 1
    "Important" → 2
    "Essential" → 3
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List

# ==== Constants ===============================================================

PRIORITY_WEIGHTS = {
    "not":       0,
    "somewhat":  1,
    "important": 2,
    "essential": 3,
}

COMMUTE_PREFERENCE_BOOST = {
    "metro": "metro",
    "bus":   "bus",
    "car":   "car",
    "walk":  "walk",
}

# Score thresholds for match label
LABEL_THRESHOLDS = [
    (88, "Best Match"),
    (75, "Great Match"),
    (60, "Good Match"),
    (0,  "Fair Match"),
]


# ==== Data classes ========================================================

@dataclass
class UserPreferences:
    budget:          float        # EUR/month (max rent)
    safety_priority: str          # Not / Somewhat / Important / Essential
    schools_priority: str
    transport_priority: str
    commute_preference: str       # metro / bus / car / walk


@dataclass
class ZoneScores:
    safety_pct:  float
    schools_pct: float
    transit_pct: float
    budget_pct:  float
    fit_score:   float
    match_label: str


# ==== Helpers ========================================================

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _priority_weight(priority: str) -> int:
    return PRIORITY_WEIGHTS.get(priority.lower().strip(), 1)


def _match_label(score: float) -> str:
    for threshold, label in LABEL_THRESHOLDS:
        if score >= threshold:
            return label
    return "Fair Match"


# ==== Individual dimension scorers ====================================

def _score_safety(zone) -> float:
    """
    Lower crime_rate → better.
    Higher police_density, street_light_density → better.
    Lower emergency_response_time → better.
    """
    # Normalise each metric to 0-100 contribution
    crime      = _clamp(100 - zone.safety_crime_rate * 4)          # crime_rate 0-25 → 100-0
    police     = _clamp(zone.safety_police_density * 20)            # density 0-5 → 0-100
    response   = _clamp(100 - zone.safety_emergency_response_time * 3)  # 0-33 min → 100-0
    lighting   = _clamp(zone.safety_street_light_density)           # already 0-100

    return round((crime * 0.4 + police * 0.2 + response * 0.2 + lighting * 0.2), 1)


def _score_schools(zone) -> float:
    """
    Higher avg_school_rating, exam_performance_index → better.
    Lower student_teacher_ratio → better.
    More schools → better (capped).
    """
    rating  = _clamp(zone.schools_avg_rating * 10)                 # 0-10 → 0-100
    exam    = _clamp(zone.schools_exam_performance_index)          # already 0-100

    ratio   = zone.schools_student_teacher_ratio
    ratio_score = _clamp(100 - (ratio - 10) * 5) if ratio else 50  # ideal ≈ 10 students/teacher

    count   = _clamp(zone.schools_count * 10)                      # 0-10+ → 0-100

    return round((rating * 0.35 + exam * 0.35 + ratio_score * 0.2 + count * 0.1), 1)


def _score_transit(zone, preference: str) -> float:
    """
    Score changes based on commute preference.
    """
    pref = preference.lower().strip()

    bus_score   = _clamp(zone.transport_bus_stop_density * 10)     # 0-10 → 0-100
    congestion  = _clamp(100 - zone.transport_congestion_index * 10)
    commute_spd = _clamp(100 - zone.transport_avg_commute_time)    # lower minutes → better

    # Metro bonus / penalty
    has_metro   = zone.transport_metro_distance >= 0
    metro_score = _clamp(100 - zone.transport_metro_distance / 100) if has_metro else 0

    if pref == "metro":
        return round((metro_score * 0.5 + bus_score * 0.2 + commute_spd * 0.2 + congestion * 0.1), 1)
    elif pref == "bus":
        return round((bus_score * 0.5 + commute_spd * 0.3 + congestion * 0.2), 1)
    else:
        # car / walk — commute time & congestion matter most
        return round((commute_spd * 0.45 + congestion * 0.35 + bus_score * 0.2), 1)


def _score_budget(zone, max_budget: float) -> float:
    """
    How well does the zone fit inside the user's budget?
    budget_avg_rent ≤ max_budget → high score.
    Overshooting budget reduces score linearly.
    """
    if max_budget <= 0:
        return 50.0

    rent = zone.budget_avg_rent
    if rent <= 0:
        return 50.0

    ratio = rent / max_budget          # 1.0 = perfect fit, >1 = over budget
    if ratio <= 0.7:
        score = 100.0                  # very affordable
    elif ratio <= 1.0:
        score = 100 - (ratio - 0.7) * (100 / 0.3)  # 100 → 0 as ratio goes 0.7→1.0
        # Actually let's make it 100 → 70 for perfect match
        score = 70 + (1 - ratio) / 0.3 * 30
    else:
        # Over budget — penalise proportionally
        over = (ratio - 1.0)
        score = max(0, 70 - over * 200)

    return round(_clamp(score), 1)


# ==== Public API =========================================================

def compute_scores(zone, prefs: UserPreferences) -> ZoneScores:
    safety_pct  = _score_safety(zone)
    schools_pct = _score_schools(zone)
    transit_pct = _score_transit(zone, prefs.commute_preference)
    budget_pct  = _score_budget(zone, prefs.budget)

    # Weights from priorities
    w_safety   = _priority_weight(prefs.safety_priority)
    w_schools  = _priority_weight(prefs.schools_priority)
    w_transport = _priority_weight(prefs.transport_priority)
    w_budget   = 2   # budget is always factored in with "Important" weight

    total_weight = w_safety + w_schools + w_transport + w_budget
    if total_weight == 0:
        total_weight = 1   # prevent div-by-zero when all "Not"

    weighted_sum = (
        safety_pct  * w_safety
        + schools_pct * w_schools
        + transit_pct * w_transport
        + budget_pct  * w_budget
    )

    # Blend with livability_score (converted 0-10 → 0-100) at 15% weight
    livability_component = zone.livability_score * 10
    fit_score = weighted_sum / total_weight * 0.85 + livability_component * 0.15

    fit_score = round(_clamp(fit_score), 1)

    return ZoneScores(
        safety_pct=safety_pct,
        schools_pct=schools_pct,
        transit_pct=transit_pct,
        budget_pct=budget_pct,
        fit_score=fit_score,
        match_label=_match_label(fit_score),
    )


def rank_zones(zones, prefs: UserPreferences, top_n: int = 10) -> List[dict]:
    """
    Score and rank all zones, return top_n as a list of dicts
    merging zone attributes with computed scores.
    """
    results = []
    for zone in zones:
        scores = compute_scores(zone, prefs)
        results.append({
            "zone":   zone,
            "scores": scores,
        })

    results.sort(key=lambda x: x["scores"].fit_score, reverse=True)
    return results[:top_n]