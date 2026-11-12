"""Dagelijkse samenvatting: welke taken vandaag (of eerder) moeten gebeuren.

Eén bericht per dag op een vast uur in plaats van losse herinneringen. Gaat
naar de ingestelde notify-doelen; zonder doelen verschijnt het als melding in
HA zelf. Geen taken en geen problemen = geen bericht.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .alarms import async_notify
from .const import (
    CONF_DIGEST_ENABLED,
    CONF_DIGEST_TIME,
    CONF_NOTIFY_TARGETS,
    DEFAULT_DIGEST_TIME,
    DOMAIN,
)
from .coordinator import ArthropodaCoordinator
from .tasks import texts


def build_digest(coordinator: ArthropodaCoordinator, language: str) -> str | None:
    """Tekst van de samenvatting, of None als er niets te melden is."""
    t = texts(language)
    data = coordinator.data or {}
    today = dt_util.now().date()
    lines = []
    for task in coordinator.due_tasks():
        if task.enclosure_id is None and task.animal_id not in data:
            continue
        days = (today - dt_util.as_local(task.due).date()).days
        when = t["overdue"].format(days=days) if days > 0 else t["due_today"]
        lines.append(f"• {t[task.kind]}: {coordinator.task_target_name(task)} ({when.lower()})")
    problems = [snap.animal.name for snap in data.values() if snap.problems]
    attention = [snap.animal.name for snap in data.values()
                 if any(i["level"] == "warn" for i in snap.insights)]
    if attention:
        lines.append(f"\n{t['digest_attention']}: {', '.join(attention)}")
    if problems:
        lines.append(f"\n{t['digest_problems']}: {', '.join(problems)}")
    low = coordinator.low_stock()
    if low:
        lines.append(f"\n{t['digest_stock']}: " + ", ".join(
            f"{s['name']} ({s['quantity']:g}{' ' + s['unit'] if s.get('unit') else ''})" for s in low))
    broods = coordinator.broods_due()
    if broods:
        names = [data[b["mother_id"]].animal.name for b in broods if b["mother_id"] in data]
        lines.append(f"\n{t['digest_broods']}: {', '.join(names)}")
    docs = coordinator.expiring_documents()
    if docs:
        lines.append(f"\n{t['digest_documents']}: " + ", ".join(
            f"{doc['title']} ({doc['expires_at']})" for doc in docs))
    return "\n".join(lines) if lines else None


class DigestManager:
    """Stuurt elke dag op het ingestelde uur de samenvatting."""

    def __init__(self, hass: HomeAssistant, coordinator: ArthropodaCoordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._unsub: Callable[[], None] | None = None

    @callback
    def async_start(self) -> None:
        opts = self.coordinator.config_entry.options
        if not opts.get(CONF_DIGEST_ENABLED, True):
            return
        moment = dt_util.parse_time(opts.get(CONF_DIGEST_TIME) or DEFAULT_DIGEST_TIME)
        if moment is None:
            return
        self._unsub = async_track_time_change(
            self.hass, self._fire, hour=moment.hour, minute=moment.minute, second=0
        )

    @callback
    def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _fire(self, _now: datetime) -> None:
        self.hass.async_create_task(self.async_send())

    async def async_send(self) -> bool:
        """Samenvatting nu versturen. Geeft False als er niets te melden was."""
        language = self.hass.config.language or "en"
        message = build_digest(self.coordinator, language)
        if message is None:
            return False
        title = texts(language)["digest_title"]
        targets = self.coordinator.config_entry.options.get(CONF_NOTIFY_TARGETS, [])
        if targets:
            for target in targets:
                await async_notify(self.hass, target, title, message)
        else:
            persistent_notification.async_create(
                self.hass, message, title, f"{DOMAIN}_digest"
            )
        return True
