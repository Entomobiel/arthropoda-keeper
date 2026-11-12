"""Aandringen bij taken die over tijd zijn, met scanbewijs.

Escalatieladder (alles instelbaar in de opties):
- over tijd (vervaldag voorbij): elke `nag_interval_hours` een melding met de
  open taken, buiten de stille uren; knoppen 'Over 1 uur' en 'Morgen'
  (maximaal `nag_max_snoozes` keer per taak). Bewust géén knop 'Gedaan'.
- `nag_urgent_days` te laat: dringende melding (eigen kanaal, hoge prioriteit,
  blijft staan en is niet weg te vegen); uitstellen kan niet meer.
- `nag_loud_days` te laat: daarbovenop een gesproken boodschap op een speaker
  en/of een knipperende lamp.
Zijn alle taken gedaan, dan wordt de melding van de gsm gehaald.

Scanbewijs: een taak die over tijd is, telt pas als afgehandeld als de kast
kort ervoor gescand werd (NFC-tag of QR-code). Alleen voor kasten die dat
kunnen bewijzen: met NFC-tag, of die al eens gescand werden.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NAG_ENABLED,
    CONF_NAG_INTERVAL_HOURS,
    CONF_NAG_LIGHT,
    CONF_NAG_LOUD_DAYS,
    CONF_NAG_MAX_SNOOZES,
    CONF_NAG_MEDIA_PLAYER,
    CONF_NAG_TTS,
    CONF_NAG_URGENT_DAYS,
    CONF_NOTIFY_TARGETS,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_REQUIRE_SCAN,
    CONF_SCAN_MINUTES,
    DOMAIN,
    NAG_DEFAULTS,
)
from .journal import COUNTER_TYPES
from .plants import PLANT_CARE_KINDS
from .tasks import TASK_KINDS, Task, texts

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
NOTIFY_TAG = "arthropoda_nag"
ACTION_LATER = "ARTHROPODA_NAG_LATER"
ACTION_TOMORROW = "ARTHROPODA_NAG_TOMORROW"
EVENT_NOTIFICATION_ACTION = "mobile_app_notification_action"
CHECK_EVERY = timedelta(minutes=5)

NAG_TEXTS = {
    "nl": {
        "title": "Arthropoda: taken over tijd",
        "title_urgent": "⚠ Arthropoda: dringend!",
        "later": "Over 1 uur",
        "tomorrow": "Morgen",
        "channel": "Arthropoda herinneringen",
        "channel_urgent": "Arthropoda dringend",
        "speech": "Let op. Er zijn {n} verzorgingstaken al {days} dagen te laat. {list}.",
        "scan_required": "Deze taak is over tijd. Scan eerst de NFC-tag of QR-code van kast {code} en geef de handeling dan in.",
    },
    "en": {
        "title": "Arthropoda: overdue tasks",
        "title_urgent": "⚠ Arthropoda: urgent!",
        "later": "In 1 hour",
        "tomorrow": "Tomorrow",
        "channel": "Arthropoda reminders",
        "channel_urgent": "Arthropoda urgent",
        "speech": "Attention. {n} care tasks are {days} days overdue. {list}.",
        "scan_required": "This task is overdue. First scan the NFC tag or QR code of enclosure {code}, then log the action.",
    },
}


def nag_texts(language: str) -> dict[str, str]:
    return NAG_TEXTS.get((language or "en")[:2], NAG_TEXTS["en"])


class ScanRequired(HomeAssistantError, ValueError):
    """Taak over tijd: eerst de kast scannen."""


def resolving_types(kind: str) -> tuple[str, ...]:
    """Dagboektypes die een taak van deze soort afhandelen."""
    if kind not in TASK_KINDS:
        return ()
    counter = TASK_KINDS[kind][1]
    return COUNTER_TYPES.get(counter) or (TASK_KINDS[kind][2],)


def days_overdue(task: Task, now: datetime) -> int:
    """Hele kalenderdagen sinds de vervaldag (0 = vandaag of later)."""
    return (dt_util.as_local(now).date() - dt_util.as_local(task.due).date()).days


def in_quiet_hours(now: datetime, start: time, end: time) -> bool:
    local = dt_util.as_local(now).time()
    if start == end:
        return False
    if start < end:
        return start <= local < end
    return local >= start or local < end


@dataclass(slots=True)
class NagState:
    """Wat bewaard moet blijven over herstarts heen."""

    snoozes: dict[str, int]          # taak-sleutel -> aantal keer uitgesteld
    silenced_until: dict[str, str]   # taak-sleutel -> ISO-tijdstip
    scans: dict[str, str]            # kast-id -> laatste scan (ISO)
    last_sent: str | None = None
    sent_active: bool = False


class NagManager:
    """Herinneringen die blijven aandringen, en het scanbewijs."""

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.nag")
        self.state = NagState({}, {}, {})
        self._unsubs: list[Callable[[], None]] = []
        self._busy = False

    # --- opties -----------------------------------------------------------

    def opt(self, key: str) -> Any:
        value = self.coordinator.config_entry.options.get(key)
        return NAG_DEFAULTS.get(key) if value in (None, "") else value

    @property
    def enabled(self) -> bool:
        return bool(self.opt(CONF_NAG_ENABLED))

    # --- levenscyclus -----------------------------------------------------

    async def async_load(self) -> None:
        # Bij herladen van de integratie (bv. dier toegevoegd) dezelfde toestand
        # hergebruiken; de Store schrijft met vertraging en is dan nog niet bij.
        cached = self.hass.data.get(f"{DOMAIN}_nag_state")
        if cached is not None:
            self.state = cached
            return
        data = await self._store.async_load() or {}
        self.state = NagState(
            snoozes=data.get("snoozes", {}),
            silenced_until=data.get("silenced_until", {}),
            scans=data.get("scans", {}),
            last_sent=data.get("last_sent"),
            sent_active=data.get("sent_active", False),
        )
        self.hass.data[f"{DOMAIN}_nag_state"] = self.state

    def _save(self) -> None:
        self._store.async_delay_save(
            lambda: {
                "snoozes": self.state.snoozes,
                "silenced_until": self.state.silenced_until,
                "scans": self.state.scans,
                "last_sent": self.state.last_sent,
                "sent_active": self.state.sent_active,
            },
            2,
        )

    @callback
    def async_start(self) -> None:
        self._unsubs.append(
            self.hass.bus.async_listen(EVENT_NOTIFICATION_ACTION, self._on_action)
        )
        if not self.enabled:
            return
        self._unsubs.append(async_track_time_interval(self.hass, self._tick, CHECK_EVERY))
        self._unsubs.append(self.coordinator.async_add_listener(self._on_update))
        self.hass.async_create_task(self.async_check())

    @callback
    def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    @callback
    def _tick(self, _now: datetime) -> None:
        self.hass.async_create_task(self.async_check())

    @callback
    def _on_update(self) -> None:
        # Alles gedaan? Dan meteen de melding weghalen (niet wachten op de tik).
        if self.state.sent_active and not self.overdue_tasks():
            self.hass.async_create_task(self.async_check())

    # --- scanbewijs -------------------------------------------------------

    @callback
    def note_scan(self, enclosure_id: int, when: datetime | None = None) -> None:
        self.state.scans[str(enclosure_id)] = (when or dt_util.utcnow()).isoformat()
        self._save()
        if self.coordinator.data is not None:
            self.coordinator.async_update_listeners()  # paneel/werkscherm: "gescand ✓"

    def scanned_recently(self, enclosure_id: int) -> bool:
        iso = self.state.scans.get(str(enclosure_id))
        when = dt_util.parse_datetime(iso) if iso else None
        minutes = float(self.opt(CONF_SCAN_MINUTES))
        return when is not None and dt_util.utcnow() - when <= timedelta(minutes=minutes)

    def verifiable(self, enclosure_id: int | None) -> bool:
        """Kan deze kast aanwezigheid bewijzen (NFC-tag of al eens gescand)?"""
        if enclosure_id is None:
            return False
        enc = self.coordinator.enclosures.get(enclosure_id)
        return bool(enc) and (bool(enc.get("nfc_tag")) or str(enclosure_id) in self.state.scans)

    def check_log_allowed(self, animal_ids: list[str], entry_type: str) -> None:
        """Weiger een handeling die een taak over tijd afhandelt zonder recente scan."""
        if not self.enabled or not self.opt(CONF_REQUIRE_SCAN):
            return
        now = dt_util.utcnow()
        for task in self.overdue_tasks(now, include_silenced=True):
            if entry_type not in resolving_types(task.kind):
                continue
            if task.enclosure_id is not None:
                enc_id = task.enclosure_id
                hit = any(self.coordinator.residents(enc_id).count(a) for a in animal_ids)
            else:
                hit = task.animal_id in animal_ids
                snap = (self.coordinator.data or {}).get(task.animal_id)
                enc_id = snap.animal.enclosure_id if snap else None
            if hit and self.verifiable(enc_id) and not self.scanned_recently(enc_id):
                code = self.coordinator.enclosures[enc_id]["code"]
                raise ScanRequired(nag_texts(self.hass.config.language)["scan_required"].format(code=code))

    def check_equipment_allowed(self, task: Task) -> None:
        if not self.enabled or not self.opt(CONF_REQUIRE_SCAN):
            return
        if days_overdue(task, dt_util.utcnow()) > 0 and self.verifiable(task.enclosure_id) \
                and not self.scanned_recently(task.enclosure_id):
            code = self.coordinator.enclosures[task.enclosure_id]["code"]
            raise ScanRequired(nag_texts(self.hass.config.language)["scan_required"].format(code=code))

    def check_plants_allowed(self, plants: list[str], entry_type: str) -> None:
        """Sproeien/bemesten over tijd mag pas na een scan van die kast."""
        for task in self.coordinator.enclosure_tasks:
            if task.plant in plants and PLANT_CARE_KINDS.get(task.kind) == entry_type:
                self.check_equipment_allowed(task)

    # --- taken ------------------------------------------------------------

    @staticmethod
    def _key(task: Task) -> str:
        # Nieuwe vervaldag (taak gedaan) = nieuwe sleutel = teller op nul.
        return f"{task.uid}@{task.due.isoformat()}"

    def overdue_tasks(self, now: datetime | None = None, include_silenced: bool = False) -> list[Task]:
        now = now or dt_util.utcnow()
        data = self.coordinator.data or {}
        result = []
        for task in self.coordinator.all_tasks():
            if task.enclosure_id is None and task.animal_id not in data:
                continue
            if days_overdue(task, now) <= 0:
                continue
            if not include_silenced:
                until = dt_util.parse_datetime(self.state.silenced_until.get(self._key(task), "") or "")
                if until is not None and now < until:
                    continue
            result.append(task)
        return result

    # --- versturen --------------------------------------------------------

    def _targets(self) -> list[str]:
        return [t.strip() for t in self.coordinator.config_entry.options.get(CONF_NOTIFY_TARGETS, []) if t.strip()]

    async def async_check(self, force: bool = False) -> None:
        if self._busy or not self.enabled:
            return
        self._busy = True
        try:
            await self._check(force)
        finally:
            self._busy = False

    async def _check(self, force: bool) -> None:
        now = dt_util.utcnow()
        tasks = self.overdue_tasks(now)
        if not tasks:
            if self.state.sent_active:
                await self._clear()
            return
        quiet = in_quiet_hours(
            now,
            dt_util.parse_time(str(self.opt(CONF_QUIET_START))) or time(22),
            dt_util.parse_time(str(self.opt(CONF_QUIET_END))) or time(8),
        )
        if quiet and not force:
            return
        last = dt_util.parse_datetime(self.state.last_sent or "")
        interval = timedelta(hours=float(self.opt(CONF_NAG_INTERVAL_HOURS)))
        if not force and last is not None and now - last < interval - timedelta(minutes=1):
            return
        await self.async_send(tasks, now)

    def level(self, tasks: list[Task], now: datetime) -> int:
        """1 = herinnering, 2 = dringend, 3 = luid."""
        worst = max(days_overdue(t, now) for t in tasks)
        if worst >= int(self.opt(CONF_NAG_LOUD_DAYS)):
            return 3
        if worst >= int(self.opt(CONF_NAG_URGENT_DAYS)):
            return 2
        return 1

    def build(self, tasks: list[Task], now: datetime) -> dict[str, Any]:
        """Titel, tekst en Android-gegevens van de melding."""
        language = self.hass.config.language or "en"
        t, nt = texts(language), nag_texts(language)
        level = self.level(tasks, now)
        tasks = sorted(tasks, key=lambda x: x.due)
        lines = [
            f"• {t.get(task.kind, task.kind)}: {self.coordinator.task_target_name(task)} "
            f"({t['overdue'].format(days=days_overdue(task, now)).lower()})"
            for task in tasks
        ]
        enclosures = {self._enclosure_of(task) for task in tasks}
        if len(enclosures) == 1 and None not in enclosures:
            # via=reminder: op de herinnering tikken telt niet als scan van de kast.
            path = f"/arthropoda?enclosure={self.coordinator.enclosures[enclosures.pop()]['code']}&via=reminder"
        else:
            path = "/arthropoda?view=enclosures"
        data: dict[str, Any] = {
            "tag": NOTIFY_TAG,
            "clickAction": path,
            "url": path,
            "channel": nt["channel"],
        }
        max_snoozes = int(self.opt(CONF_NAG_MAX_SNOOZES))
        can_snooze = level == 1 and any(
            self.state.snoozes.get(self._key(task), 0) < max_snoozes for task in tasks
        )
        if can_snooze:
            data["actions"] = [
                {"action": ACTION_LATER, "title": nt["later"]},
                {"action": ACTION_TOMORROW, "title": nt["tomorrow"]},
            ]
        if level >= 2:
            data.update({
                "channel": nt["channel_urgent"],
                "importance": "high",
                "priority": "high",
                "ttl": 0,
                "persistent": True,
                "sticky": "true",
                "push": {"interruption-level": "time-sensitive"},
            })
        return {
            "title": nt["title_urgent"] if level >= 2 else nt["title"],
            "message": "\n".join(lines),
            "data": data,
            "level": level,
        }

    def _enclosure_of(self, task: Task) -> int | None:
        if task.enclosure_id is not None:
            return task.enclosure_id
        snap = (self.coordinator.data or {}).get(task.animal_id)
        return snap.animal.enclosure_id if snap else None

    async def async_send(self, tasks: list[Task], now: datetime, loud: bool = True) -> None:
        note = self.build(tasks, now)
        for target in self._targets():
            await self._notify(target, note["title"], note["message"], note["data"])
        if not self._targets():
            from homeassistant.components import persistent_notification

            persistent_notification.async_create(
                self.hass, note["message"], note["title"], f"{DOMAIN}_nag"
            )
        if loud and note["level"] >= 3:
            await self._loud(tasks, now)
        self.state.last_sent = now.isoformat()
        self.state.sent_active = True
        self._save()

    async def _notify(self, target: str, title: str, message: str, data: dict[str, Any] | None) -> None:
        try:
            if self.hass.states.get(target) is not None:
                # notify-entiteit: geen extra gegevens mogelijk (gewone melding).
                await self.hass.services.async_call(
                    "notify", "send_message", {"entity_id": target, "title": title, "message": message},
                    blocking=True,
                )
                return
            payload: dict[str, Any] = {"message": message}
            if title:
                payload["title"] = title
            if data:
                payload["data"] = data
            await self.hass.services.async_call(
                "notify", target.removeprefix("notify."), payload, blocking=True
            )
        except (HomeAssistantError, ValueError) as err:
            _LOGGER.warning("Herinnering naar %s mislukt: %s", target, err)

    async def _loud(self, tasks: list[Task], now: datetime) -> None:
        language = self.hass.config.language or "en"
        t, nt = texts(language), nag_texts(language)
        player, tts, light = (self.opt(CONF_NAG_MEDIA_PLAYER), self.opt(CONF_NAG_TTS), self.opt(CONF_NAG_LIGHT))
        if player and tts:
            names = ", ".join(
                f"{t.get(task.kind, task.kind)} {self.coordinator.task_target_name(task)}" for task in tasks[:4]
            )
            speech = nt["speech"].format(
                n=len(tasks), days=max(days_overdue(x, now) for x in tasks), list=names
            )
            try:
                await self.hass.services.async_call(
                    "tts", "speak",
                    {"entity_id": tts, "media_player_entity_id": player, "message": speech},
                    blocking=True,
                )
            except (HomeAssistantError, ValueError) as err:
                _LOGGER.warning("Gesproken herinnering mislukt: %s", err)
        if light:
            try:
                await self.hass.services.async_call(
                    "light", "turn_on", {"entity_id": light, "flash": "long"}, blocking=True
                )
            except (HomeAssistantError, ValueError) as err:
                _LOGGER.warning("Lamp laten knipperen mislukt: %s", err)

    async def _clear(self) -> None:
        for target in self._targets():
            if self.hass.states.get(target) is None:
                await self._notify(target, "", "clear_notification", {"tag": NOTIFY_TAG})
        from homeassistant.components import persistent_notification

        persistent_notification.async_dismiss(self.hass, f"{DOMAIN}_nag")
        self.state.sent_active = False
        self.state.last_sent = None
        self._save()

    # --- knoppen in de melding ------------------------------------------------

    async def _on_action(self, event: Event) -> None:
        action = event.data.get("action")
        if action not in (ACTION_LATER, ACTION_TOMORROW):
            return
        await self.async_snooze(tomorrow=action == ACTION_TOMORROW)

    async def async_snooze(self, tomorrow: bool) -> int:
        """Taken die nog mogen, stilzetten. Geeft het aantal uitgestelde taken."""
        now = dt_util.utcnow()
        if tomorrow:
            end = dt_util.parse_time(str(self.opt(CONF_QUIET_END))) or time(8)
            day = dt_util.as_local(now).date() + timedelta(days=1)
            until = datetime.combine(day, end, tzinfo=dt_util.get_default_time_zone())
        else:
            until = now + timedelta(hours=1)
        max_snoozes = int(self.opt(CONF_NAG_MAX_SNOOZES))
        count = 0
        for task in self.overdue_tasks(now):
            if self.level([task], now) >= 2:
                continue  # dringend: niet meer uitstelbaar
            key = self._key(task)
            if self.state.snoozes.get(key, 0) >= max_snoozes:
                continue
            self.state.snoozes[key] = self.state.snoozes.get(key, 0) + 1
            self.state.silenced_until[key] = until.isoformat()
            count += 1
        # Oude sleutels opruimen (taken die intussen gedaan zijn).
        live = {self._key(t) for t in self.coordinator.all_tasks()}
        for store in (self.state.snoozes, self.state.silenced_until):
            for key in [k for k in store if k not in live]:
                store.pop(key)
        self.state.last_sent = None  # volgende herinnering na het uitstel, niet pas na het interval
        self._save()
        remaining = self.overdue_tasks(now)
        if remaining:
            await self.async_send(remaining, now, loud=False)
        else:
            await self._clear()
        return count
