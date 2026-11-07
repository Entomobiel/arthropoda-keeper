"""Alarmen: meldingen bij klimaatproblemen, met vertraging en hersteld-bericht.

- Een probleem moet `alarm_delay_minutes` aanhouden voor er gemeld wordt
  (deur open bij het voederen geeft zo geen vals alarm).
- Kritieke problemen (gevaarlijk warm) worden meteen gemeld.
- Er komt altijd een melding in HA zelf (persistent notification); daarnaast
  optioneel naar de gekozen notify-diensten of -entiteiten (bv. je gsm).
- Als alles weer in orde is, verdwijnt de HA-melding en volgt een
  "opgelost"-bericht.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import (
    ALARM_PROBLEMS,
    CONF_ALARM_DELAY_MINUTES,
    CONF_NOTIFY_TARGETS,
    CRITICAL_PROBLEMS,
    DEFAULT_ALARM_DELAY_MINUTES,
    DOMAIN,
)
from .coordinator import AnimalSnapshot, ArthropodaCoordinator

_LOGGER = logging.getLogger(__name__)

TEXTS = {
    "nl": {
        "title": "Arthropoda: {name}",
        "resolved_title": "Arthropoda: {name} opgelost",
        "resolved": "Alle klimaatwaarden zijn weer in orde.",
        "temperature_critical": "GEVAARLIJK WARM: {temp} °C (verwarming uitgeschakeld)",
        "temperature_low": "Te koud: {temp} °C (doel {t_lo}–{t_hi} °C)",
        "temperature_high": "Te warm: {temp} °C (doel {t_lo}–{t_hi} °C)",
        "humidity_low": "Te droog: {hum} % (doel {h_lo}–{h_hi} %)",
        "humidity_high": "Te vochtig: {hum} % (doel {h_lo}–{h_hi} %)",
        "water_temperature_low": "Water te koud: {water} °C",
        "water_temperature_high": "Water te warm: {water} °C",
        "sensor_unavailable": "Sensor geeft geen waarden: {sensors}",
    },
    "en": {
        "title": "Arthropoda: {name}",
        "resolved_title": "Arthropoda: {name} resolved",
        "resolved": "All climate values are back in range.",
        "temperature_critical": "DANGEROUSLY HOT: {temp} °C (heating switched off)",
        "temperature_low": "Too cold: {temp} °C (target {t_lo}–{t_hi} °C)",
        "temperature_high": "Too warm: {temp} °C (target {t_lo}–{t_hi} °C)",
        "humidity_low": "Too dry: {hum} % (target {h_lo}–{h_hi} %)",
        "humidity_high": "Too humid: {hum} % (target {h_lo}–{h_hi} %)",
        "water_temperature_low": "Water too cold: {water} °C",
        "water_temperature_high": "Water too warm: {water} °C",
        "sensor_unavailable": "Sensor not reporting: {sensors}",
    },
}


def _fmt(value: float | None) -> str:
    return "?" if value is None else f"{value:g}"


def build_message(snap: AnimalSnapshot, problems: list[str], language: str) -> str:
    """Leesbaar bericht met de actuele waarden."""
    texts = TEXTS.get(language[:2], TEXTS["en"])
    temps = snap.readings.temperatures
    t_target = snap.target_temperature or [None, None]
    h_target = snap.values.get("humidity") or [None, None]
    too_warm = any(p in ("temperature_high", "temperature_critical") for p in problems)
    temp = (max(temps) if too_warm else min(temps)) if temps else None
    values = {
        "temp": _fmt(temp),
        "t_lo": _fmt(t_target[0]),
        "t_hi": _fmt(t_target[1]),
        "hum": _fmt(snap.readings.humidity),
        "h_lo": _fmt(h_target[0]),
        "h_hi": _fmt(h_target[1]),
        "water": _fmt(snap.readings.water_temperature),
        "sensors": ", ".join(snap.readings.unavailable),
    }
    return "\n".join(texts[p].format(**values) for p in problems if p in texts)


class AlarmManager:
    """Houdt per dier bij welke problemen al hoelang bestaan en meldt ze."""

    def __init__(self, hass: HomeAssistant, coordinator: ArthropodaCoordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._since: dict[tuple[str, str], datetime] = {}
        self._notified: dict[str, set[str]] = {}
        self._unsub: Callable[[], None] | None = None

    @callback
    def async_start(self) -> None:
        self._unsub = self.coordinator.async_add_listener(self._on_update)

    @callback
    def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @property
    def _delay(self) -> timedelta:
        minutes = self.coordinator.config_entry.options.get(
            CONF_ALARM_DELAY_MINUTES, DEFAULT_ALARM_DELAY_MINUTES
        )
        return timedelta(minutes=minutes)

    @callback
    def _on_update(self) -> None:
        now = dt_util.utcnow()
        for animal_id, snap in (self.coordinator.data or {}).items():
            current = {p for p in snap.problems if p in ALARM_PROBLEMS} if snap.monitored else set()
            # Begintijd bijhouden / opruimen
            for problem in current:
                self._since.setdefault((animal_id, problem), now)
            for key in [k for k in self._since if k[0] == animal_id and k[1] not in current]:
                del self._since[key]

            due = {
                p for p in current
                if p in CRITICAL_PROBLEMS or now - self._since[(animal_id, p)] >= self._delay
            }
            notified = self._notified.get(animal_id, set())
            if due - notified:
                self._notified[animal_id] = notified | due
                ordered = [p for p in snap.problems if p in self._notified[animal_id]]
                self.hass.async_create_task(self._send(snap, ordered, resolved=False))
            elif notified and not current:
                self._notified.pop(animal_id)
                self.hass.async_create_task(self._send(snap, [], resolved=True))

    async def _send(self, snap: AnimalSnapshot, problems: list[str], resolved: bool) -> None:
        language = self.hass.config.language or "en"
        texts = TEXTS.get(language[:2], TEXTS["en"])
        name = snap.animal.name
        notification_id = f"{DOMAIN}_{snap.animal.id}"
        if resolved:
            persistent_notification.async_dismiss(self.hass, notification_id)
            title = texts["resolved_title"].format(name=name)
            message = texts["resolved"]
        else:
            title = texts["title"].format(name=name)
            message = build_message(snap, problems, language)
            persistent_notification.async_create(self.hass, message, title, notification_id)

        for target in self.coordinator.config_entry.options.get(CONF_NOTIFY_TARGETS, []):
            await async_notify(self.hass, target, title, message)


async def async_notify(hass: HomeAssistant, target: str, title: str, message: str) -> None:
    """Melding sturen; ondersteunt notify-entiteiten én (oudere) notify-diensten."""
    target = target.strip()
    try:
        if hass.states.get(target) is not None:
            await hass.services.async_call(
                "notify", "send_message",
                {"entity_id": target, "title": title, "message": message}, blocking=True,
            )
        else:
            service = target.removeprefix("notify.")
            await hass.services.async_call(
                "notify", service, {"title": title, "message": message}, blocking=True
            )
    except (HomeAssistantError, ValueError) as err:
        _LOGGER.warning("Melding naar %s mislukt: %s", target, err)
