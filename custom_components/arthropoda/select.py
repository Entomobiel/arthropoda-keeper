"""Keuzelijsten per dier: seizoensprofiel en levensfase."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .const import SEASON_MODES, STAGES
from .entity import ArthropodaEntity, add_animal_entities


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    add_animal_entities(
        entry,
        async_add_entities,
        lambda coordinator, animal_id, snap: [
            SeasonModeSelect(coordinator, animal_id),
            StageSelect(coordinator, animal_id),
        ],
    )


class SeasonModeSelect(ArthropodaEntity, SelectEntity):
    """Automatisch seizoen volgen, of een seizoensprofiel forceren."""

    _attr_options = SEASON_MODES
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, animal_id: str) -> None:
        super().__init__(coordinator, animal_id, "season_mode")

    @property
    def current_option(self) -> str | None:
        return self.snapshot.animal.season_mode

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_update_animal(self.animal_id, season_mode=option)


class StageSelect(ArthropodaEntity, SelectEntity):
    """Levensfase wijzigen (wordt in het dagboek genoteerd)."""

    _attr_options = STAGES
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, animal_id: str) -> None:
        super().__init__(coordinator, animal_id, "stage_select")

    @property
    def current_option(self) -> str | None:
        return self.snapshot.animal.stage

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_log([self.animal_id], "stage_change", data={"stage": option})
