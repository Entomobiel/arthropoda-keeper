"""Actief verzorgingsprofiel bepalen en de status evalueren.

Geen Home Assistant-afhankelijkheden, zodat dit los testbaar is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import STAGE_FALLBACK
from .control import safe_maximum
from .models import CareProfile


def _stage_candidates(stage: str | None) -> list[str]:
    if not stage:
        return []
    return [stage, *STAGE_FALLBACK.get(stage, [])]


def _pick_stage(profiles: list[CareProfile], stage: str | None) -> list[CareProfile]:
    """Generieke profielen + de best passende levensfase (in die volgorde)."""
    generic = [p for p in profiles if p.stage is None]
    for candidate in _stage_candidates(stage):
        matching = [p for p in profiles if p.stage == candidate]
        if matching:
            return generic + matching
    return generic


def resolve_profile(
    profiles: list[CareProfile],
    stage: str | None,
    season_mode: str,
    month: int,
) -> tuple[dict[str, Any], str]:
    """Voeg profielen samen tot de waarden die nu gelden.

    Volgorde (latere overschrijft eerdere): generiek normaal → levensfase normaal
    → generiek seizoen → levensfase seizoen.

    Geeft (waarden, actief seizoen) terug.
    """
    normal = [p for p in profiles if p.season == "normal"]
    seasonal = [p for p in profiles if p.season != "normal"]

    if season_mode == "auto":
        active = [p for p in seasonal if p.months and month in p.months]
        season = active[0].season if active else "normal"
        active = [p for p in active if p.season == season]
    elif season_mode == "normal":
        active, season = [], "normal"
    else:
        active, season = [p for p in seasonal if p.season == season_mode], season_mode

    merged: dict[str, Any] = {}
    for profile in _pick_stage(normal, stage) + _pick_stage(active, stage):
        merged.update({k: v for k, v in profile.values.items() if v is not None})
    return merged, season


@dataclass(slots=True)
class Readings:
    """Actuele sensorwaarden (temperaturen in °C)."""

    temperatures: list[float] = field(default_factory=list)
    humidity: float | None = None
    water_temperature: float | None = None
    unavailable: list[str] = field(default_factory=list)

    @property
    def temperature(self) -> float | None:
        if not self.temperatures:
            return None
        return round(sum(self.temperatures) / len(self.temperatures), 2)


def _check_range(
    value: float | None, rng: Any, low: str, high: str, problems: list[str]
) -> None:
    if value is None or not rng:
        return
    lo, hi = rng
    if lo is not None and value < lo:
        problems.append(low)
    elif hi is not None and value > hi:
        problems.append(high)


def safe_temperature(values: dict[str, Any]) -> float | None:
    """Gevaarlijke temperatuur: temp_max_safe, anders dagmaximum + marge."""
    return safe_maximum(values.get("temp_day") or values.get("temp_night"),
                        values.get("temp_max_safe"))


def target_temperature(values: dict[str, Any], is_day: bool) -> list[float] | None:
    """Doelbereik temperatuur voor nu (nacht valt terug op dag)."""
    if is_day:
        return values.get("temp_day")
    return values.get("temp_night") or values.get("temp_day")


def evaluate(
    values: dict[str, Any],
    readings: Readings,
    is_day: bool,
    days_since: dict[str, int | None],
    feeding_paused: bool,
) -> list[str]:
    """Lijst met problemen (lege lijst = alles ok)."""
    problems: list[str] = []

    if readings.unavailable:
        problems.append("sensor_unavailable")

    t_range = target_temperature(values, is_day)
    if readings.temperatures and t_range:
        lo, hi = t_range
        if min(readings.temperatures) < lo:
            problems.append("temperature_low")
        if max(readings.temperatures) > hi:
            problems.append("temperature_high")
        safe = safe_temperature(values)
        if safe is not None and max(readings.temperatures) >= safe:
            problems.insert(0, "temperature_critical")

    _check_range(
        readings.humidity, values.get("humidity"), "humidity_low", "humidity_high", problems
    )
    _check_range(
        readings.water_temperature,
        values.get("water_temp"),
        "water_temperature_low",
        "water_temperature_high",
        problems,
    )

    def overdue(counter: str, interval_key: str) -> bool:
        interval = values.get(interval_key)
        days = days_since.get(counter)
        return bool(interval) and days is not None and days > interval

    if not feeding_paused and overdue("feeding", "feeding_interval_days"):
        problems.append("feeding_overdue")
    if overdue("cleaning", "cleaning_interval_days"):
        problems.append("cleaning_overdue")
    if overdue("water_change", "water_change_interval_days"):
        problems.append("water_change_overdue")

    return problems
