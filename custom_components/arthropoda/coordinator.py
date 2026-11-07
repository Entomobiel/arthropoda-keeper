"""Coordinator: houdt de toestand van alle dieren bij."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    ACTUATOR_KEYS,
    CONF_DAY_END,
    CONF_DAY_START,
    CONF_HUMIDITY_SENSOR,
    CONF_LIGHT_MODE,
    CONF_POST_MOLT_FAST_DAYS,
    CONF_STALE_MINUTES,
    CONF_TEMPERATURE_SENSORS,
    CONF_WATER_TEMPERATURE_SENSOR,
    DEFAULT_DAY_END,
    DEFAULT_DAY_START,
    DEFAULT_LIGHT_MODE,
    DEFAULT_POST_MOLT_FAST_DAYS,
    DEFAULT_STALE_MINUTES,
    DOMAIN,
    EVENT_JOURNAL_ENTRY,
    MONITORED_STATUSES,
    SUBENTRY_ANIMAL,
)
from .db import Database
from .journal import can_molt
from .models import AnimalBundle
from .profile import Readings, evaluate, resolve_profile, target_temperature
from .tasks import Task, compute_tasks, estimate_next_molt

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=15)


@dataclass(slots=True)
class AnimalSnapshot:
    """Berekende toestand van één dier, voor de entiteiten."""

    bundle: AnimalBundle
    config: dict[str, Any]
    values: dict[str, Any]
    season: str
    is_day: bool
    readings: Readings
    days_since: dict[str, int | None]
    feeding_paused: bool
    next_feeding: datetime | None
    day_start: datetime | None = None
    day_end: datetime | None = None
    problems: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    next_molt: datetime | None = None
    diapause: dict[str, Any] | None = None

    @property
    def animal(self):
        return self.bundle.animal

    @property
    def monitored(self) -> bool:
        return self.animal.status in MONITORED_STATUSES

    @property
    def climate_enabled(self) -> bool:
        """Klimaatsturing aan voor dit dier (schakelaar 'Klimaatsturing')."""
        return bool(self.animal.info.get("climate_control", True))

    @property
    def has_actuators(self) -> bool:
        return any(self.config.get(key) for key in ACTUATOR_KEYS)

    @property
    def can_molt(self) -> bool:
        species = self.bundle.species
        return self.animal.kind == "individual" and can_molt(
            self.animal.stage, species.development if species else None
        )

    @property
    def target_temperature(self) -> list[float] | None:
        return target_temperature(self.values, self.is_day)


def _parse_time(value: str | None, default: str) -> time:
    return dt_util.parse_time(value or default) or dt_util.parse_time(default)  # type: ignore[return-value]


def _days_between(earlier: datetime | None, now: datetime) -> int | None:
    """Kalenderdagen tussen twee tijdstippen (lokale tijd)."""
    if earlier is None:
        return None
    return (dt_util.as_local(now).date() - dt_util.as_local(earlier).date()).days


class ArthropodaCoordinator(DataUpdateCoordinator[dict[str, AnimalSnapshot]]):
    """Laadt dieren uit de database en evalueert ze tegen hun profiel."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, db: Database) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.db = db
        self._bundles: dict[str, AnimalBundle] = {}
        self.broods: list[dict[str, Any]] = []
        self.stock: list[dict[str, Any]] = []
        self.documents: list[dict[str, Any]] = []
        self._unsub_state: Callable[[], None] | None = None

    # --- configuratie -----------------------------------------------------

    @property
    def animal_configs(self) -> dict[str, dict[str, Any]]:
        """subentry_id -> subentry-data van alle dieren."""
        return {
            sid: dict(sub.data)
            for sid, sub in self.config_entry.subentries.items()
            if sub.subentry_type == SUBENTRY_ANIMAL
        }

    def _source_entities(self) -> set[str]:
        ids: set[str] = set()
        for cfg in self.animal_configs.values():
            ids.update(cfg.get(CONF_TEMPERATURE_SENSORS) or [])
            for key in (CONF_HUMIDITY_SENSOR, CONF_WATER_TEMPERATURE_SENSOR):
                if cfg.get(key):
                    ids.add(cfg[key])
        return ids

    @callback
    def async_start_tracking(self) -> None:
        """Herbereken bij elke wijziging van een gekoppelde sensor."""
        sources = self._source_entities()
        if not sources:
            return

        @callback
        def _changed(event: Event[EventStateChangedData]) -> None:
            self.async_recompute()

        self._unsub_state = async_track_state_change_event(self.hass, sources, _changed)

    @callback
    def async_stop_tracking(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None

    # --- data -------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, AnimalSnapshot]:
        def _load():
            return (
                self.db.load_bundles(list(self.animal_configs)),
                self.db.list_broods(status="incubating"),
                self.db.list_stock(),
                self.db.list_documents(),
            )

        self._bundles, self.broods, self.stock, self.documents = (
            await self.hass.async_add_executor_job(_load)
        )
        return self._compute()

    # --- collectie-overzicht (kweek, voorraad, documenten) -----------------

    def low_stock(self) -> list[dict[str, Any]]:
        """Voorraden onder hun minimum."""
        return [
            s for s in self.stock
            if s.get("min_quantity") is not None and s["quantity"] < s["min_quantity"]
        ]

    def expiring_documents(self, days: int = 30) -> list[dict[str, Any]]:
        """Documenten die binnen `days` dagen vervallen (of al vervallen zijn)."""
        limit = dt_util.now().date() + timedelta(days=days)
        result = []
        for doc in self.documents:
            expires = dt_util.parse_date(doc["expires_at"]) if doc.get("expires_at") else None
            if expires and expires <= limit:
                result.append(doc)
        return result

    def broods_due(self, days: int = 7) -> list[dict[str, Any]]:
        """Legsels waarvan de uitkomst binnen `days` dagen kan beginnen."""
        limit = dt_util.utcnow() + timedelta(days=days)
        return [
            b for b in self.broods
            if b.get("expected") and dt_util.parse_datetime(b["expected"][0]) <= limit
        ]

    @callback
    def async_recompute(self) -> None:
        """Herbereken zonder de database te lezen (bv. na een sensorwijziging)."""
        if self._bundles:
            self.async_set_updated_data(self._compute())

    def _read(self, entity_id: str | None, readings: Readings, temperature: bool) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            readings.unavailable.append(entity_id)
            return None
        stale = self.config_entry.options.get(CONF_STALE_MINUTES, DEFAULT_STALE_MINUTES)
        last = getattr(state, "last_reported", None) or state.last_updated
        if stale and dt_util.utcnow() - last > timedelta(minutes=stale):
            # Sensor geeft al te lang niets door (lege batterij, buiten bereik, ...)
            readings.unavailable.append(entity_id)
            return None
        try:
            value = float(state.state)
        except ValueError:
            readings.unavailable.append(entity_id)
            return None
        if temperature:
            unit = state.attributes.get("unit_of_measurement")
            if unit in (UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.KELVIN):
                value = TemperatureConverter.convert(value, unit, UnitOfTemperature.CELSIUS)
        return value

    def _readings(self, cfg: dict[str, Any]) -> Readings:
        readings = Readings()
        for entity_id in cfg.get(CONF_TEMPERATURE_SENSORS) or []:
            value = self._read(entity_id, readings, temperature=True)
            if value is not None:
                readings.temperatures.append(value)
        readings.humidity = self._read(cfg.get(CONF_HUMIDITY_SENSOR), readings, False)
        readings.water_temperature = self._read(
            cfg.get(CONF_WATER_TEMPERATURE_SENSOR), readings, True
        )
        return readings

    def _day_window(
        self, values: dict[str, Any], now: datetime
    ) -> tuple[bool, datetime | None, datetime | None]:
        """(is het dag, begin, einde) voor een dier.

        - modus 'sun': dag zolang de zon boven de horizon staat;
        - modus 'fixed': dag begint om day_start en duurt light_hours uit de
          caresheet (seizoensgebonden), of tot day_end als die ontbreekt.
        """
        opts = self.config_entry.options
        if opts.get(CONF_LIGHT_MODE, DEFAULT_LIGHT_MODE) == "sun":
            sun = self.hass.states.get("sun.sun")
            if sun is not None:
                return sun.state == "above_horizon", None, None

        local = dt_util.as_local(now)
        start_t = _parse_time(opts.get(CONF_DAY_START), DEFAULT_DAY_START)
        end_t = _parse_time(opts.get(CONF_DAY_END), DEFAULT_DAY_END)
        hours = values.get("light_hours")
        windows = []
        for offset in (0, -1):
            day = local.date() + timedelta(days=offset)
            start = datetime.combine(day, start_t, tzinfo=local.tzinfo)
            if hours:
                end = start + timedelta(hours=hours)
            else:
                end = datetime.combine(day, end_t, tzinfo=local.tzinfo)
                if end <= start:
                    end += timedelta(days=1)
            if start <= local < end:
                return True, start, end
            windows.append((start, end))
        return False, *windows[0]

    def _compute(self) -> dict[str, AnimalSnapshot]:
        now = dt_util.utcnow()
        local = dt_util.as_local(now)
        configs = self.animal_configs
        default_fast = self.config_entry.options.get(
            CONF_POST_MOLT_FAST_DAYS, DEFAULT_POST_MOLT_FAST_DAYS
        )
        result: dict[str, AnimalSnapshot] = {}

        for animal_id, bundle in self._bundles.items():
            animal = bundle.animal
            cfg = configs.get(animal_id, {})
            values, season = resolve_profile(
                bundle.profiles, animal.stage, animal.season_mode, local.month
            )
            readings = self._readings(cfg)
            is_day, day_start, day_end = self._day_window(values, now)

            # Basis voor "dagen sinds voedering" als er nog niets gelogd is.
            baseline = animal.created_at
            acquired = dt_util.parse_date(animal.acquired_at) if animal.acquired_at else None
            if acquired:
                baseline = dt_util.start_of_local_day(acquired)
            last = bundle.last_ts
            days_since = {
                "feeding": _days_between(last.get("feeding") or baseline, now),
                "molt": _days_between(last.get("molt"), now),
                "cleaning": _days_between(last.get("cleaning") or baseline, now),
                "substrate_change": _days_between(last.get("substrate_change"), now),
                "water_change": _days_between(last.get("water_change") or baseline, now),
                "misting": _days_between(last.get("misting"), now),
            }

            fast_days = values.get("post_molt_fast_days", default_fast)
            recently_molted = (
                last.get("molt") is not None
                and now - last["molt"] < timedelta(days=fast_days)
            )
            feeding_paused = animal.premolt or animal.status == "diapause" or recently_molted

            interval = values.get("feeding_interval_days")
            next_feeding = None
            if interval and not feeding_paused:
                next_feeding = (last.get("feeding") or baseline) + timedelta(days=interval)

            snapshot = AnimalSnapshot(
                bundle=bundle,
                config=cfg,
                values=values,
                season=season,
                is_day=is_day,
                readings=readings,
                days_since=days_since,
                feeding_paused=feeding_paused,
                next_feeding=next_feeding,
                day_start=day_start,
                day_end=day_end,
            )
            if snapshot.monitored:
                snapshot.problems = evaluate(
                    values, readings, is_day, days_since, feeding_paused
                )
                snoozed = {
                    kind: parsed
                    for kind, iso in (animal.info.get("snooze") or {}).items()
                    if (parsed := dt_util.parse_datetime(iso)) is not None
                }
                snapshot.diapause = (
                    animal.info.get("diapause") if animal.status == "diapause" else None
                )
                snapshot.tasks = compute_tasks(
                    animal_id, values, last, baseline, feeding_paused, snoozed,
                    snapshot.diapause,
                )
                if snapshot.can_molt:
                    snapshot.next_molt = estimate_next_molt(bundle.molt_times)
            result[animal_id] = snapshot
        return result

    # --- schrijven --------------------------------------------------------

    async def async_log(
        self,
        animal_ids: list[str],
        entry_type: str,
        ts: datetime | None = None,
        notes: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> list[int]:
        """Dagboekregel toevoegen, gevolgen toepassen en entiteiten bijwerken."""
        ts = ts or dt_util.utcnow()
        data = data or {}
        group_id = None
        if len(animal_ids) > 1:
            group_id = f"{entry_type}-{int(ts.timestamp())}"
        ids = await self.hass.async_add_executor_job(
            self.db.add_entries, animal_ids, entry_type, ts, notes, data, group_id
        )
        await self.async_refresh()
        for animal_id, entry_id in zip(animal_ids, ids, strict=True):
            self.hass.bus.async_fire(
                EVENT_JOURNAL_ENTRY,
                {
                    "entry_id": entry_id,
                    "animal_id": animal_id,
                    "type": entry_type,
                    "timestamp": ts.isoformat(),
                    "notes": notes,
                    "data": data,
                },
            )
        return ids

    def all_tasks(self) -> list[Task]:
        """Taken van alle bewaakte dieren, gesorteerd op vervaldatum."""
        tasks = [t for snap in (self.data or {}).values() for t in snap.tasks]
        return sorted(tasks, key=lambda t: t.due)

    def due_tasks(self) -> list[Task]:
        """Taken die vandaag of eerder vervallen (lokale tijd)."""
        today = dt_util.now().date()
        return [t for t in self.all_tasks() if dt_util.as_local(t.due).date() <= today]

    async def async_snooze(self, animal_id: str, kind: str, until: datetime) -> None:
        """Taak uitstellen tot `until`."""
        animal = self.data[animal_id].animal
        snooze = {**(animal.info.get("snooze") or {}), kind: until.isoformat()}
        await self.async_update_animal(animal_id, info={**animal.info, "snooze": snooze})

    async def async_update_animal(self, animal_id: str, **fields: Any) -> None:
        await self.hass.async_add_executor_job(
            lambda: self.db.update_animal(animal_id, **fields)
        )
        await self.async_refresh()
