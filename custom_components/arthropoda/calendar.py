"""Kalender: geplande taken, dagboek, verwachte vervellingen en uitkomstdata.

- Geplande taken (voederen, schoonmaken, ...) als hele-dag-items, terugkerend.
- Uitgevoerde handelingen uit het dagboek op hun tijdstip.
- Verwachte vervelling (schatting op basis van de vorige intervallen).
- Verwachte uitkomst van eicocons/ootheken (incubatieduur uit de caresheet of
  uit de dagboekregel: data.incubation_days).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import HubEntity
from .tasks import project, texts

JOURNAL_EVENT_MINUTES = 15
LOOKAHEAD = timedelta(days=60)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_add_entities([ArthropodaCalendar(entry.runtime_data.coordinator)])


def _all_day(day: date, summary: str, uid: str, description: str | None = None) -> CalendarEvent:
    return CalendarEvent(
        start=day, end=day + timedelta(days=1), summary=summary, uid=uid, description=description
    )


class ArthropodaCalendar(HubEntity, CalendarEntity):
    """Kalender van de collectie."""

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "calendar")
        self._labels: dict[str, str] = {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        language = self.hass.config.language
        self._labels = await async_get_translations(self.hass, language, "selector", {DOMAIN})

    def _label(self, entry_type: str) -> str:
        key = f"component.{DOMAIN}.selector.entry_type.options.{entry_type}"
        return self._labels.get(key, entry_type)

    # --- berekende items (taken en schattingen) ---------------------------

    def _computed(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        t = texts(self.hass.config.language)
        events: list[CalendarEvent] = []
        data = self.coordinator.data or {}
        start_day = dt_util.as_local(start).date()
        end_day = dt_util.as_local(end).date()

        today_start = dt_util.start_of_local_day()
        for task in self.coordinator.all_tasks():
            if task.enclosure_id is None and task.animal_id not in data:
                continue
            name = self.coordinator.task_target_name(task)
            # Achterstallige taken staan op vandaag; de volgende rekenen vanaf daar.
            current = replace(task, due=max(task.due, today_start))
            for due in project(current, end):
                day = dt_util.as_local(due).date()
                if start_day <= day < end_day:
                    events.append(_all_day(
                        day, f"{t[task.kind]}: {name}", f"{task.uid}:{day.isoformat()}"
                    ))

        for animal_id, snap in data.items():
            name = snap.animal.name
            if snap.next_molt is not None:
                day = dt_util.as_local(snap.next_molt).date()
                if start_day <= day < end_day:
                    events.append(_all_day(
                        day, t["molt_estimate"].format(name=name), f"{animal_id}:molt_estimate"
                    ))

        # Diapauze: periode tussen vroegste en laatste einde
        for animal_id, snap in data.items():
            dia = snap.diapause
            if not dia or not (dia.get("earliest_end") or dia.get("latest_end")):
                continue
            first = dt_util.parse_datetime(dia.get("earliest_end") or dia["latest_end"])
            last = dt_util.parse_datetime(dia.get("latest_end") or dia["earliest_end"])
            first_day, last_day = dt_util.as_local(first).date(), dt_util.as_local(last).date()
            if first_day < end_day and last_day >= start_day:
                events.append(CalendarEvent(
                    start=first_day, end=last_day + timedelta(days=1),
                    summary=t["diapause_window"].format(name=snap.animal.name),
                    uid=f"{animal_id}:diapause",
                ))

        # Legsels die nog uitbroeden (uit de kweektabel)
        for brood in self.coordinator.broods:
            if not brood.get("expected"):
                continue
            first_day = dt_util.as_local(dt_util.parse_datetime(brood["expected"][0])).date()
            last_day = dt_util.as_local(dt_util.parse_datetime(brood["expected"][1])).date()
            if first_day < end_day and last_day >= start_day:
                mother = data.get(brood["mother_id"])
                name = mother.animal.name if mother else "?"
                events.append(CalendarEvent(
                    start=first_day,
                    end=last_day + timedelta(days=1),
                    summary=t["hatch_estimate"].format(what=t.get(brood["type"], brood["type"]), name=name),
                    uid=f"brood:{brood['id']}",
                ))

        # Documenten die vervallen
        for doc in self.coordinator.documents:
            expires = dt_util.parse_date(doc["expires_at"]) if doc.get("expires_at") else None
            if expires and start_day <= expires < end_day:
                events.append(_all_day(
                    expires, t["document_expires"].format(title=doc["title"]), f"document:{doc['id']}"
                ))
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Eerstvolgend item (voor de status van de kalender-entiteit)."""
        now = dt_util.now()
        upcoming = self._computed(now, now + LOOKAHEAD)
        if not upcoming:
            return None
        return min(upcoming, key=lambda e: e.start_datetime_local)

    # --- dagboek ----------------------------------------------------------

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        events = self._computed(start_date, end_date)
        db = self.coordinator.db
        entries = await hass.async_add_executor_job(db.get_journal_between, start_date, end_date)
        for entry in entries:
            ts: datetime = entry["timestamp"]
            events.append(
                CalendarEvent(
                    start=dt_util.as_local(ts),
                    end=dt_util.as_local(ts) + timedelta(minutes=JOURNAL_EVENT_MINUTES),
                    summary=f"{self._label(entry['type'])}: {entry['animal_name']}",
                    description=_describe(entry),
                    uid=f"journal:{entry['id']}",
                )
            )
        return events


def _describe(entry: dict[str, Any]) -> str | None:
    parts = []
    if entry.get("notes"):
        parts.append(entry["notes"])
    details = {k: v for k, v in (entry.get("data") or {}).items() if k != "source"}
    if details:
        parts.append(", ".join(f"{k}: {v}" for k, v in details.items()))
    return "\n".join(parts) or None
