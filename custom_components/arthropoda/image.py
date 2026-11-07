"""Foto per dier: de eigen profielfoto, of anders de soortfoto (iNaturalist).

De afbeelding wordt via HA's beveiligde afbeeldingslink getoond
(attribuut entity_picture), dus ook in gewone HA-kaarten bruikbaar.
"""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
from typing import Any

import aiohttp

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .ai_import import USER_AGENT
from .entity import ArthropodaEntity, add_animal_entities
from .http_views import photo_dir

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    add_animal_entities(
        entry,
        async_add_entities,
        lambda coordinator, animal_id, snap: [AnimalPhoto(coordinator, animal_id)],
    )


class AnimalPhoto(ArthropodaEntity, ImageEntity):
    """Profielfoto (eigen upload) of soortfoto."""

    _attr_content_type = "image/jpeg"

    def __init__(self, coordinator, animal_id: str) -> None:
        ArthropodaEntity.__init__(self, coordinator, animal_id, "photo")
        ImageEntity.__init__(self, coordinator.hass)
        self._cache: tuple[str, bytes] | None = None

    # Welke foto geldt nu? (sleutel, bron)
    def _current(self) -> tuple[str, dict[str, Any]] | None:
        snap = self.coordinator.data.get(self.animal_id)
        if snap is None:
            return None
        own = snap.animal.info.get("photo")
        if own and own.get("file"):
            return f"own:{own['file']}:{own.get('updated')}", own
        species = snap.bundle.species
        sp_photo = species.info.get("photo") if species else None
        if sp_photo and sp_photo.get("url"):
            return f"species:{sp_photo['url']}", sp_photo
        return None

    @property
    def image_last_updated(self) -> datetime | None:
        current = self._current()
        if current is None:
            return None
        stamp = current[1].get("updated") or current[1].get("set_at")
        return dt_util.parse_datetime(stamp) if stamp else dt_util.utc_from_timestamp(0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        current = self._current()
        if current is None:
            return {"source": None}
        key, info = current
        if key.startswith("own:"):
            return {"source": "own"}
        return {
            "source": "inaturalist",
            "attribution": info.get("attribution"),
            "license": info.get("license"),
            "source_url": info.get("source_url"),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        current = self._current()
        if self._cache and (current is None or current[0] != self._cache[0]):
            self._cache = None
            self.async_update_token()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        current = self._current()
        if current is None:
            return None
        key, info = current
        if self._cache and self._cache[0] == key:
            return self._cache[1]
        if key.startswith("own:"):
            path = photo_dir(self.hass) / info["file"]
            try:
                data = await self.hass.async_add_executor_job(Path(path).read_bytes)
            except OSError:
                return None
        else:
            try:
                session = async_get_clientsession(self.hass)
                async with session.get(
                    info["url"], headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.read()
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.debug("Soortfoto ophalen mislukt: %s", err)
                return None
        self._cache = (key, data)
        return data
