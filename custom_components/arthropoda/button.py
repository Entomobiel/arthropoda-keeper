"""Snelknoppen: met één klik een dagboekregel toevoegen."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from .entity import ArthropodaEntity, add_animal_entities

# sleutel -> dagboektype
QUICK_ACTIONS = {
    "log_feeding": "feeding",
    "log_misting": "misting_manual",
    "log_spot_clean": "spot_clean",
    "log_water_refill": "water_refill",
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    add_animal_entities(
        entry,
        async_add_entities,
        lambda coordinator, animal_id, snap: [
            QuickLogButton(coordinator, animal_id, key, entry_type)
            for key, entry_type in QUICK_ACTIONS.items()
        ],
    )


class QuickLogButton(ArthropodaEntity, ButtonEntity):
    """Knop die een dagboekregel met standaardwaarden toevoegt."""

    def __init__(self, coordinator, animal_id: str, key: str, entry_type: str) -> None:
        super().__init__(coordinator, animal_id, key)
        self._entry_type = entry_type

    async def async_press(self) -> None:
        await self.coordinator.async_log(
            [self.animal_id], self._entry_type, data={"source": "button"}
        )
