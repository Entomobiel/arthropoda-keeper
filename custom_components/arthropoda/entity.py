"""Basisentiteit: één HA-apparaat per dier of kolonie."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, SUBENTRY_ANIMAL
from .coordinator import AnimalSnapshot, ArthropodaCoordinator

CONFIG_URL = f"homeassistant://config/integrations/integration/{DOMAIN}"


class ArthropodaEntity(CoordinatorEntity[ArthropodaCoordinator]):
    """Entiteit die bij een dier hoort."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ArthropodaCoordinator, animal_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.animal_id = animal_id
        self._attr_unique_id = f"{animal_id}_{key}"
        self._attr_translation_key = key
        snap = coordinator.data.get(animal_id)
        species = snap.bundle.species if snap else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, animal_id)},
            name=snap.animal.name if snap else None,
            manufacturer=NAME,
            model=species.scientific_name if species else None,
            # Link "Instellingen" op de apparaatpagina → pagina met het tandwiel
            configuration_url=CONFIG_URL,
        )

    @property
    def snapshot(self) -> AnimalSnapshot:
        return self.coordinator.data[self.animal_id]

    @property
    def available(self) -> bool:
        return super().available and self.animal_id in self.coordinator.data


class HubEntity(CoordinatorEntity[ArthropodaCoordinator]):
    """Entiteit van de collectie als geheel (takenlijst, kalender, totalen)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ArthropodaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=NAME,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=CONFIG_URL,
        )


def add_animal_entities(
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[ArthropodaCoordinator, str, AnimalSnapshot], Iterable[Entity]],
) -> None:
    """Maak entiteiten aan per dier, gekoppeld aan de juiste subentry."""
    coordinator: ArthropodaCoordinator = entry.runtime_data.coordinator
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_ANIMAL:
            continue
        snap = coordinator.data.get(subentry_id)
        if snap is None:
            continue
        async_add_entities(
            list(factory(coordinator, subentry_id, snap)), config_subentry_id=subentry_id
        )
