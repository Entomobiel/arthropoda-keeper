"""Inzichten per dier: voerweigering/premolt, vervelling, levensverwachting, kolonie.

Bewust zonder Home Assistant-afhankelijkheden (los te testen). Elk inzicht is een
dict {"key", "level" ("info" | "warn"), ...parameters}; het paneel maakt er tekst van.

- premolt_suspected: een dier dat kan vervellen weigerde N keer na elkaar voer.
  Het voederen pauzeert dan vanzelf (zoals bij een bevestigde premolt).
- refusing_food: een dier dat niet (meer) vervelt weigert herhaaldelijk voer.
- premolt_long: al heel lang in premolt.
- molt_overdue: de verwachte vervelling is ruim voorbij.
- lifespan / senior / beyond_lifespan / pairing_window: leeftijd t.o.v. de
  levensverwachting uit de caresheet (lifespan: female_years, male_years, years,
  adult_months, female_adult_months, male_adult_months).
- colony_declining / colony_trend: verloop van de tellingen van een kolonie.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

REFUSALS_MOLTING = 2  # na zoveel weigeringen: waarschijnlijk premolt
REFUSALS_OTHER = 3  # dier dat niet vervelt: waarschuwing
PREMOLT_LONG_DAYS = 90
PAIRING_WINDOW_DAYS = 180
COLONY_DROP = 0.30  # 30 % minder ...
COLONY_WINDOW_DAYS = 45  # ... binnen 45 dagen
YEAR = 365.25


def refusal_streak(history: list[tuple[str, datetime]]) -> int:
    """Aantal weigeringen na elkaar sinds de laatste (aanvaarde) voedering."""
    streak = 0
    for entry_type, _ts in history:  # nieuwste eerst
        if entry_type != "feeding_refused":
            break
        streak += 1
    return streak


def _range(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
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


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def lifespan(
    info: dict[str, Any],
    sex: str | None,
    born_at: str | None,
    acquired_at: str | None,
    stage: str | None,
    adult_since: datetime | None,
    today: date,
) -> dict[str, Any] | None:
    """Leeftijd en verwacht levenseinde (vroegst/laatst), of None zonder gegevens."""
    spans = info.get("lifespan") if isinstance(info, dict) else None
    if not isinstance(spans, dict):
        return None
    male = sex in ("male", "probably_male")
    female = sex in ("female", "probably_female")
    prefix = "male_" if male else "female_" if female else ""
    born = _date(born_at)
    estimated = born is None
    start = born or _date(acquired_at)
    end: tuple[date, date] | None = None
    basis = None
    # Na de laatste vervelling/uitkomst telt de levensduur als adult (bv. bidsprinkhanen).
    adult = _range(spans.get(f"{prefix}adult_months")) or _range(spans.get("adult_months"))
    adult_start = _date(adult_since)
    if stage == "adult" and adult and adult_start:
        end = (adult_start + timedelta(days=adult[0] * 30.44), adult_start + timedelta(days=adult[1] * 30.44))
        basis = "adult"
    years = _range(spans.get(f"{prefix}years")) or _range(spans.get("years"))
    if end is None and not prefix and not years:
        # Geslacht onbekend: van het kortste tot het langste van beide geslachten.
        both = [r for r in (_range(spans.get("female_years")), _range(spans.get("male_years"))) if r]
        if both:
            years = (min(r[0] for r in both), max(r[1] for r in both))
    if end is None and years and start:
        end = (start + timedelta(days=years[0] * YEAR), start + timedelta(days=years[1] * YEAR))
        basis = "age"
    if end is None:
        return None
    age_days = (today - start).days if start else None
    return {
        "age_days": age_days,
        "age_estimated": estimated,
        "end_min": end[0].isoformat(),
        "end_max": end[1].isoformat(),
        "remaining_min_days": (end[0] - today).days,
        "remaining_max_days": (end[1] - today).days,
        "basis": basis,
    }


def colony_trend(counts: list[tuple[datetime, float]], now: datetime) -> dict[str, Any] | None:
    """Verloop van een kolonie: laatste telling t.o.v. de oudste binnen het venster."""
    if len(counts) < 2:
        return None
    latest_ts, latest = counts[-1]
    window = [c for c in counts[:-1] if latest_ts - c[0] <= timedelta(days=COLONY_WINDOW_DAYS)]
    ref_ts, ref = (window[0] if window else counts[-2])
    if ref <= 0:
        return None
    change = (latest - ref) / ref
    return {
        "from": ref,
        "to": latest,
        "change": round(change, 3),
        "days": max(0, (latest_ts - ref_ts).days),
        "declining": change <= -COLONY_DROP and (latest_ts - ref_ts) <= timedelta(days=COLONY_WINDOW_DAYS),
        "stale_days": (now - latest_ts).days,
    }


def compute_insights(
    *,
    can_molt: bool,
    kind: str,
    premolt: bool,
    feeding_history: list[tuple[str, datetime]],
    premolt_since: datetime | None,
    molt_times: list[datetime],
    next_molt: datetime | None,
    life: dict[str, Any] | None,
    sex: str | None,
    stage: str | None,
    counts: list[tuple[datetime, float]],
    now: datetime,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    streak = refusal_streak(feeding_history)
    if kind == "individual":
        if can_molt and not premolt and streak >= REFUSALS_MOLTING:
            result.append({"key": "premolt_suspected", "level": "warn", "refusals": streak})
        elif not can_molt and streak >= REFUSALS_OTHER:
            result.append({"key": "refusing_food", "level": "warn", "refusals": streak})
        if premolt and premolt_since is not None:
            days = (now - premolt_since).days
            if days > PREMOLT_LONG_DAYS:
                result.append({"key": "premolt_long", "level": "warn", "days": days})
        if can_molt and next_molt is not None and len(molt_times) >= 2:
            interval = molt_times[-1] - molt_times[-2]
            if now > next_molt + interval / 2:
                result.append({"key": "molt_overdue", "level": "info",
                               "expected": next_molt.isoformat(), "days": (now - next_molt).days})
    if life is not None:
        lo, hi = life["remaining_min_days"], life["remaining_max_days"]
        if hi < 0:
            result.append({"key": "beyond_lifespan", "level": "info", **life})
        elif sex in ("male", "probably_male") and stage == "adult" and hi <= PAIRING_WINDOW_DAYS:
            # Volwassen mannetje met weinig tijd: nu koppelen.
            result.append({"key": "pairing_window", "level": "warn", **life})
        elif lo <= 0:
            result.append({"key": "senior", "level": "info", **life})
        else:
            result.append({"key": "lifespan", "level": "info", **life})
    if kind == "colony":
        trend = colony_trend(counts, now)
        if trend is not None:
            result.append({"key": "colony_declining" if trend["declining"] else "colony_trend",
                           "level": "warn" if trend["declining"] else "info", **trend})
    return result


def premolt_suspected(insights: list[dict[str, Any]]) -> bool:
    return any(i["key"] == "premolt_suspected" for i in insights)
