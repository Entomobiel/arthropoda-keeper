"""Schakelaars per dier: klimaatsturing aan/uit en onderhoudsmodus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .entity import ArthropodaEntity, add_animal_entities


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    controller = entry.runtime_data.controller
    add_animal_entities(
        entry,
        async_add_entities,
        lambda coordinator, animal_id, snap: (
            [
                ClimateControlSwitch(coordinator, animal_id),
                MaintenanceSwitch(coordinator, animal_id, controller),
            ]
            if snap.has_actuators
            else []
        ),
    )


class ClimateControlSwitch(ArthropodaEntity, SwitchEntity):
    """Uit = de integratie raakt de actuatoren voor dit dier niet aan (alleen bewaken)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, animal_id: str) -> None:
        super().__init__(coordinator, animal_id, "climate_control")

    @property
    def is_on(self) -> bool:
        return self.snapshot.climate_enabled

    async def _set(self, value: bool) -> None:
        info = {**self.snapshot.animal.info, "climate_control": value}
        await self.coordinator.async_update_animal(self.animal_id, info=info)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)


class MaintenanceSwitch(ArthropodaEntity, SwitchEntity):
    """Onderhoudsmodus: verneveling, ventilatie en pompen tijdelijk uit (max. 60 min)."""

    def __init__(self, coordinator, animal_id: str, controller) -> None:
        super().__init__(coordinator, animal_id, "maintenance")
        self._controller = controller

    @property
    def is_on(self) -> bool:
        return self._controller.maintenance_active(self.animal_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"until": self._controller.maintenance_until(self.animal_id)}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._controller.async_set_maintenance(self.animal_id, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._controller.async_set_maintenance(self.animal_id, False)
        self.async_write_ha_state()
