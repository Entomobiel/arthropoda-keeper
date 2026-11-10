"""NFC-tags op kasten.

Werking (met de Home Assistant Companion-app):
1. Schrijf een tag met de app (Instellingen → Companion-app → NFC-tags).
2. Koppel hem in het paneel aan een kast (knop 'Tag koppelen' en de tag scannen).
3. Scan je de tag met Android, dan opent de app meteen het werkscherm van de kast
   (notify-commando `command_webview`); op iOS krijg je een melding om op te tikken. Er vuurt ook de gebeurtenis `arthropoda_enclosure_scanned`,
   zodat je er eigen automatiseringen aan kunt hangen.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.util import slugify

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

EVENT_TAG_SCANNED = "tag_scanned"
EVENT_ENCLOSURE_SCANNED = f"{DOMAIN}_enclosure_scanned"


def work_screen_path(code: str) -> str:
    return f"/arthropoda?enclosure={code}"


def deep_link(code: str) -> str:
    """Link die rechtstreeks de HA-app op het werkscherm opent (QR-code, NFC Tools)."""
    return f"homeassistant://navigate{work_screen_path(code)}"


def _notify_service(hass: HomeAssistant, device_id: str | None) -> tuple[str | None, bool]:
    """notify-dienst van de Companion-app die de tag scande, en of het een Android-toestel is."""
    if not device_id:
        return None, False
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None, False
    entry_id = getattr(device, "config_entry_id", None)
    entry = hass.config_entries.async_get_entry(entry_id) if entry_id else None
    android = (
        entry is not None
        and entry.domain == "mobile_app"
        and str(entry.data.get("os_name", "")).lower() == "android"
    )
    for name in (device.name_by_user, device.name):
        if name:
            service = f"mobile_app_{slugify(name)}"
            if hass.services.has_service("notify", service):
                return service, android
    return None, android


@callback
def async_setup_nfc(hass: HomeAssistant, coordinator) -> callable:
    """Luister naar gescande tags; geeft de afmeldfunctie terug."""

    async def _handle(event: Event) -> None:
        tag_id = event.data.get("tag_id")
        if not tag_id:
            return
        enclosure = next(
            (e for e in coordinator.enclosures.values() if e.get("nfc_tag") == tag_id), None
        )
        if enclosure is None:
            return
        code = enclosure["code"]
        device_id = event.data.get("device_id")
        if coordinator.nag is not None:
            coordinator.nag.note_scan(enclosure["id"])  # bewijs: je stond bij de kast
        hass.bus.async_fire(
            EVENT_ENCLOSURE_SCANNED,
            {"enclosure_id": enclosure["id"], "code": code, "device_id": device_id},
        )
        service, android = _notify_service(hass, device_id)
        if service is None:
            return
        path = work_screen_path(code)
        if android:
            # Android: de app opent zichzelf meteen op het werkscherm, zonder te tikken.
            # 'via=nfc': het scanbewijs is hierboven al genoteerd.
            command = {"message": "command_webview", "data": {"command": f"{path}&via=nfc"}}
            try:
                await hass.services.async_call("notify", service, command, blocking=False)
            except HomeAssistantError as err:
                _LOGGER.warning("Werkscherm openen voor kast %s mislukt: %s", code, err)
            return
        residents = [
            coordinator.data[a].animal.name for a in coordinator.residents(enclosure["id"])
            if a in (coordinator.data or {})
        ]
        message: dict[str, Any] = {
            "title": f"{code}{' – ' + enclosure['name'] if enclosure.get('name') else ''}",
            "message": ", ".join(residents) or "Tik om het werkscherm te openen",
            # iOS gebruikt 'url', Android 'clickAction'; 'tag' vervangt een vorige melding.
            "data": {"url": path, "clickAction": path, "tag": f"arthropoda_{code}"},
        }
        try:
            await hass.services.async_call("notify", service, message, blocking=False)
        except HomeAssistantError as err:
            _LOGGER.warning("Melding voor kast %s mislukt: %s", code, err)

    return hass.bus.async_listen(EVENT_TAG_SCANNED, _handle)
