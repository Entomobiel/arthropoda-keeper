"""Mierenkolonies: telling, levensfase, stichting, voedselstromen en inzichten.

Bewust zonder Home Assistant-afhankelijkheden (los te testen).

Een dier is een mierenkolonie als de soort tot de groep "ant" hoort of als het
dier zelf een blok `info["ant"]` heeft (handig voor koninginnen die nog
gedetermineerd moeten worden).

Instellingen komen uit de caresheet (`species.info["ant"]`) en kunnen per
kolonie overschreven worden (`animal.info["ant"]`):
- type: generalist | harvester (oogstmier, zaden) | leafcutter (bladsnijder) |
  predator | honeypot
- founding: claustral (niet voederen tijdens de stichting) | semi_claustral |
  parasitic | unknown
- polygyne, polymorphic (majors/soldaten)
- development_days: {egg: [min, max], larva: [...], pupa: [...]} of
  {egg_to_worker: [min, max]}
- food: {water: dagen, sugar: dagen, protein: dagen, seeds: dagen, leaves: dagen}
- queen_check_days: na hoeveel dagen 'koningin niet gezien' gemeld wordt
Per kolonie ook: stage (founding | nanitics | growing | mature; leeg = automatisch),
caught_place, queen_count.

Telling (dagboektype "census"), data:
  queen: seen | not_seen | dead, queens: aantal (polygyn),
  workers: aantal, eggs/larvae/pupae: 0 geen · 1 weinig · 2 matig · 3 veel,
  majors: aantal, alates: true/false
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

ANT_GROUP = "ant"
STREAMS = ("water", "sugar", "protein", "seeds", "leaves")
# Voedselstroom -> (taaksoort, dagboektype)
STREAM_TASKS = {
    "water": ("ant_water", "water_refill"),
    "sugar": ("ant_sugar", "feed_sugar"),
    "protein": ("ant_protein", "feeding"),
    "seeds": ("ant_seeds", "feed_seeds"),
    "leaves": ("ant_leaves", "feed_leaves"),
}
# Standaard voedselstromen (dagen) per type mier.
TYPE_FOOD: dict[str, dict[str, float]] = {
    "generalist": {"water": 7, "sugar": 4, "protein": 4},
    "harvester": {"water": 7, "seeds": 7, "protein": 7},
    "leafcutter": {"water": 3, "leaves": 1, "sugar": 7},
    "predator": {"water": 7, "protein": 3},
    "honeypot": {"water": 7, "sugar": 3, "protein": 5},
}
STAGES = ("founding", "nanitics", "growing", "mature")
NANITICS_MAX = 20  # tot zoveel werksters: eerste (kleine) werksters
MATURE_WORKERS = 500  # vanaf zoveel werksters (of gevleugelden): volwassen
QUEEN_CHECK_DAYS = 60
LEFTOVER_DAYS = 2  # restjes eiwit na zoveel dagen weghalen
FOUNDING_GRACE = timedelta(days=14)


def is_ant(species_group: str | None, info: dict[str, Any] | None) -> bool:
    return species_group == ANT_GROUP or bool((info or {}).get("ant"))


def _range(value: Any) -> tuple[float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            lo, hi = float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
        return (min(lo, hi), max(lo, hi))
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return (number, number)


def settings(species_info: dict[str, Any] | None, colony_info: dict[str, Any] | None) -> dict[str, Any]:
    """Instellingen van een kolonie: caresheet, overschreven door de kolonie zelf."""
    sheet = dict((species_info or {}).get("ant") or {})
    own = dict((colony_info or {}).get("ant") or {})
    ant_type = own.get("type") or sheet.get("type") or "generalist"
    food = dict(TYPE_FOOD.get(ant_type, TYPE_FOOD["generalist"]))
    food.update({k: v for k, v in (sheet.get("food") or {}).items() if k in STREAMS})
    for key, value in (own.get("food") or {}).items():
        if key in STREAMS:
            if value in (None, "", 0):
                food.pop(key, None)  # stroom uitgezet
            else:
                food[key] = value
    return {
        "type": ant_type,
        "founding": own.get("founding") or sheet.get("founding") or "unknown",
        "polygyne": bool(own.get("polygyne", sheet.get("polygyne", False))),
        "polymorphic": bool(own.get("polymorphic", sheet.get("polymorphic", False))),
        "development_days": sheet.get("development_days") or {},
        "food": {k: float(v) for k, v in food.items() if v},
        "queen_check_days": float(own.get("queen_check_days") or sheet.get("queen_check_days") or QUEEN_CHECK_DAYS),
        "stage": own.get("stage") if own.get("stage") in STAGES else None,
        "caught_place": own.get("caught_place"),
    }


def _first(census: list[tuple[datetime, dict[str, Any]]], key: str) -> datetime | None:
    for ts, data in census:
        try:
            if float(data.get(key) or 0) > 0:
                return ts
        except (TypeError, ValueError):
            continue
    return None


def _latest(census: list[tuple[datetime, dict[str, Any]]], key: str) -> tuple[datetime, Any] | None:
    for ts, data in reversed(census):
        if data.get(key) not in (None, ""):
            return ts, data[key]
    return None


def expected_first_workers(dev: dict[str, Any], first_eggs: datetime | None) -> tuple[datetime, datetime] | None:
    """Verwachte eerste werksters: eerste eitjes + ontwikkelingstijd (min–max)."""
    if first_eggs is None:
        return None
    total = _range(dev.get("egg_to_worker"))
    if total is None:
        parts = [_range(dev.get(k)) for k in ("egg", "larva", "pupa")]
        if not all(parts):
            return None
        total = (sum(p[0] for p in parts), sum(p[1] for p in parts))
    return first_eggs + timedelta(days=total[0]), first_eggs + timedelta(days=total[1])


def colony_state(
    census: list[tuple[datetime, dict[str, Any]]],
    cfg: dict[str, Any],
    started: datetime | None,
    now: datetime,
) -> dict[str, Any]:
    """Toestand van de kolonie uit de tellingen."""
    queen_seen = None
    queen_status = None
    for ts, data in reversed(census):
        q = data.get("queen")
        if queen_status is None and q in ("seen", "not_seen", "dead"):
            queen_status = q
        if q == "seen":
            queen_seen = ts
            break
    if queen_status is None and census:
        queen_status = "unknown"
    workers = _latest(census, "workers")
    queens = _latest(census, "queens")
    brood = {}
    last = census[-1][1] if census else {}
    for key in ("eggs", "larvae", "pupae"):
        try:
            brood[key] = int(last.get(key)) if last.get(key) not in (None, "") else None
        except (TypeError, ValueError):
            brood[key] = None
    majors = _latest(census, "majors")
    alates = any(bool(d.get("alates")) for _ts, d in census)
    first = {k: _first(census, k) for k in ("eggs", "larvae", "pupae", "workers")}
    worker_count = int(workers[1]) if workers else None
    stage = cfg.get("stage")
    if stage is None:
        if not worker_count:
            stage = "founding"
        elif worker_count >= MATURE_WORKERS or alates:
            stage = "mature"
        elif worker_count <= NANITICS_MAX:
            stage = "nanitics"
        else:
            stage = "growing"
    expected = expected_first_workers(cfg.get("development_days") or {}, first["eggs"] or (started if stage == "founding" else None))
    return {
        "stage": stage,
        "queen": {
            "status": queen_status,
            "last_seen": queen_seen.isoformat() if queen_seen else None,
            "count": int(queens[1]) if queens else None,
        },
        "workers": worker_count,
        "workers_at": workers[0].isoformat() if workers else None,
        "brood": brood,
        "majors": int(majors[1]) if majors else None,
        "alates": alates,
        "first": {k: v.isoformat() if v else None for k, v in first.items()},
        "expected_workers": [e.isoformat() for e in expected] if expected and not first["workers"] else None,
        "census_count": len(census),
        "last_census": census[-1][0].isoformat() if census else None,
    }


def feeding_blocked(state: dict[str, Any], cfg: dict[str, Any]) -> bool:
    """Claustrale stichting: niet voederen en niet storen."""
    return state["stage"] == "founding" and cfg["founding"] == "claustral"


def stream_intervals(state: dict[str, Any], cfg: dict[str, Any]) -> dict[str, float]:
    """Intervallen per voedselstroom; veel larven = vaker eiwit."""
    food = dict(cfg["food"])
    larvae = state["brood"].get("larvae")
    if "protein" in food and larvae is not None and larvae >= 2:
        food["protein"] = max(1.0, round(food["protein"] * 2 / 3, 1))
    return food


def stream_dues(
    state: dict[str, Any],
    cfg: dict[str, Any],
    last_by_type: dict[str, datetime],
    baseline: datetime,
    paused: bool,
) -> list[tuple[str, datetime, float]]:
    """(taaksoort, vervaldag, interval) per voedselstroom, plus restjes eiwit."""
    if paused or feeding_blocked(state, cfg):
        return []
    result = []
    for stream, days in stream_intervals(state, cfg).items():
        kind, entry_type = STREAM_TASKS[stream]
        last = last_by_type.get(entry_type) or baseline
        result.append((kind, last + timedelta(days=days), days))
    protein = last_by_type.get("feeding")
    cleaned = last_by_type.get("remove_leftovers")
    if "protein" in cfg["food"] and protein and (cleaned is None or cleaned < protein):
        result.append(("ant_leftovers", protein + timedelta(days=LEFTOVER_DAYS), 0.0))
    return result


def ant_insights(state: dict[str, Any], cfg: dict[str, Any], diapause: bool, now: datetime) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    queen = state["queen"]
    if feeding_blocked(state, cfg):
        result.append({"key": "claustral_founding", "level": "info"})
    if queen["status"] == "dead":
        result.append({"key": "queen_dead", "level": "warn"})
    elif state["census_count"]:
        last_seen = datetime.fromisoformat(queen["last_seen"]) if queen["last_seen"] else None
        days = (now - last_seen).days if last_seen else None
        if (days is None or days > cfg["queen_check_days"]) and not diapause:
            result.append({"key": "queen_not_seen", "level": "warn", "days": days})
    else:
        result.append({"key": "no_census", "level": "info"})
    if state["stage"] == "founding" and state["expected_workers"]:
        lo, hi = (datetime.fromisoformat(x) for x in state["expected_workers"])
        result.append({"key": "founding_slow" if now > hi + FOUNDING_GRACE else "founding_progress",
                       "level": "warn" if now > hi + FOUNDING_GRACE else "info",
                       "expected_min": lo.isoformat(), "expected_max": hi.isoformat(),
                       "first_eggs": state["first"]["eggs"]})
    brood = state["brood"]
    if (state["census_count"] >= 1 and not diapause and state["stage"] != "founding"
            and all(brood.get(k) == 0 for k in ("eggs", "larvae", "pupae"))):
        result.append({"key": "no_brood", "level": "warn"})
    if "protein" in cfg["food"] and (brood.get("larvae") or 0) >= 2:
        result.append({"key": "larvae_protein", "level": "info",
                       "days": stream_intervals(state, cfg)["protein"]})
    return result
