"""Nestmodules van een kast (bv. gipsblokken met één kamer, foerageerbak, reageerbuis).

config["modules"] = [
  {"id": "m1a2", "name": "Kamer 1", "kind": "chamber" | "outworld" | "tube",
   "role": "brood" | "waste" | "dry" | "wet" | "",
   "temperature_sensor": "sensor.x", "humidity_sensor": "sensor.y",
   "moisture_sensor": "sensor.z",          # bv. geleiding van het gips
   "humidity_min": 70, "moisture_min": 30,  # onder deze waarde: bevochtigen
   "wet_every_days": 7,                     # zonder sensor: vast interval
   "wetted_at": "2026-11-13T10:00:00+00:00"}
]

Bevochtigtaak ("module_wet") per module:
- met een vocht- of luchtvochtsensor en een minimum: zodra de waarde eronder zakt;
- anders elke `wet_every_days` dagen na de laatste keer bevochtigen.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import secrets
from typing import Any

MODULE_KINDS = ("chamber", "outworld", "tube")
MODULE_ROLES = ("", "brood", "waste", "dry", "wet", "food")
SENSOR_FIELDS = ("temperature_sensor", "humidity_sensor", "moisture_sensor")
NUMBER_FIELDS = {"humidity_min": (0, 100), "moisture_min": (0, 100), "wet_every_days": (0.5, 365)}
MAX_MODULES = 24


def clean_modules(raw: Any, old: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Geldige modules; 'wetted_at' blijft behouden van de vorige versie."""
    if not isinstance(raw, list):
        return []
    previous = {m.get("id"): m for m in (old or []) if isinstance(m, dict)}
    result = []
    for item in raw[:MAX_MODULES]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()[:60]
        if not name:
            continue
        module_id = str(item.get("id") or "") or secrets.token_hex(3)
        clean: dict[str, Any] = {
            "id": module_id,
            "name": name,
            "kind": item.get("kind") if item.get("kind") in MODULE_KINDS else "chamber",
            "role": item.get("role") if item.get("role") in MODULE_ROLES else "",
        }
        for key in SENSOR_FIELDS:
            value = item.get(key)
            if isinstance(value, str) and value.startswith(("sensor.", "input_number.")):
                clean[key] = value
        for key, (lo, hi) in NUMBER_FIELDS.items():
            try:
                value = float(item.get(key))
            except (TypeError, ValueError):
                continue
            clean[key] = max(lo, min(value, hi))
        wetted = item.get("wetted_at") or previous.get(module_id, {}).get("wetted_at")
        if wetted:
            clean["wetted_at"] = str(wetted)
        result.append(clean)
    return result


def module_sensors(modules: list[dict[str, Any]]) -> set[str]:
    return {m[k] for m in modules for k in SENSOR_FIELDS if m.get(k)}


def wet_due(
    module: dict[str, Any],
    values: dict[str, float | None],
    dry_since: datetime | None,
    created: datetime,
    now: datetime,
) -> tuple[datetime | None, datetime | None]:
    """(vervaldag of None, nieuwe dry_since) voor het bevochtigen van één module.

    `values` = actuele {"humidity": .., "moisture": ..} van de module.
    """
    checks = [(values.get("moisture"), module.get("moisture_min")),
              (values.get("humidity"), module.get("humidity_min"))]
    measured = [(v, lo) for v, lo in checks if v is not None and lo is not None]
    if measured:
        if any(v < lo for v, lo in measured):
            since = dry_since or now
            return since, since
        return None, None
    every = module.get("wet_every_days")
    if not every:
        return None, None
    last = None
    if module.get("wetted_at"):
        try:
            last = datetime.fromisoformat(module["wetted_at"])
        except ValueError:
            last = None
    return (last or created) + timedelta(days=float(every)), None
