"""Regelbeslissingen voor klimaatactuatoren (pure functies, zonder Home Assistant).

Elke functie krijgt metingen en doelwaarden en geeft een `Decision` terug.
De klimaatregelaar voert die beslissingen uit en bewaakt de schakeltijden.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean

# Als een caresheet geen temp_max_safe heeft: zoveel graden boven het maximum
# geldt als gevaarlijk (verwarming onmiddellijk uit + kritieke melding).
DEFAULT_SAFE_MARGIN = 5.0

# Proportionele regeling (dimbare verwarming): % vermogen per °C afwijking.
PROPORTIONAL_GAIN = 25.0


@dataclass(slots=True)
class Decision:
    """Wat er met een actuator moet gebeuren.

    on:    True/False = aan/uit zetten, None = laten zoals hij is
    level: 0–100 % voor dimbare apparaten (None = niet dimmen)
    """

    on: bool | None
    reason: str
    level: float | None = None
    critical: bool = False
    setpoint: float | None = None


def combine_ranges(ranges: list[list[float] | None]) -> tuple[list[float] | None, bool]:
    """Gezamenlijk doelbereik van dieren die een actuator delen.

    Geeft (bereik, conflict). Bij overlap is het bereik de doorsnede. Zonder
    overlap is er een conflict, en dan wordt het gemiddelde van de minima en
    maxima gebruikt.
    """
    valid = [r for r in ranges if r]
    if not valid:
        return None, False
    lo = max(r[0] for r in valid)
    hi = min(r[1] for r in valid)
    if lo <= hi:
        return [lo, hi], False
    lo_avg = round(mean(r[0] for r in valid), 2)
    hi_avg = round(mean(r[1] for r in valid), 2)
    return [min(lo_avg, hi_avg), max(lo_avg, hi_avg)], True


def safe_maximum(target: list[float] | None, explicit: float | None) -> float | None:
    """Temperatuur waarboven de verwarming altijd uit moet."""
    if explicit is not None:
        return explicit
    if target:
        return target[1] + DEFAULT_SAFE_MARGIN
    return None


def heater(
    temps: list[float],
    target: list[float] | None,
    safe_max: float | None,
    is_on: bool,
    hysteresis: float,
    sensor_problem: bool,
    proportional: bool = False,
) -> Decision:
    """Thermostaat met hysterese rond het midden van het doelbereik.

    Veiligheid gaat altijd voor:
    - geen geldige meting → uit (fail-safe)
    - warmste sensor ≥ veiligheidsmaximum → uit, kritiek
    - warmste sensor > bovengrens → uit
    """
    if sensor_problem or not temps:
        return Decision(False, "sensor_unavailable", level=0 if proportional else None)
    if not target:
        return Decision(None, "no_target")

    lo, hi = target
    setpoint = round((lo + hi) / 2, 2)
    hottest = max(temps)
    if safe_max is not None and hottest >= safe_max:
        return Decision(False, "over_safe_max", level=0 if proportional else None,
                        critical=True, setpoint=setpoint)
    if hottest > hi:
        return Decision(False, "above_max", level=0 if proportional else None, setpoint=setpoint)

    current = mean(temps)
    if proportional:
        level = max(0.0, min(100.0, 50.0 + (setpoint - current) * PROPORTIONAL_GAIN))
        return Decision(level > 0, "proportional", level=round(level), setpoint=setpoint)
    if current < setpoint - hysteresis:
        return Decision(True, "below_setpoint", setpoint=setpoint)
    if current > setpoint + hysteresis:
        return Decision(False, "above_setpoint", setpoint=setpoint)
    return Decision(is_on, "within_hysteresis", setpoint=setpoint)


def mister(
    humidity: float | None,
    target: list[float] | None,
    now: datetime,
    last_pulse: datetime | None,
    pulses_today: int,
    max_per_day: int,
    min_pause: timedelta,
    scheduled_due: bool,
) -> Decision:
    """Moet er nu een vernevelpuls gegeven worden? (on=True = puls geven)

    Vaste tijdstippen gaan altijd door. Op vochtigheid wordt alleen genevel
    met een geldige meting, na de minimale pauze en onder het daglimiet.
    """
    if scheduled_due:
        return Decision(True, "schedule")
    if humidity is None:
        return Decision(False, "sensor_unavailable")
    if not target:
        return Decision(False, "no_target")
    if humidity >= target[0]:
        return Decision(False, "humidity_ok")
    if last_pulse is not None and now - last_pulse < min_pause:
        return Decision(False, "pause")
    if max_per_day and pulses_today >= max_per_day:
        return Decision(False, "daily_limit")
    return Decision(True, "humidity_low")


def fan(
    temps: list[float],
    humidity: float | None,
    t_target: list[float] | None,
    h_target: list[float] | None,
    is_on: bool,
    t_hysteresis: float = 0.5,
    h_hysteresis: float = 3.0,
) -> Decision:
    """Ventilator aan bij te hoge vochtigheid of temperatuur, met hysterese."""
    too_humid = humidity is not None and h_target is not None and humidity > h_target[1]
    too_warm = bool(temps) and t_target is not None and max(temps) > t_target[1]
    if too_humid:
        return Decision(True, "humidity_high")
    if too_warm:
        return Decision(True, "temperature_high")
    humid_ok = humidity is None or h_target is None or humidity < h_target[1] - h_hysteresis
    warm_ok = not temps or t_target is None or max(temps) < t_target[1] - t_hysteresis
    if humid_ok and warm_ok:
        return Decision(False, "within_range")
    return Decision(is_on, "within_hysteresis")


def light(
    is_day: bool,
    now: datetime,
    day_start: datetime | None,
    day_end: datetime | None,
    ramp_minutes: float,
) -> Decision:
    """Licht volgens het dagritme, optioneel geleidelijk op- en afdimmen."""
    if not is_day:
        return Decision(False, "night", level=0)
    if not ramp_minutes or day_start is None or day_end is None:
        return Decision(True, "day", level=100)
    since_start = (now - day_start).total_seconds() / 60
    until_end = (day_end - now).total_seconds() / 60
    fraction = min(1.0, since_start / ramp_minutes, until_end / ramp_minutes)
    level = max(1, round(fraction * 100))
    reason = "sunrise" if since_start < ramp_minutes else "sunset" if until_end < ramp_minutes else "day"
    return Decision(True, reason, level=level)


def parse_times(text: str | None) -> list[tuple[int, int]]:
    """'08:00, 20:30' → [(8, 0), (20, 30)]. Ongeldige delen worden genegeerd."""
    result = []
    for part in (text or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            hour, minute = (int(x) for x in part.split(":")[:2])
        except ValueError:
            continue
        if 0 <= hour < 24 and 0 <= minute < 60:
            result.append((hour, minute))
    return result
