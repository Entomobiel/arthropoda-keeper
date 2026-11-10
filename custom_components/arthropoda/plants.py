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
ENCLOSURE_PLANT_KEYS = (CONF_PLANTS, CONF_LIGHT_HOURS, CONF_PLANT_CLIMATE)

# Grootheden die de klimaatregeling gebruikt (en die we tonen).
THRESHOLDS = ("temperature", "humidity", "illuminance", "dli", "moisture")

PLANT_ENTRY_TYPES = (
    "watered", "fertilized", "pruned", "repotted", "harvested", "pest", "sown", "note",
)


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


def plants_steer(enclosure: dict[str, Any], has_animals: bool) -> bool:
    """Sturen de planten deze kast? Alleen zonder dieren en als het niet uitstaat."""
    cfg = enclosure.get("config") or {}
    return bool(cfg.get(CONF_PLANTS)) and not has_animals and cfg.get(CONF_PLANT_CLIMATE, True) is not False
