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
from .const import MULTI_ACTUATOR_KEYS, SENSOR_KEYS, TUNING_KEYS
from .db import Database
from .journal import can_molt
from .models import AnimalBundle
from .plants import (
    CONF_LIGHT_HOURS,
    CONF_PLANTS,
    PlantSnapshot,
    _PlantRef,
    plant_thresholds,
    plant_values,
    plants_steer,
)
from .profile import Readings, enclosure_too_small, evaluate, resolve_profile, target_temperature
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
        self.enclosures: dict[int, dict[str, Any]] = {}
        self.enclosure_tasks: list[Task] = []
        self.effective_configs: dict[str, dict[str, Any]] = {}
        # Planten in plantenkasten (zonder dieren) als leden van klimaatgroepen.
        self.plant_snapshots: dict[str, PlantSnapshot] = {}
        self.plant_last: dict[str, dict[str, str]] = {}
        # Aandringen en scanbewijs (NagManager, gezet in __init__.py).
        self.nag = None
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
        configs = list((self.effective_configs or self.animal_configs).values())
        configs += [snap.config for snap in self.plant_snapshots.values()]
        for cfg in configs:
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

        self._tracked = sources
        self._unsub_state = async_track_state_change_event(self.hass, sources, _changed)

    @callback
    def _retrack_if_needed(self) -> None:
        """Sensoren opnieuw volgen als een kast andere sensoren kreeg."""
        if self._source_entities() != getattr(self, "_tracked", set()):
            self.async_stop_tracking()
            self.async_start_tracking()

    @callback
    def async_stop_tracking(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None

    # --- data -------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, AnimalSnapshot]:
        def _load():
            enclosures = {e["id"]: e for e in self.db.list_enclosures()}
            plants = sorted({p for e in enclosures.values() for p in (e["config"].get(CONF_PLANTS) or [])})
            return (
                self.db.load_bundles(list(self.animal_configs)),
                self.db.list_broods(status="incubating"),
                self.db.list_stock(),
                self.db.list_documents(),
                enclosures,
                self.db.last_plant_entries(plants),
            )

        (
            self._bundles, self.broods, self.stock, self.documents, self.enclosures, self.plant_last,
        ) = await self.hass.async_add_executor_job(_load)
        result = self._compute()
        if self._unsub_state is not None or self._source_entities():
            self._retrack_if_needed()
        return result

    # --- kasten -----------------------------------------------------------

    def residents(self, enclosure_id: int, monitored_only: bool = True) -> list[str]:
        """Dieren in een kast."""
        return [
            aid for aid, bundle in self._bundles.items()
            if bundle.animal.enclosure_id == enclosure_id
            and (not monitored_only or bundle.animal.status in MONITORED_STATUSES)
        ]

    def enclosure_readings(self, enclosure_id: int) -> Readings | None:
        """Actuele sensorwaarden van een kast (None zonder sensoren)."""
        cfg = (self.enclosures.get(enclosure_id) or {}).get("config") or {}
        if not any(cfg.get(k) for k in SENSOR_KEYS if k != "food_plants"):
            return None
        return self._readings(cfg)

    def plant_cabinet(self, enclosure_id: int) -> bool:
        """Stuurt deze kast op haar planten (planten en geen dieren)?"""
        enc = self.enclosures.get(enclosure_id)
        return bool(enc) and plants_steer(enc, bool(self.residents(enclosure_id)))

    def _plant_snapshots(self, now: datetime) -> dict[str, PlantSnapshot]:
        """Eén lid per plant voor elke kast die op haar planten stuurt."""
        result: dict[str, PlantSnapshot] = {}
        climate_keys = (*[k for k in SENSOR_KEYS if k != "food_plants"], *ACTUATOR_KEYS)
        for enc_id, enc in self.enclosures.items():
            cfg = enc.get("config") or {}
            if enc.get("status") == "maintenance" or not self.plant_cabinet(enc_id):
                continue
            if not any(cfg.get(k) for k in climate_keys):
                continue
            readings = self._readings(cfg)
            for entity_id in cfg.get(CONF_PLANTS) or []:
                state = self.hass.states.get(entity_id)
                values = plant_values(plant_thresholds(self.hass, entity_id), cfg.get(CONF_LIGHT_HOURS))
                is_day, day_start, day_end = self._day_window(values, now)
                name = (state.attributes.get("friendly_name") if state else None) or entity_id
                result[f"plant:{enc_id}:{entity_id}"] = PlantSnapshot(
                    animal=_PlantRef(f"plant:{enc_id}:{entity_id}", name),
                    enclosure_id=enc_id,
                    config={**cfg, "climate_from_enclosure": enc_id},
                    values=values,
                    readings=readings,
                    is_day=is_day,
                    day_start=day_start,
                    day_end=day_end,
                    monitored=state is not None,
                )
        return result

    def _effective_config(self, animal_id: str, cfg: dict[str, Any]) -> dict[str, Any]:
        """Configuratie van een dier, met klimaat van de kast als die er een heeft.

        Heeft de kast sensoren of toestellen, dan bepaalt de kast het volledige
        klimaat (sensoren, toestellen, afstelling) voor al haar bewoners.
        """
        bundle = self._bundles.get(animal_id)
        enc = self.enclosures.get(bundle.animal.enclosure_id) if bundle else None
        enc_cfg = (enc or {}).get("config") or {}
        climate_keys = (*[k for k in SENSOR_KEYS if k != "food_plants"], *ACTUATOR_KEYS)
        if not any(enc_cfg.get(k) for k in climate_keys):
            return cfg
        merged = {k: v for k, v in cfg.items() if k not in (*climate_keys, *TUNING_KEYS)}
        merged.update({k: v for k, v in enc_cfg.items() if k in (*climate_keys, *TUNING_KEYS) and v not in (None, "", [])})
        merged["climate_from_enclosure"] = enc["id"]
        return merged

    def _enclosure_tasks(self, snapshots: dict[str, "AnimalSnapshot"], now: datetime) -> list[Task]:
        """Schoonmaak/substraat per kast (één taak voor alle bewoners) en uitrusting."""
        tasks: list[Task] = []
        for enc_id, enc in self.enclosures.items():
            residents = [snapshots[a] for a in self.residents(enc_id) if a in snapshots]
            snooze = {
                k: parsed for k, iso in ((enc.get("config") or {}).get("snooze") or {}).items()
                if (parsed := dt_util.parse_datetime(iso)) is not None
            }
            for kind, interval_key, counter in (
                ("cleaning", "cleaning_interval_days", "cleaning"),
                ("substrate_change", "substrate_change_interval_days", "substrate_change"),
            ):
                intervals = [s.values.get(interval_key) for s in residents if s.values.get(interval_key)]
                if not intervals:
                    continue
                lasts = [s.bundle.last_ts.get(counter) for s in residents if s.bundle.last_ts.get(counter)]
                base = max(lasts) if lasts else min(s.animal.created_at for s in residents)
                due = base + timedelta(days=min(intervals))
                if snooze.get(kind) and snooze[kind] > due:
                    due = snooze[kind]
                tasks.append(Task("", kind, due, float(min(intervals)), enclosure_id=enc_id))
            for index, item in enumerate(enc.get("equipment") or []):
                interval = item.get("interval_days")
                if not interval:
                    continue
                start = dt_util.parse_date(item.get("serviced_at") or "") or dt_util.parse_date(
                    (enc.get("created_at") or "")[:10]
                )
                if start is None:
                    continue
                due = dt_util.start_of_local_day(start) + timedelta(days=float(interval))
                key = f"equipment:{index}"
                if snooze.get(key) and snooze[key] > due:
                    due = snooze[key]
                tasks.append(Task("", "equipment", due, float(interval), enclosure_id=enc_id,
                                  index=index, label=item.get("name") or item.get("type")))
        return tasks

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
        if self._bundles or self.enclosures:
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
        self.effective_configs = {
            aid: self._effective_config(aid, configs.get(aid, {})) for aid in self._bundles
        }
        default_fast = self.config_entry.options.get(
            CONF_POST_MOLT_FAST_DAYS, DEFAULT_POST_MOLT_FAST_DAYS
        )
        result: dict[str, AnimalSnapshot] = {}

        for animal_id, bundle in self._bundles.items():
            animal = bundle.animal
            cfg = self.effective_configs.get(animal_id, {})
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
                if animal.enclosure_id in self.enclosures:
                    # Schoonmaak en substraat gebeuren per kast (zie _enclosure_tasks).
                    snapshot.tasks = [
                        t for t in snapshot.tasks if t.kind not in ("cleaning", "substrate_change")
                    ]
                    snapshot.problems = [p for p in snapshot.problems if p != "cleaning_overdue"]
                    if enclosure_too_small(self.enclosures[animal.enclosure_id], bundle.species):
                        snapshot.problems.append("enclosure_too_small")
                if snapshot.can_molt:
                    snapshot.next_molt = estimate_next_molt(bundle.molt_times)
            result[animal_id] = snapshot
        self.enclosure_tasks = self._enclosure_tasks(result, now)
        self.plant_snapshots = self._plant_snapshots(now)
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
        if self.nag is not None:
            # Taak over tijd? Dan eerst de kast scannen (ScanRequired).
            self.nag.check_log_allowed(animal_ids, entry_type)
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
        """Taken van alle bewaakte dieren en kasten, gesorteerd op vervaldatum."""
        tasks = [t for snap in (self.data or {}).values() for t in snap.tasks]
        tasks.extend(self.enclosure_tasks)
        return sorted(tasks, key=lambda t: t.due)

    def task_target_name(self, task: Task) -> str:
        """Naam van het dier of de kast waar een taak bij hoort."""
        if task.enclosure_id is not None:
            enc = self.enclosures.get(task.enclosure_id) or {}
            name = f"{enc.get('code', '?')}{' – ' + enc['name'] if enc.get('name') else ''}"
            return f"{task.label} ({name})" if task.label else name
        snap = (self.data or {}).get(task.animal_id)
        return snap.animal.name if snap else "?"

    async def async_complete_task(self, task: Task) -> None:
        """Taak afvinken: dagboekregel(s) of onderhoud van een toestel noteren."""
        if task.enclosure_id is None:
            await self.async_log([task.animal_id], task.journal_type, data={"source": "todo"})
            return
        if task.kind == "equipment":
            if self.nag is not None:
                self.nag.check_equipment_allowed(task)
            day = dt_util.now().date().isoformat()
            await self.hass.async_add_executor_job(
                self.db.service_equipment, task.enclosure_id, task.index, day
            )
            await self.async_refresh()
            return
        residents = self.residents(task.enclosure_id)
        if residents:
            await self.async_log(
                residents, task.journal_type,
                data={"source": "todo", "enclosure_id": task.enclosure_id},
            )

    async def async_snooze_task(self, task: Task, until: datetime) -> None:
        if task.enclosure_id is None:
            await self.async_snooze(task.animal_id, task.kind, until)
            return
        enc = self.enclosures[task.enclosure_id]
        key = f"equipment:{task.index}" if task.kind == "equipment" else task.kind
        config = dict(enc.get("config") or {})
        config["snooze"] = {**(config.get("snooze") or {}), key: until.isoformat()}
        await self.hass.async_add_executor_job(
            self.db.save_enclosure, {**enc, "config": config}
        )
        await self.async_refresh()

    async def async_assign(self, animal_id: str, enclosure_id: int | None) -> None:
        """Dier in een kast zetten (of eruit halen) en de verhuis noteren."""
        bundle = self._bundles.get(animal_id)
        if bundle is None:
            raise KeyError(animal_id)
        old = bundle.animal.enclosure_id
        if old == enclosure_id:
            return
        await self.hass.async_add_executor_job(
            lambda: self.db.update_animal(animal_id, enclosure_id=enclosure_id)
        )
        code = lambda eid: (self.enclosures.get(eid) or {}).get("code") if eid else None  # noqa: E731
        if bundle.animal.status in MONITORED_STATUSES:
            await self.async_log(
                [animal_id], "rehouse",
                data={"from": code(old), "to": code(enclosure_id), "enclosure_id": enclosure_id},
            )
        else:
            await self.async_refresh()

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
