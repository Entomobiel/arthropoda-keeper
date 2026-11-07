"""Binaire sensoren per dier: probleem, premolt, voederen achterstallig, klimaat."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant

from .const import CLIMATE_PROBLEMS
from .coordinator import AnimalSnapshot
from .entity import ArthropodaEntity, add_animal_entities


@dataclass(frozen=True, kw_only=True)
class AnimalBinaryDescription(BinarySensorEntityDescription):
    """Beschrijving van een binaire diersensor."""

    is_on_fn: Callable[[AnimalSnapshot], bool]
    exists_fn: Callable[[AnimalSnapshot], bool] = lambda s: True


BINARY_SENSORS: tuple[AnimalBinaryDescription, ...] = (
    AnimalBinaryDescription(
        key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda s: bool(s.problems),
    ),
    AnimalBinaryDescription(
        key="climate_out_of_range",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda s: any(p in CLIMATE_PROBLEMS for p in s.problems),
    ),
    AnimalBinaryDescription(
        key="feeding_overdue",
        is_on_fn=lambda s: "feeding_overdue" in s.problems,
    ),
    AnimalBinaryDescription(
        key="premolt",
        is_on_fn=lambda s: s.animal.premolt,
        exists_fn=lambda s: s.can_molt,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    add_animal_entities(
        entry,
        async_add_entities,
        lambda coordinator, animal_id, snap: [
            AnimalBinarySensor(coordinator, animal_id, desc)
            for desc in BINARY_SENSORS
            if desc.exists_fn(snap)
        ],
    )


class AnimalBinarySensor(ArthropodaEntity, BinarySensorEntity):
    """Binaire sensor van een dier."""

    entity_description: AnimalBinaryDescription

    def __init__(self, coordinator, animal_id: str, description: AnimalBinaryDescription) -> None:
        super().__init__(coordinator, animal_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.is_on_fn(self.snapshot)
