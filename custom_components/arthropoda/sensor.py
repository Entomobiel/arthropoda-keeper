"""Sensoren per dier: klimaat, status, stadium, tellers en metingen."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfMass,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HUMIDITY_SENSOR,
    CONF_TEMPERATURE_SENSORS,
    CONF_WATER_TEMPERATURE_SENSOR,
    STAGES,
)
from .coordinator import AnimalSnapshot
from .entity import ArthropodaEntity, HubEntity, add_animal_entities


@dataclass(frozen=True, kw_only=True)
class AnimalSensorDescription(SensorEntityDescription):
    """Beschrijving van een diersensor."""

    value_fn: Callable[[AnimalSnapshot], Any]
    exists_fn: Callable[[AnimalSnapshot], bool] = lambda s: True
    attrs_fn: Callable[[AnimalSnapshot], dict[str, Any]] | None = None


def _range_value(key: str, index: int):
    """Min (0) of max (1) van een doelbereik; 'temp' volgt dag/nacht."""

    def fn(s: AnimalSnapshot):
        rng = s.target_temperature if key == "temp" else s.values.get(key)
        return rng[index] if rng else None

    return fn


def _measurement(kind: str):
    def fn(s: AnimalSnapshot):
        m = s.bundle.measurements.get(kind)
        return m.value if m else None

    return fn


def _status(s: AnimalSnapshot) -> str:
    if not s.monitored:
        return "inactive"
    return "problem" if s.problems else "ok"


def _status_attrs(s: AnimalSnapshot) -> dict[str, Any]:
    animal = s.animal
    species = s.bundle.species
    return {
        "problems": s.problems,
        "animal_status": animal.status,
        "species": species.scientific_name if species else None,
        "common_names": species.common_names if species else None,
        "group": species.group if species else None,
        "kind": animal.kind,
        "sex": animal.sex,
        "season": s.season,
        "is_day": s.is_day,
        "feeding_paused": s.feeding_paused,
        "profile": s.values,
    }


def _has(key: str) -> Callable[[AnimalSnapshot], bool]:
    return lambda s: bool(s.config.get(key))


def _individual(s: AnimalSnapshot) -> bool:
    return s.animal.kind == "individual"


def _molts(s: AnimalSnapshot) -> bool:
    """Vervellingssensoren: als het dier nog kan vervellen, of al vervellingen heeft."""
    return s.can_molt or s.bundle.molt_count > 0


def _climate_status(s: AnimalSnapshot) -> str:
    if not s.has_actuators:
        return "monitoring"
    return "active" if s.climate_enabled and s.monitored else "paused"


def _is_aquatic(s: AnimalSnapshot) -> bool:
    species = s.bundle.species
    return bool(s.config.get(CONF_WATER_TEMPERATURE_SENSOR)) or bool(
        species and species.habitat in ("aquatic", "semi_aquatic")
    )


def _days(counter: str) -> dict[str, Any]:
    return {
        "native_unit_of_measurement": UnitOfTime.DAYS,
        "state_class": SensorStateClass.MEASUREMENT,
        "value_fn": lambda s: s.days_since.get(counter),
        "suggested_display_precision": 0,
    }


SENSORS: tuple[AnimalSensorDescription, ...] = (
    AnimalSensorDescription(
        key="status",
        device_class=SensorDeviceClass.ENUM,
        options=["ok", "problem", "inactive"],
        value_fn=_status,
        attrs_fn=_status_attrs,
    ),
    AnimalSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda s: s.readings.temperature,
        exists_fn=_has(CONF_TEMPERATURE_SENSORS),
        attrs_fn=lambda s: {
            "min": min(s.readings.temperatures, default=None),
            "max": max(s.readings.temperatures, default=None),
            "sources": s.config.get(CONF_TEMPERATURE_SENSORS),
        },
    ),
    AnimalSensorDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda s: s.readings.humidity,
        exists_fn=_has(CONF_HUMIDITY_SENSOR),
    ),
    AnimalSensorDescription(
        key="water_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda s: s.readings.water_temperature,
        exists_fn=_has(CONF_WATER_TEMPERATURE_SENSOR),
    ),
    AnimalSensorDescription(
        key="stage",
        device_class=SensorDeviceClass.ENUM,
        options=STAGES,
        value_fn=lambda s: s.animal.stage,
    ),
    AnimalSensorDescription(
        key="instar",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.animal.instar,
        exists_fn=_individual,
    ),
    AnimalSensorDescription(
        key="molt_count",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda s: s.bundle.molt_count,
        exists_fn=_molts,
    ),
    AnimalSensorDescription(
        key="colony_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.animal.count,
        exists_fn=lambda s: s.animal.kind == "colony",
    ),
    AnimalSensorDescription(key="days_since_feeding", **_days("feeding")),
    AnimalSensorDescription(key="days_since_molt", exists_fn=_molts, **_days("molt")),
    AnimalSensorDescription(key="days_since_cleaning", **_days("cleaning")),
    AnimalSensorDescription(key="days_since_substrate_change", **_days("substrate_change")),
    AnimalSensorDescription(
        key="days_since_water_change", exists_fn=_is_aquatic, **_days("water_change")
    ),
    AnimalSensorDescription(
        key="next_feeding",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda s: s.next_feeding,
    ),
    AnimalSensorDescription(
        key="length",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_measurement("length_mm"),
        entity_registry_enabled_default=False,
    ),
    AnimalSensorDescription(
        key="legspan",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_measurement("legspan_mm"),
        entity_registry_enabled_default=False,
    ),
    AnimalSensorDescription(
        key="weight",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_measurement("weight_g"),
        entity_registry_enabled_default=False,
    ),
    AnimalSensorDescription(
        key="target_temperature_min",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_range_value("temp", 0),
    ),
    AnimalSensorDescription(
        key="target_temperature_max",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_range_value("temp", 1),
    ),
    AnimalSensorDescription(
        key="target_humidity_min",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_range_value("humidity", 0),
    ),
    AnimalSensorDescription(
        key="target_humidity_max",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_range_value("humidity", 1),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    controller = entry.runtime_data.controller

    def factory(coordinator, animal_id, snap) -> Iterable[SensorEntity]:
        entities: list[SensorEntity] = [
            AnimalSensor(coordinator, animal_id, desc)
            for desc in SENSORS
            if desc.exists_fn(snap)
        ]
        entities.append(ClimateControlSensor(coordinator, animal_id, controller))
        return entities

    add_animal_entities(entry, async_add_entities, factory)
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [OpenTasksSensor(coordinator), ProblemAnimalsSensor(coordinator), LowStockSensor(coordinator)]
    )


class OpenTasksSensor(HubEntity, SensorEntity):
    """Aantal taken dat vandaag (of eerder) moet gebeuren."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "open_tasks")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.due_tasks())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "tasks": [
                {
                    "animal": data[t.animal_id].animal.name,
                    "kind": t.kind,
                    "due": t.due,
                }
                for t in self.coordinator.due_tasks()
                if t.animal_id in data
            ]
        }


class ProblemAnimalsSensor(HubEntity, SensorEntity):
    """Aantal dieren met een probleem (klimaat, voederen, sensor, ...)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "animals_with_problems")

    @property
    def native_value(self) -> int:
        return sum(1 for s in (self.coordinator.data or {}).values() if s.problems)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "animals": {
                s.animal.name: s.problems
                for s in (self.coordinator.data or {}).values()
                if s.problems
            }
        }


class LowStockSensor(HubEntity, SensorEntity):
    """Aantal voedseldier-voorraden onder hun minimum."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "low_stock")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.low_stock())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "items": [
                {"name": s["name"], "quantity": s["quantity"], "min": s["min_quantity"], "unit": s.get("unit")}
                for s in self.coordinator.low_stock()
            ]
        }


class ClimateControlSensor(ArthropodaEntity, SensorEntity):
    """Wat de klimaatregeling nu doet en waarom (diagnostisch)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["active", "paused", "monitoring", "maintenance"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, animal_id: str, controller) -> None:
        super().__init__(coordinator, animal_id, "climate_control_status")
        self._controller = controller

    @property
    def native_value(self) -> str:
        if self._controller.maintenance_active(self.animal_id):
            return "maintenance"
        return _climate_status(self.snapshot)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        actuators = [
            result.as_dict()
            for result in self._controller.results.values()
            if self.animal_id in result.members
        ]
        until = self._controller.maintenance_until(self.animal_id)
        return {
            "is_day": self.snapshot.is_day,
            "day_start": self.snapshot.day_start,
            "day_end": self.snapshot.day_end,
            "maintenance_until": until,
            "actuators": actuators,
        }


class AnimalSensor(ArthropodaEntity, SensorEntity):
    """Sensor van een dier."""

    entity_description: AnimalSensorDescription

    def __init__(self, coordinator, animal_id: str, description: AnimalSensorDescription) -> None:
        super().__init__(coordinator, animal_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | str | datetime | None:
        return self.entity_description.value_fn(self.snapshot)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.snapshot)
