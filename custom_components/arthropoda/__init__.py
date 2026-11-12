"""Arthropoda Keeper: insecten en andere geleedpotigen houden in Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .alarms import AlarmManager
from .climate_controller import ClimateController
from .const import DATA_DIR, DB_FILE, DOMAIN, NAME, SIGNAL_UPDATE
from .coordinator import ArthropodaCoordinator
from .db import Database
from .digest import DigestManager
from .frontend import async_register_frontend, async_unregister_panel
from .http_views import async_register_views
from .nag import NagManager
from .watering import WateringManager
from .nfc import async_setup_nfc
from .services import async_setup_services
from .websocket_api import async_register_websocket

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.IMAGE,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TODO,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass(slots=True)
class ArthropodaRuntime:
    """Gedeelde objecten van de geladen integratie."""

    db: Database
    coordinator: ArthropodaCoordinator
    controller: ClimateController
    alarms: AlarmManager
    digest: DigestManager
    nag: NagManager
    watering: WateringManager | None = None


type ArthropodaConfigEntry = ConfigEntry[ArthropodaRuntime]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Registreer de acties en de WebSocket-API (één keer, los van de config entry)."""
    async_setup_services(hass)
    async_register_websocket(hass)
    async_register_views(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ArthropodaConfigEntry) -> bool:
    """Open de database en zet de dieren klaar."""
    db = Database(hass.config.path(DATA_DIR, DB_FILE))
    await hass.async_add_executor_job(db.open)

    coordinator = ArthropodaCoordinator(hass, entry, db)
    try:
        await hass.async_add_executor_job(db.sync_animals, coordinator.animal_configs)
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await hass.async_add_executor_job(db.close)
        raise

    controller = ClimateController(hass, coordinator)
    alarms = AlarmManager(hass, coordinator)
    digest = DigestManager(hass, coordinator)
    nag = NagManager(hass, coordinator)
    await nag.async_load()
    coordinator.nag = nag
    entry.runtime_data = ArthropodaRuntime(
        db=db, coordinator=coordinator, controller=controller, alarms=alarms, digest=digest,
        nag=nag, watering=WateringManager(hass, coordinator),
    )
    coordinator.async_start_tracking()
    entry.async_on_unload(coordinator.async_stop_tracking)

    # Apparaat voor de collectie (takenlijst, kalender); de dieren hangen eronder.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=NAME,
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Paneel en kaarten op de hoogte houden van elke wijziging.
    entry.async_on_unload(
        coordinator.async_add_listener(lambda: async_dispatcher_send(hass, SIGNAL_UPDATE))
    )
    await async_register_frontend(hass, entry.title)
    entry.async_on_unload(async_setup_nfc(hass, coordinator))
    async_dispatcher_send(hass, SIGNAL_UPDATE)

    alarms.async_start()
    entry.async_on_unload(alarms.async_stop)
    digest.async_start()
    entry.async_on_unload(digest.async_stop)
    nag.async_start()
    entry.async_on_unload(nag.async_stop)
    entry.runtime_data.watering.async_start()
    entry.async_on_unload(entry.runtime_data.watering.async_stop)
    controller.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ArthropodaConfigEntry) -> None:
    """Herlaad bij gewijzigde opties of toegevoegde/verwijderde dieren."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ArthropodaConfigEntry) -> bool:
    """Stop de regelaar, ontlaad de platformen en sluit de database."""
    await entry.runtime_data.controller.async_stop()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await hass.async_add_executor_job(entry.runtime_data.db.close)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ArthropodaConfigEntry) -> None:
    """Collectie verwijderd: paneel uit de zijbalk halen (de database blijft bewaard)."""
    async_unregister_panel(hass)
