"""Planten uit Plant Monitor (integratie `plant`, entiteiten plant.*) in kasten.

- Een kast kan planten bevatten (config["plants"]).
- Zit er geen enkel dier in de kast, dan stuurt de kast het klimaat op de
  grenswaarden van haar planten: elke plant telt als lid van de klimaatgroep,
  net zoals dieren die samen een toestel delen (overlap van de bereiken).
- Zitten er wel dieren in, dan zijn de planten voedsel en tellen ze niet mee.

De grenswaarden zijn number-entiteiten van Plant Monitor met unique_id
"<config_entry_id>-min-temperature", "-max-humidity", ... Ze worden via het
entiteitenregister gezocht, zodat hernoemde entity_id's blijven werken.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_conversion import TemperatureConverter

from .profile import Readings, target_temperature

CONF_PLANTS = "plants"
CONF_LIGHT_HOURS = "light_hours"
CONF_PLANT_CLIMATE = "plant_climate"
# Groeilampen uit zodra de lichtsom (DLI) van de planten bereikt is.
CONF_LIGHT_DLI = "light_dli"
ENCLOSURE_PLANT_KEYS = (CONF_PLANTS, CONF_LIGHT_HOURS, CONF_PLANT_CLIMATE)

# Grootheden die de klimaatregeling gebruikt (en die we tonen).
THRESHOLDS = ("temperature", "humidity", "illuminance", "dli", "moisture")

PLANT_ENTRY_TYPES = (
    "watered", "fertilized", "pruned", "repotted", "harvested", "pest", "sown", "moved", "note",
)

EVENT_PLANT_ENTRY = "arthropoda_plant_entry"

# Verzorging per plant: config["plant_care"] = {"plant.x": {"plant_water": 1, ...}}.
# Taaksoort -> handeling in het plantenlogboek die de taak afhandelt.
CONF_PLANT_CARE = "plant_care"
PLANT_CARE_KINDS = {"plant_water": "watered", "plant_fertilize": "fertilized"}


# Sproeien op bodemvocht en automatische pomp (zie watering.py)
CARE_MOISTURE = "water_on_moisture"
CARE_PUMP = "pump"
PUMP_DEFAULTS = {"pump_seconds": 5.0, "pump_max_per_day": 3.0, "pump_pause_minutes": 60.0}
PUMP_LIMITS = {"pump_seconds": 120.0, "pump_max_per_day": 24.0, "pump_pause_minutes": 1440.0}
PUMP_DOMAINS = ("switch.", "input_boolean.", "valve.", "script.")


def clean_plant_care(raw: Any, plants: list[str]) -> dict[str, dict[str, Any]]:
    """Alleen geldige instellingen voor planten die in de kast staan."""
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return result
    for plant, intervals in raw.items():
        if plant not in plants or not isinstance(intervals, dict):
            continue
        clean: dict[str, Any] = {}
        for kind in PLANT_CARE_KINDS:
            try:
                days = float(intervals.get(kind) or 0)
            except (TypeError, ValueError):
                continue
            if days > 0:
                clean[kind] = min(days, 365.0)
        if intervals.get(CARE_MOISTURE) is True:
            clean[CARE_MOISTURE] = True
        pump = intervals.get(CARE_PUMP)
        if isinstance(pump, str) and pump.startswith(PUMP_DOMAINS):
            clean[CARE_PUMP] = pump
            for key, default in PUMP_DEFAULTS.items():
                try:
                    value = float(intervals.get(key) or default)
                except (TypeError, ValueError):
                    value = default
                clean[key] = max(1.0, min(value, PUMP_LIMITS[key]))
        if clean:
            result[plant] = clean
    return result


def _number(hass: HomeAssistant, entity_id: str | None, temperature: bool = False) -> float | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    try:
        value = float(state.state)
    except ValueError:
        return None
    if temperature:
        unit = state.attributes.get("unit_of_measurement")
        if unit in (UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.KELVIN):
            value = TemperatureConverter.convert(value, unit, UnitOfTemperature.CELSIUS)
    return value


def plant_thresholds(hass: HomeAssistant, plant_entity_id: str) -> dict[str, list[float]]:
    """{grootheid: [min, max]} voor één plant; ontbrekende grootheden worden weggelaten."""
    registry = er.async_get(hass)
    entry = registry.async_get(plant_entity_id)
    if entry is None or not entry.config_entry_id:
        return {}
    result: dict[str, list[float]] = {}
    for quantity in THRESHOLDS:
        bounds = []
        for side in ("min", "max"):
            entity_id = registry.async_get_entity_id(
                "number", entry.platform, f"{entry.config_entry_id}-{side}-{quantity}"
            )
            bounds.append(_number(hass, entity_id, temperature=quantity == "temperature"))
        if bounds[0] is not None and bounds[1] is not None and bounds[0] <= bounds[1]:
            result[quantity] = [bounds[0], bounds[1]]
    return result


def plant_sensor(hass: HomeAssistant, plant_entity_id: str, quantity: str) -> str | None:
    """Sensor van Plant Monitor bij een plant: 'moisture' (bodemvocht) of 'dli' (lichtsom).

    Gezocht onder de sensoren van dezelfde integratie-entry: eerst op unique_id
    ("<entry>-current-moisture", "<entry>-dli"), anders op device_class/eenheid.
    """
    registry = er.async_get(hass)
    entry = registry.async_get(plant_entity_id)
    if entry is None or not entry.config_entry_id:
        return None
    sensors = [
        e for e in er.async_entries_for_config_entry(registry, entry.config_entry_id)
        if e.domain == "sensor"
    ]
    suffix = {"moisture": "-current-moisture", "dli": "-dli"}[quantity]
    for sensor in sensors:
        if (sensor.unique_id or "").endswith(suffix):
            return sensor.entity_id
    for sensor in sensors:
        state = hass.states.get(sensor.entity_id)
        attrs = state.attributes if state else {}
        device_class = sensor.device_class or sensor.original_device_class or attrs.get("device_class")
        unit = str(attrs.get("unit_of_measurement") or sensor.unit_of_measurement or "")
        if quantity == "moisture" and device_class == "moisture":
            return sensor.entity_id
        if quantity == "dli" and "mol" in unit and "/s" not in unit:
            return sensor.entity_id
    return None


def plant_reading(hass: HomeAssistant, plant_entity_id: str, quantity: str) -> float | None:
    """Actuele waarde van bodemvocht (%) of lichtsom (mol/m²/dag), None als onbekend."""
    return _number(hass, plant_sensor(hass, plant_entity_id, quantity))


def plant_info(hass: HomeAssistant, plant_entity_id: str) -> dict[str, Any]:
    """Naam, toestand, problemen en foto van een plant (voor paneel en werkscherm)."""
    state = hass.states.get(plant_entity_id)
    attrs = state.attributes if state else {}
    problems = attrs.get("problems")
    if isinstance(problems, str):
        problems = [p.strip() for p in problems.split(",") if p.strip() and p.strip() != "none"]
    statuses = {
        key[: -len("_status")]: value
        for key, value in attrs.items()
        if key.endswith("_status") and value not in (None, "", "ok")
    }
    return {
        "entity_id": plant_entity_id,
        "name": attrs.get("friendly_name") or plant_entity_id.split(".", 1)[-1],
        "state": state.state if state else "missing",
        "species": attrs.get("species"),
        "picture": attrs.get("entity_picture"),
        "problems": list(problems or []),
        "statuses": statuses,
        "thresholds": plant_thresholds(hass, plant_entity_id) if state else {},
        "moisture": plant_reading(hass, plant_entity_id, "moisture") if state else None,
        "dli": plant_reading(hass, plant_entity_id, "dli") if state else None,
    }


@dataclass(slots=True)
class _PlantRef:
    """Doet zich voor als `Animal` voor de klimaatregelaar (id + naam)."""

    id: str
    name: str


@dataclass(slots=True)
class PlantSnapshot:
    """Een plant in een plantenkast, als lid van een klimaatgroep.

    Heeft dezelfde velden als AnimalSnapshot die de klimaatregelaar gebruikt.
    """

    animal: _PlantRef
    enclosure_id: int
    config: dict[str, Any]
    values: dict[str, Any]
    readings: Readings
    is_day: bool
    day_start: datetime | None = None
    day_end: datetime | None = None
    climate_enabled: bool = True
    monitored: bool = True
    problems: list[str] = field(default_factory=list)
    # Lichtsom (DLI) van vandaag bereikt → groeilampen mogen uit (CONF_LIGHT_DLI).
    light_done: bool = False

    @property
    def target_temperature(self) -> list[float] | None:
        return target_temperature(self.values, self.is_day)


def plant_values(thresholds: dict[str, list[float]], light_hours: float | None) -> dict[str, Any]:
    """Grenswaarden van een plant omzetten naar profielwaarden van de regelaar."""
    values: dict[str, Any] = {}
    if "temperature" in thresholds:
        values["temp_day"] = thresholds["temperature"]
        values["temp_max_safe"] = thresholds["temperature"][1] + 3
    if "humidity" in thresholds:
        values["humidity"] = thresholds["humidity"]
    if light_hours:
        values["light_hours"] = float(light_hours)
    return values


def dli_status(hass: HomeAssistant, plants: list[str]) -> dict[str, Any]:
    """Lichtsom van een kast: doel = hoogste minimum-DLI, gemeten = laagste meting.

    Zo krijgt elke plant minstens haar minimum. Zonder doel of meting: niet bereikt.
    """
    targets = [t["dli"][0] for p in plants if (t := plant_thresholds(hass, p)).get("dli")]
    readings = [r for p in plants if (r := plant_reading(hass, p, "dli")) is not None]
    target = max(targets) if targets else None
    current = min(readings) if readings else None
    return {
        "target": target,
        "current": current,
        "reached": target is not None and current is not None and current >= target,
    }


def plants_steer(enclosure: dict[str, Any], has_animals: bool) -> bool:
    """Sturen de planten deze kast? Alleen zonder dieren en als het niet uitstaat."""
    cfg = enclosure.get("config") or {}
    return bool(cfg.get(CONF_PLANTS)) and not has_animals and cfg.get(CONF_PLANT_CLIMATE, True) is not False
