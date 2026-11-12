"""Automatisch sproeien: pompje per plant, gestuurd op het bodemvocht uit Plant Monitor.

Per plant in een kast (config["plant_care"][plant]):
- "pump": schakelaar van het pompje (switch/input_boolean/valve/script),
- "pump_seconds": hoe lang het pompje per beurt loopt,
- "pump_max_per_day": hoeveel beurten per dag maximaal,
- "pump_pause_minutes": minimale tijd tussen twee beurten (zodat het water kan intrekken).

Zakt het bodemvocht onder het minimum van de plant, dan krijgt het pompje één beurt
(binnen de grenzen). Elke beurt komt als 'water gegeven' in het plantendagboek.
Veiligheid: nooit zonder geldige meting, niet in onderhoud, het pompje wordt
altijd weer uitgeschakeld (ook na een herstart), en maximaal X beurten per dag.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.util import dt as dt_util

from .plants import CARE_PUMP, CONF_PLANT_CARE, CONF_PLANTS, plant_reading, plant_thresholds

_LOGGER = logging.getLogger(__name__)

CHECK_EVERY = timedelta(minutes=2)
DATA_RUNS = "arthropoda_watering_runs"  # overleeft het herladen van de integratie


class WateringManager:
    """Laat pompjes lopen als de grond te droog is."""

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        # {plant: [tijdstippen van pompbeurten]}
        self.runs: dict[str, list[datetime]] = hass.data.setdefault(DATA_RUNS, {})
        self._unsubs: list = []
        self._running: set[str] = set()

    # --- configuratie -----------------------------------------------------

    def pumps(self) -> list[tuple[dict[str, Any], str, dict[str, Any]]]:
        """(kast, plant, instellingen) voor elke plant met een pompje."""
        result = []
        for enc in self.coordinator.enclosures.values():
            cfg = enc.get("config") or {}
            care = cfg.get(CONF_PLANT_CARE) or {}
            for plant in cfg.get(CONF_PLANTS) or []:
                settings = care.get(plant) or {}
                if settings.get(CARE_PUMP):
                    result.append((enc, plant, settings))
        return result

    # --- levenscyclus -----------------------------------------------------

    @callback
    def async_start(self) -> None:
        self._unsubs.append(async_track_time_interval(self.hass, self._tick, CHECK_EVERY))
        self._unsubs.append(self.coordinator.async_add_listener(self._on_update))
        self.hass.async_create_task(self._ensure_off())

    @callback
    def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    async def _ensure_off(self) -> None:
        """Na een (her)start: geen pompje mag blijven lopen."""
        for _enc, _plant, settings in self.pumps():
            pump = settings[CARE_PUMP]
            state = self.hass.states.get(pump)
            if state is not None and state.state == "on" and not pump.startswith("script."):
                await self._switch(pump, False)

    @callback
    def _tick(self, _now: datetime) -> None:
        self.hass.async_create_task(self.async_check())

    @callback
    def _on_update(self) -> None:
        self.hass.async_create_task(self.async_check())

    # --- beslissen --------------------------------------------------------

    def runs_today(self, plant: str, now: datetime) -> list[datetime]:
        start = dt_util.start_of_local_day(now)
        return [t for t in self.runs.get(plant, []) if t >= start]

    def should_run(self, enc: dict[str, Any], plant: str, settings: dict[str, Any], now: datetime) -> str | None:
        """Reden om nu te pompen, of None."""
        if enc.get("status") == "maintenance" or plant in self._running:
            return None
        moisture = plant_reading(self.hass, plant, "moisture")
        low = (plant_thresholds(self.hass, plant).get("moisture") or [None])[0]
        if moisture is None or low is None or moisture >= low:
            return None
        today = self.runs_today(plant, now)
        if len(today) >= int(settings.get("pump_max_per_day") or 3):
            return None
        last = max(self.runs.get(plant, []), default=None)
        if last is not None and now - last < timedelta(minutes=float(settings.get("pump_pause_minutes") or 60)):
            return None
        return f"{moisture:g} < {low:g}"

    async def async_check(self) -> None:
        now = dt_util.utcnow()
        for enc, plant, settings in self.pumps():
            reason = self.should_run(enc, plant, settings, now)
            if reason is not None:
                await self.async_run(enc, plant, settings, reason)

    # --- uitvoeren --------------------------------------------------------

    async def async_run(self, enc: dict[str, Any], plant: str, settings: dict[str, Any], reason: str) -> None:
        pump = settings[CARE_PUMP]
        seconds = float(settings.get("pump_seconds") or 5)
        now = dt_util.utcnow()
        self.runs.setdefault(plant, []).append(now)
        # Alleen de laatste 2 dagen bijhouden.
        self.runs[plant] = [t for t in self.runs[plant] if now - t < timedelta(days=2)]
        self._running.add(plant)
        _LOGGER.info("Pompje %s voor %s: %s s (%s)", pump, plant, seconds, reason)
        try:
            await self._switch(pump, True)
        except HomeAssistantError as err:
            self._running.discard(plant)
            _LOGGER.warning("Pompje %s starten mislukt: %s", pump, err)
            return

        @callback
        def _off(_now: datetime) -> None:
            self.hass.async_create_task(self._finish(pump, plant))

        if pump.startswith("script."):
            self._running.discard(plant)  # een script stopt zelf
        else:
            self._unsubs.append(async_call_later(self.hass, seconds, _off))
        await self.coordinator.async_log_plants(
            [plant], "watered", enclosure_id=enc["id"],
            data={"source": "pump", "auto": True, "seconds": seconds, "reason": reason},
        )

    async def _finish(self, pump: str, plant: str) -> None:
        try:
            await self._switch(pump, False)
        finally:
            self._running.discard(plant)

    async def _switch(self, entity_id: str, on: bool) -> None:
        domain = entity_id.split(".", 1)[0]
        if domain == "script":
            if on:
                await self.hass.services.async_call("script", "turn_on", {"entity_id": entity_id}, blocking=True)
            return
        if domain == "valve":
            service = "open_valve" if on else "close_valve"
        else:
            service = "turn_on" if on else "turn_off"
        await self.hass.services.async_call(domain, service, {"entity_id": entity_id}, blocking=True)
