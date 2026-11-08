"""Klimaatregelaar: stuurt verwarming, verneveling, licht, ventilatie en water.

Werking:
- Elke actuator (bv. switch.warmtemat_rek_2) vormt een *klimaatgroep* met alle
  dieren die hem in hun configuratie hebben staan.
- Het doelbereik van de groep is de overlap van de profielen van die dieren.
  Zonder overlap → reparatiemelding in HA en het gemiddelde wordt gebruikt.
- Dieren met de schakelaar 'Klimaatsturing' uit, of die niet (meer) actief
  zijn, tellen niet mee. Blijft er niemand over, dan wordt de actuator niet
  aangeraakt.
- De regelaar beslist bij elke sensorwijziging en elke 30 seconden.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_ON
from homeassistant.core import CALLBACK_TYPE, CoreState, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.util import dt as dt_util

from . import control
from .const import (
    CONF_FAN,
    CONF_HEATER,
    CONF_HYSTERESIS,
    CONF_LIGHT_RAMP_MINUTES,
    CONF_LIGHTS,
    CONF_MIST_MAX_PER_DAY,
    CONF_MIST_PAUSE_MINUTES,
    CONF_MIST_SECONDS,
    CONF_MIST_TIMES,
    CONF_MISTER,
    CONF_PUMPS,
    CONF_WATER_HEATER,
    CONTROL_TICK_SECONDS,
    DOMAIN,
    MAINTENANCE_MINUTES,
    MIN_SWITCH_INTERVAL_SECONDS,
    MULTI_ACTUATOR_KEYS,
    TUNING_DEFAULTS,
)
from .coordinator import AnimalSnapshot, ArthropodaCoordinator
from .profile import safe_temperature

_LOGGER = logging.getLogger(__name__)

# Rollen die tijdens onderhoud uit gaan.
PAUSED_DURING_MAINTENANCE = {CONF_MISTER, CONF_FAN, CONF_PUMPS}

ROLE_ORDER = (CONF_HEATER, CONF_WATER_HEATER, CONF_MISTER, CONF_LIGHTS, CONF_FAN, CONF_PUMPS)


@dataclass(slots=True)
class ActuatorState:
    """Wat de regelaar over een actuator onthoudt."""

    last_change: datetime | None = None
    last_pulse: datetime | None = None
    pulses_day: str | None = None
    pulses_today: int = 0
    done_schedule: set[str] = field(default_factory=set)
    last_level: float | None = None


@dataclass(slots=True)
class GroupResult:
    """Resultaat van één beslissing, voor de diagnostische sensor."""

    role: str
    entity_id: str
    members: list[str]
    action: str
    reason: str
    target: list[float] | None = None
    setpoint: float | None = None
    conflict: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "entity_id": self.entity_id,
            "members": self.members,
            "action": self.action,
            "reason": self.reason,
            "target": self.target,
            "setpoint": self.setpoint,
            "conflict": self.conflict,
        }


class ClimateController:
    """Stuurt de actuatoren van alle dieren."""

    def __init__(self, hass: HomeAssistant, coordinator: ArthropodaCoordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._states: dict[str, ActuatorState] = {}
        self._maintenance_until: dict[str, datetime] = {}
        self._pending_off: dict[str, CALLBACK_TYPE] = {}
        self._unsubs: list[Callable[[], None]] = []
        self._start_unsub: Callable[[], None] | None = None
        self._running = False
        self._busy = False
        self._dirty = False
        self._publishing = False
        self._conflicts: set[str] = set()
        self.results: dict[str, GroupResult] = {}

    # --- levenscyclus -----------------------------------------------------

    @callback
    def async_start(self) -> None:
        """Start pas als HA volledig opgestart is (sensoren hebben dan waarden)."""
        if self.hass.state is CoreState.running:
            self._begin()
            return

        @callback
        def _started(_event: Event) -> None:
            self._start_unsub = None
            self._begin()

        # async_listen_once meldt zichzelf af na het afvuren; alleen afmelden
        # als HA nog niet gestart was toen de integratie stopte.
        self._start_unsub = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, _started
        )

    @callback
    def _begin(self) -> None:
        self._running = True
        self._unsubs.append(self.coordinator.async_add_listener(self._on_update))
        self._unsubs.append(
            async_track_time_interval(
                self.hass, self._on_tick, timedelta(seconds=CONTROL_TICK_SECONDS)
            )
        )
        self._schedule()

    async def async_stop(self) -> None:
        """Stoppen; lopende vernevelpulsen worden meteen beëindigd."""
        self._running = False
        if self._start_unsub is not None:
            self._start_unsub()
            self._start_unsub = None
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for entity_id, cancel in list(self._pending_off.items()):
            cancel()
            await self._turn(entity_id, False)
        self._pending_off.clear()

    @callback
    def _on_update(self) -> None:
        if not self._publishing:
            self._schedule()

    @callback
    def _on_tick(self, _now: datetime) -> None:
        # Herberekent dag/nacht, verouderde sensoren, ... en daarna _on_update.
        self.coordinator.async_recompute()

    @callback
    def _schedule(self) -> None:
        if not self._running:
            return
        if self._busy:
            self._dirty = True  # na de lopende evaluatie nog eens
            return
        self.hass.async_create_task(self.async_evaluate(), eager_start=True)

    # --- onderhoudsmodus --------------------------------------------------

    def maintenance_active(self, animal_id: str) -> bool:
        until = self._maintenance_until.get(animal_id)
        return until is not None and dt_util.utcnow() < until

    def maintenance_until(self, animal_id: str) -> datetime | None:
        return self._maintenance_until.get(animal_id) if self.maintenance_active(animal_id) else None

    async def async_set_maintenance(self, animal_id: str, active: bool) -> None:
        if active:
            self._maintenance_until[animal_id] = dt_util.utcnow() + timedelta(
                minutes=MAINTENANCE_MINUTES
            )
        else:
            self._maintenance_until.pop(animal_id, None)
        await self.async_evaluate()

    # --- groepen ----------------------------------------------------------

    def _groups(self) -> dict[tuple[str, str], list[str]]:
        """(rol, entity_id) -> dier-ids, in vaste volgorde."""
        groups: dict[tuple[str, str], list[str]] = {}
        configs = self.coordinator.effective_configs or self.coordinator.animal_configs
        for animal_id, cfg in sorted(configs.items()):
            for role in ROLE_ORDER:
                value = cfg.get(role)
                if not value:
                    continue
                entity_ids = value if role in MULTI_ACTUATOR_KEYS else [value]
                for entity_id in entity_ids:
                    groups.setdefault((role, entity_id), []).append(animal_id)
        return groups

    @staticmethod
    def _tuning(snapshots: list[AnimalSnapshot], key: str) -> Any:
        for snap in snapshots:
            value = snap.config.get(key)
            if value not in (None, ""):
                return value
        return TUNING_DEFAULTS[key]

    # --- beslissen --------------------------------------------------------

    async def async_evaluate(self) -> None:
        if self._busy or not self.coordinator.data:
            return
        self._busy = True
        try:
            now = dt_util.utcnow()
            results: dict[str, GroupResult] = {}
            conflicts: set[str] = set()
            for (role, entity_id), animal_ids in self._groups().items():
                active = [
                    self.coordinator.data[a]
                    for a in animal_ids
                    if a in self.coordinator.data
                    and self.coordinator.data[a].monitored
                    and self.coordinator.data[a].climate_enabled
                ]
                result = await self._evaluate_group(role, entity_id, active, now)
                result.members = animal_ids
                results[entity_id] = result
                if result.conflict:
                    conflicts.add(entity_id)
            self._update_issues(conflicts, results)
            changed = {k: v.as_dict() for k, v in results.items()} != {
                k: v.as_dict() for k, v in self.results.items()
            }
            self.results = results
            if changed:
                self._publishing = True
                try:
                    self.coordinator.async_update_listeners()
                finally:
                    self._publishing = False
        finally:
            self._busy = False
        if self._dirty:
            self._dirty = False
            self._schedule()

    async def _evaluate_group(
        self, role: str, entity_id: str, snaps: list[AnimalSnapshot], now: datetime
    ) -> GroupResult:
        if not snaps:
            return GroupResult(role, entity_id, [], "none", "control_disabled")
        if self.hass.states.get(entity_id) is None:
            return GroupResult(role, entity_id, [], "none", "actuator_missing")

        maintenance = any(self.maintenance_active(s.animal.id) for s in snaps)
        if maintenance and role in PAUSED_DURING_MAINTENANCE:
            await self._apply(entity_id, control.Decision(False, "maintenance"), critical=True)
            return GroupResult(role, entity_id, [], "off", "maintenance")

        if role in (CONF_HEATER, CONF_WATER_HEATER):
            return await self._heater(role, entity_id, snaps)
        if role == CONF_MISTER:
            return await self._mister(entity_id, snaps, now)
        if role == CONF_FAN:
            return await self._fan(entity_id, snaps)
        if role == CONF_LIGHTS:
            return await self._light(entity_id, snaps, now)
        # Pomp, filter, luchtpomp: altijd aan (behalve tijdens onderhoud).
        await self._apply(entity_id, control.Decision(True, "always_on"))
        return GroupResult(role, entity_id, [], "on", "always_on")

    async def _heater(self, role: str, entity_id: str, snaps: list[AnimalSnapshot]) -> GroupResult:
        water = role == CONF_WATER_HEATER
        if water:
            ranges = [s.values.get("water_temp") for s in snaps]
            temps = [s.readings.water_temperature for s in snaps if s.readings.water_temperature is not None]
            safe_values = [r[1] + control.DEFAULT_SAFE_MARGIN for r in ranges if r]
        else:
            ranges = [s.target_temperature for s in snaps]
            temps = [t for s in snaps for t in s.readings.temperatures]
            safe_values = [v for v in (safe_temperature(s.values) for s in snaps) if v is not None]
        target, conflict = control.combine_ranges(ranges)
        safe_max = min(safe_values) if safe_values else None
        sensor_problem = any(s.readings.unavailable for s in snaps) and not temps

        domain = entity_id.split(".")[0]
        decision = control.heater(
            temps,
            target,
            safe_max,
            self._is_on(entity_id),
            float(self._tuning(snaps, CONF_HYSTERESIS)),
            sensor_problem,
            proportional=domain == "light",
        )
        if domain == "climate":
            await self._apply_climate(entity_id, decision)
        else:
            await self._apply(entity_id, decision, critical=decision.critical)
        return GroupResult(
            role, entity_id, [], _action(decision), decision.reason, target,
            decision.setpoint, conflict,
        )

    async def _mister(self, entity_id: str, snaps: list[AnimalSnapshot], now: datetime) -> GroupResult:
        state = self._states.setdefault(entity_id, ActuatorState())
        local = dt_util.as_local(now)
        today = local.date().isoformat()
        if state.pulses_day != today:
            state.pulses_day, state.pulses_today, state.done_schedule = today, 0, set()

        # Vaste tijdstippen: binnen 5 minuten na het tijdstip, één keer per dag.
        due = False
        for hour, minute in control.parse_times(self._tuning(snaps, CONF_MIST_TIMES)):
            key = f"{hour:02d}:{minute:02d}"
            moment = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if key not in state.done_schedule and timedelta(0) <= local - moment < timedelta(minutes=5):
                state.done_schedule.add(key)
                due = True

        humidities = [s.readings.humidity for s in snaps if s.readings.humidity is not None]
        target, conflict = control.combine_ranges([s.values.get("humidity") for s in snaps])
        decision = control.mister(
            min(humidities) if humidities else None,
            target,
            now,
            state.last_pulse,
            state.pulses_today,
            int(self._tuning(snaps, CONF_MIST_MAX_PER_DAY)),
            timedelta(minutes=float(self._tuning(snaps, CONF_MIST_PAUSE_MINUTES))),
            due,
        )
        if decision.on and entity_id not in self._pending_off:
            state.last_pulse = now
            state.pulses_today += 1
            await self._pulse(entity_id, float(self._tuning(snaps, CONF_MIST_SECONDS)))
            action = "pulse"
        else:
            action = "none"
        return GroupResult(CONF_MISTER, entity_id, [], action, decision.reason, target, None, conflict)

    async def _fan(self, entity_id: str, snaps: list[AnimalSnapshot]) -> GroupResult:
        temps = [t for s in snaps for t in s.readings.temperatures]
        humidities = [s.readings.humidity for s in snaps if s.readings.humidity is not None]
        t_target, c1 = control.combine_ranges([s.target_temperature for s in snaps])
        h_target, c2 = control.combine_ranges([s.values.get("humidity") for s in snaps])
        decision = control.fan(
            temps, max(humidities) if humidities else None, t_target, h_target,
            self._is_on(entity_id),
        )
        await self._apply(entity_id, decision)
        return GroupResult(CONF_FAN, entity_id, [], _action(decision), decision.reason,
                           h_target, None, c1 or c2)

    async def _light(self, entity_id: str, snaps: list[AnimalSnapshot], now: datetime) -> GroupResult:
        # Gedeeld licht: aan zolang het voor minstens één dier dag is.
        day_snaps = [s for s in snaps if s.is_day]
        ref = day_snaps[0] if day_snaps else snaps[0]
        ramp = float(self._tuning(snaps, CONF_LIGHT_RAMP_MINUTES))
        decision = control.light(bool(day_snaps), dt_util.as_local(now), ref.day_start, ref.day_end, ramp)
        if entity_id.startswith("light.") and ramp:
            await self._apply(entity_id, decision)
        else:
            await self._apply(entity_id, control.Decision(decision.on, decision.reason))
        return GroupResult(CONF_LIGHTS, entity_id, [], _action(decision), decision.reason)

    # --- uitvoeren --------------------------------------------------------

    def _is_on(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        if entity_id.startswith("climate."):
            return state.state not in ("off", "unavailable", "unknown")
        return state.state == STATE_ON

    async def _apply(self, entity_id: str, decision: control.Decision, critical: bool = False) -> None:
        if decision.on is None:
            return
        state = self._states.setdefault(entity_id, ActuatorState())
        now = dt_util.utcnow()
        is_on = self._is_on(entity_id)
        domain = entity_id.split(".")[0]

        # Dimbare lampen: helderheid bijsturen zonder aan/uit-beperking.
        if domain == "light" and decision.on and decision.level is not None:
            if not is_on or state.last_level is None or abs(state.last_level - decision.level) >= 1:
                await self._call("light", "turn_on", entity_id, {"brightness_pct": decision.level})
                state.last_level = decision.level
                if not is_on:
                    state.last_change = now
            return

        if decision.on == is_on:
            return
        # Relais sparen: niet vaker schakelen dan elke minuut, behalve bij gevaar
        # of als iets uit moet.
        if (
            not critical
            and decision.on
            and state.last_change is not None
            and now - state.last_change < timedelta(seconds=MIN_SWITCH_INTERVAL_SECONDS)
        ):
            return
        await self._turn(entity_id, decision.on)
        state.last_change = now
        state.last_level = None

    async def _apply_climate(self, entity_id: str, decision: control.Decision) -> None:
        """Bestaande thermostaat: doeltemperatuur instellen of uitzetten."""
        if decision.on is False and decision.reason in ("over_safe_max", "sensor_unavailable"):
            if self._is_on(entity_id):
                await self._call("climate", "set_hvac_mode", entity_id, {"hvac_mode": "off"})
            return
        if decision.setpoint is None:
            return
        state = self.hass.states.get(entity_id)
        current = state.attributes.get("temperature") if state else None
        if not self._is_on(entity_id):
            await self._call("climate", "set_hvac_mode", entity_id, {"hvac_mode": "heat"})
        if current != decision.setpoint:
            await self._call("climate", "set_temperature", entity_id, {"temperature": decision.setpoint})

    async def _turn(self, entity_id: str, on: bool) -> None:
        domain = entity_id.split(".")[0]
        if domain == "script":
            if on:
                await self._call("script", "turn_on", entity_id)
            return
        service_domain = domain if domain in ("switch", "light", "fan", "input_boolean") else "homeassistant"
        await self._call(service_domain, "turn_on" if on else "turn_off", entity_id)

    async def _pulse(self, entity_id: str, seconds: float) -> None:
        await self._turn(entity_id, True)
        if entity_id.startswith("script."):
            return  # een script regelt zelf hoe lang het nevelt

        @callback
        def _off(_now: datetime) -> None:
            self._pending_off.pop(entity_id, None)
            self.hass.async_create_task(self._turn(entity_id, False))

        self._pending_off[entity_id] = async_call_later(self.hass, seconds, _off)

    async def _call(
        self, domain: str, service: str, entity_id: str, data: dict[str, Any] | None = None
    ) -> None:
        try:
            await self.hass.services.async_call(
                domain, service, {"entity_id": entity_id, **(data or {})}, blocking=True
            )
        except (HomeAssistantError, ValueError) as err:
            _LOGGER.warning("Kon %s.%s niet uitvoeren op %s: %s", domain, service, entity_id, err)

    # --- reparatiemeldingen -----------------------------------------------

    def _update_issues(self, conflicts: set[str], results: dict[str, GroupResult]) -> None:
        for entity_id in conflicts - self._conflicts:
            names = ", ".join(
                self.coordinator.data[a].animal.name
                for a in results[entity_id].members
                if a in self.coordinator.data
            )
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"range_conflict_{entity_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="range_conflict",
                translation_placeholders={"actuator": entity_id, "animals": names},
            )
        for entity_id in self._conflicts - conflicts:
            ir.async_delete_issue(self.hass, DOMAIN, f"range_conflict_{entity_id}")
        self._conflicts = conflicts


def _action(decision: control.Decision) -> str:
    if decision.on is None:
        return "none"
    if decision.level is not None and decision.on:
        return f"on {decision.level:.0f}%"
    return "on" if decision.on else "off"
