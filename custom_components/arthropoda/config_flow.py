"""Configuratie: de collectie (hoofdentry), dieren (subentries) en soorten (opties)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME, PERCENTAGE, UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers import selector

from .caresheet import CaresheetError, ParsedCaresheet, looks_like_path, parse_caresheets
from .const import (
    ACTUATOR_KEYS,
    CONF_ACQUIRED_AT,
    CONF_ALARM_DELAY_MINUTES,
    CONF_BORN_AT,
    CONF_COUNT,
    CONF_DAY_END,
    CONF_DAY_START,
    CONF_DIGEST_ENABLED,
    CONF_DIGEST_TIME,
    CONF_FAN,
    CONF_FOOD_PLANTS,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_HYSTERESIS,
    CONF_INSTAR,
    CONF_KIND,
    CONF_LIGHT_MODE,
    CONF_LIGHT_RAMP_MINUTES,
    CONF_LIGHTS,
    CONF_MIST_MAX_PER_DAY,
    CONF_MIST_PAUSE_MINUTES,
    CONF_MIST_SECONDS,
    CONF_MIST_TIMES,
    CONF_MISTER,
    CONF_NOTIFY_TARGETS,
    CONF_ORIGIN,
    CONF_POST_MOLT_FAST_DAYS,
    CONF_PUMPS,
    CONF_SEX,
    CONF_SPECIES_ID,
    CONF_STAGE,
    CONF_STALE_MINUTES,
    CONF_TEMPERATURE_SENSORS,
    CONF_WATER_HEATER,
    CONF_WATER_TEMPERATURE_SENSOR,
    DEFAULT_ALARM_DELAY_MINUTES,
    DEFAULT_DAY_END,
    DEFAULT_DAY_START,
    DEFAULT_DIGEST_TIME,
    DEFAULT_LIGHT_MODE,
    DEFAULT_POST_MOLT_FAST_DAYS,
    DEFAULT_STALE_MINUTES,
    DEVELOPMENT,
    DOMAIN,
    GROUPS,
    HABITATS,
    KINDS,
    LIGHT_MODES,
    ORIGINS,
    SENSOR_KEYS,
    SEXES,
    STAGES,
    SUBENTRY_ANIMAL,
    TUNING_DEFAULTS,
    TUNING_KEYS,
)
from .db import SpeciesExistsError


def _select(options: list[str], key: str) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options, translation_key=key, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


def _number(minimum: float, maximum: float, step: float = 1, unit: str | None = None):
    config = selector.NumberSelectorConfig(
        min=minimum, max=maximum, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


def _suggested(defaults: dict[str, Any], key: str) -> dict[str, Any]:
    value = defaults.get(key)
    return {"suggested_value": value} if value not in (None, "", []) else {}


# --- Hoofdentry -----------------------------------------------------------


class ArthropodaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Maakt de collectie aan (één per HA-installatie)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={},
                options={
                    CONF_DAY_START: DEFAULT_DAY_START,
                    CONF_DAY_END: DEFAULT_DAY_END,
                    CONF_POST_MOLT_FAST_DAYS: DEFAULT_POST_MOLT_FAST_DAYS,
                },
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default="Collectie"): str}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ArthropodaOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_ANIMAL: AnimalSubentryFlow}


# --- Opties: instellingen en soorten ---------------------------------------


class ArthropodaOptionsFlow(OptionsFlow):
    """Instellingen, soort toevoegen, caresheet importeren."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init", menu_options=["add_species", "import_caresheet", "settings"]
        )

    def _runtime(self):
        if self.config_entry.state is not ConfigEntryState.LOADED:
            return None
        return self.config_entry.runtime_data

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            options = {**self.config_entry.options, **user_input}
            if CONF_NOTIFY_TARGETS not in user_input:  # leeggemaakt
                options.pop(CONF_NOTIFY_TARGETS, None)
            return self.async_create_entry(data=options)
        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DAY_START, default=opts.get(CONF_DAY_START, DEFAULT_DAY_START)
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_DAY_END, default=opts.get(CONF_DAY_END, DEFAULT_DAY_END)
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_LIGHT_MODE, default=opts.get(CONF_LIGHT_MODE, DEFAULT_LIGHT_MODE)
                ): _select(LIGHT_MODES, "light_mode"),
                vol.Required(
                    CONF_POST_MOLT_FAST_DAYS,
                    default=opts.get(CONF_POST_MOLT_FAST_DAYS, DEFAULT_POST_MOLT_FAST_DAYS),
                ): _number(0, 60, 1, "d"),
                vol.Required(
                    CONF_STALE_MINUTES,
                    default=opts.get(CONF_STALE_MINUTES, DEFAULT_STALE_MINUTES),
                ): _number(0, 1440, 1, "min"),
                vol.Required(
                    CONF_ALARM_DELAY_MINUTES,
                    default=opts.get(CONF_ALARM_DELAY_MINUTES, DEFAULT_ALARM_DELAY_MINUTES),
                ): _number(0, 240, 1, "min"),
                vol.Optional(
                    CONF_NOTIFY_TARGETS,
                    description=_suggested(dict(opts), CONF_NOTIFY_TARGETS),
                ): selector.TextSelector(selector.TextSelectorConfig(multiple=True)),
                vol.Required(
                    CONF_DIGEST_ENABLED, default=opts.get(CONF_DIGEST_ENABLED, True)
                ): bool,
                vol.Required(
                    CONF_DIGEST_TIME, default=opts.get(CONF_DIGEST_TIME, DEFAULT_DIGEST_TIME)
                ): selector.TimeSelector(),
            }
        )
        return self.async_show_form(step_id="settings", data_schema=schema)

    async def _save(self, sheets: list[ParsedCaresheet], overwrite: bool) -> tuple[list, list]:
        runtime = self._runtime()
        saved, skipped = [], []
        for sheet in sheets:
            name = sheet.species["scientific_name"]
            try:
                await self.hass.async_add_executor_job(runtime.db.save_caresheet, sheet, overwrite)
                saved.append(name)
            except SpeciesExistsError:
                skipped.append(name)
        if saved:
            await runtime.coordinator.async_refresh()
        return saved, skipped

    async def async_step_add_species(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._runtime() is None:
            return self.async_abort(reason="not_loaded")
        errors: dict[str, str] = {}
        if user_input is not None:
            sheet = _sheet_from_form(user_input)
            if sheet is None:
                errors["base"] = "invalid_range"
            else:
                saved, _ = await self._save([sheet], overwrite=False)
                if saved:
                    return self.async_abort(
                        reason="species_added", description_placeholders={"names": saved[0]}
                    )
                errors["scientific_name"] = "species_exists"

        unit_t = UnitOfTemperature.CELSIUS
        schema = vol.Schema(
            {
                vol.Required("scientific_name"): str,
                vol.Optional("common_name_nl"): str,
                vol.Optional("common_name_en"): str,
                vol.Required("group", default="other"): _select(GROUPS, "group"),
                vol.Optional("development"): _select(DEVELOPMENT, "development"),
                vol.Optional("habitat"): _select(HABITATS, "habitat"),
                vol.Optional("feeder", default=False): bool,
                vol.Optional("temp_day_min"): _number(0, 45, 0.5, unit_t),
                vol.Optional("temp_day_max"): _number(0, 45, 0.5, unit_t),
                vol.Optional("temp_night_min"): _number(0, 45, 0.5, unit_t),
                vol.Optional("temp_night_max"): _number(0, 45, 0.5, unit_t),
                vol.Optional("humidity_min"): _number(0, 100, 1, PERCENTAGE),
                vol.Optional("humidity_max"): _number(0, 100, 1, PERCENTAGE),
                vol.Optional("water_temp_min"): _number(0, 40, 0.5, unit_t),
                vol.Optional("water_temp_max"): _number(0, 40, 0.5, unit_t),
                vol.Optional("feeding_interval_days"): _number(0, 120, 1, "d"),
                vol.Optional("cleaning_interval_days"): _number(0, 365, 1, "d"),
                vol.Optional("water_change_interval_days"): _number(0, 365, 1, "d"),
                vol.Optional("notes"): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
            }
        )
        return self.async_show_form(
            step_id="add_species",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def async_step_import_caresheet(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._runtime() is None:
            return self.async_abort(reason="not_loaded")
        errors: dict[str, str] = {}
        placeholders = {"error": ""}
        if user_input is not None:
            text = user_input.get("yaml", "")
            path = user_input.get("path") or looks_like_path(text)
            try:
                if path:
                    text = await self.hass.async_add_executor_job(
                        _read_config_file, self.hass.config.path(), path
                    )
                sheets = parse_caresheets(text)
            except (CaresheetError, OSError, ValueError) as err:
                errors["base"] = "invalid_caresheet"
                placeholders["error"] = str(err)
            else:
                saved, skipped = await self._save(sheets, user_input.get("overwrite", False))
                return self.async_abort(
                    reason="caresheets_imported",
                    description_placeholders={
                        "saved": ", ".join(saved) or "–",
                        "skipped": ", ".join(skipped) or "–",
                    },
                )

        schema = vol.Schema(
            {
                vol.Optional("yaml"): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                vol.Optional("path"): str,
                vol.Optional("overwrite", default=False): bool,
            }
        )
        return self.async_show_form(
            step_id="import_caresheet",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
            description_placeholders=placeholders,
        )


def _read_config_file(config_dir: str, relative: str) -> str:
    """Lees een bestand dat binnen de HA-configuratiemap moet liggen."""
    base = Path(config_dir).resolve()
    path = (base / relative.strip().removeprefix("/config/")).resolve()
    if base not in path.parents:
        raise ValueError("Het bestand moet in de Home Assistant-configuratiemap staan.")
    if not path.is_file():
        name = Path(relative).name
        # Beperkt zoeken (max. 3 mapniveaus diep) om een tip te geven.
        found = [p for depth in range(4) for p in base.glob("*/" * depth + name)]
        hits = [str(p.relative_to(base)).replace("\\", "/") for p in found][:3]
        hint = f" Gevonden op: {', '.join(hits)}" if hits else ""
        raise ValueError(f"Bestand '{relative}' niet gevonden in /config.{hint}")
    return path.read_text(encoding="utf-8")


def _sheet_from_form(data: dict[str, Any]) -> ParsedCaresheet | None:
    """Zet het formulier 'soort toevoegen' om naar een caresheet."""
    profile: dict[str, Any] = {}
    for key in ("temp_day", "temp_night", "humidity", "water_temp"):
        lo, hi = data.get(f"{key}_min"), data.get(f"{key}_max")
        if lo is None and hi is None:
            continue
        if lo is None or hi is None or lo > hi:
            return None
        profile[key] = [float(lo), float(hi)]
    for key in ("feeding_interval_days", "cleaning_interval_days", "water_change_interval_days"):
        if data.get(key):
            profile[key] = float(data[key])

    species: dict[str, Any] = {
        "scientific_name": data["scientific_name"].strip(),
        "common_names": {
            lang: data[f"common_name_{lang}"].strip()
            for lang in ("nl", "en")
            if data.get(f"common_name_{lang}")
        },
        "group": data.get("group", "other"),
    }
    for key in ("development", "habitat", "notes"):
        if data.get(key):
            species[key] = data[key]
    if data.get("feeder"):
        species["feeder"] = True
    return ParsedCaresheet(species=species, profiles=[profile] if profile else [], source="handmatig")


# --- Subentry: dier of kolonie ---------------------------------------------


class AnimalSubentryFlow(ConfigSubentryFlow):
    """Dier of kolonie toevoegen en wijzigen."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def _runtime(self):
        entry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return None
        return entry.runtime_data

    async def _animal_schema(self, defaults: dict[str, Any]) -> vol.Schema | None:
        runtime = self._runtime()
        species = await self.hass.async_add_executor_job(runtime.db.list_species)
        if not species:
            return None
        language = self.hass.config.language[:2]
        species_options = [
            selector.SelectOptionDict(value=str(s.id), label=s.display_name(language))
            for s in species
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_SPECIES_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=species_options, mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Required(CONF_KIND, default="individual"): _select(KINDS, "kind"),
                vol.Required(CONF_SEX, default="unknown"): _select(SEXES, "sex"),
                vol.Optional(CONF_STAGE): _select(STAGES, "stage"),
                vol.Optional(CONF_INSTAR): _number(0, 30),
                vol.Optional(CONF_COUNT): _number(0, 100000),
                vol.Optional(CONF_BORN_AT): selector.DateSelector(),
                vol.Optional(CONF_ACQUIRED_AT): selector.DateSelector(),
                vol.Optional(CONF_ORIGIN): _select(ORIGINS, "origin"),
            }
        )
        return self.add_suggested_values_to_schema(schema, defaults)

    @staticmethod
    def _sensor_schema(defaults: dict[str, Any]) -> vol.Schema:
        temp = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature", multiple=True)
        )
        hum = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="humidity")
        )
        water = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )
        return vol.Schema(
            {
                vol.Optional(
                    CONF_TEMPERATURE_SENSORS, description=_suggested(defaults, CONF_TEMPERATURE_SENSORS)
                ): temp,
                vol.Optional(
                    CONF_HUMIDITY_SENSOR, description=_suggested(defaults, CONF_HUMIDITY_SENSOR)
                ): hum,
                vol.Optional(
                    CONF_WATER_TEMPERATURE_SENSOR,
                    description=_suggested(defaults, CONF_WATER_TEMPERATURE_SENSOR),
                ): water,
                # Voedselplanten uit de plant monitor (domein plant.*)
                vol.Optional(
                    CONF_FOOD_PLANTS, description=_suggested(defaults, CONF_FOOD_PLANTS)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="plant", multiple=True)
                ),
            }
        )

    @staticmethod
    def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
        data = dict(user_input)
        for key in (CONF_INSTAR, CONF_COUNT):
            if data.get(key) is not None:
                data[key] = int(data[key])
        return data

    # Toevoegen

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if self._runtime() is None:
            return self.async_abort(reason="not_loaded")
        if user_input is not None:
            self._data = self._clean(user_input)
            return await self.async_step_sensors()
        schema = await self._animal_schema({})
        if schema is None:
            return self.async_abort(reason="no_species")
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_sensors(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_actuators()
        return self.async_show_form(step_id="sensors", data_schema=self._sensor_schema({}))

    async def async_step_actuators(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            if any(user_input.get(k) for k in ACTUATOR_KEYS):
                return await self.async_step_control()
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)
        return self.async_show_form(step_id="actuators", data_schema=self._actuator_schema({}))

    async def async_step_control(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)
        return self.async_show_form(
            step_id="control", data_schema=self._control_schema(TUNING_DEFAULTS, self._data)
        )

    @staticmethod
    def _actuator_schema(defaults: dict[str, Any]) -> vol.Schema:
        def entity(domains: list[str], multiple: bool = False) -> selector.EntitySelector:
            return selector.EntitySelector(
                selector.EntitySelectorConfig(domain=domains, multiple=multiple)
            )

        fields = {
            CONF_HEATER: entity(["switch", "light", "climate", "input_boolean"]),
            CONF_MISTER: entity(["switch", "script", "input_boolean"]),
            CONF_LIGHTS: entity(["switch", "light", "input_boolean"], multiple=True),
            CONF_FAN: entity(["switch", "fan", "input_boolean"]),
            CONF_WATER_HEATER: entity(["switch", "climate", "input_boolean"]),
            CONF_PUMPS: entity(["switch", "input_boolean"], multiple=True),
        }
        return vol.Schema(
            {
                vol.Optional(key, description=_suggested(defaults, key)): sel
                for key, sel in fields.items()
            }
        )

    @staticmethod
    def _control_schema(defaults: dict[str, Any], data: dict[str, Any]) -> vol.Schema:
        """Afstelling; alleen velden voor de gekozen actuatoren."""
        fields: dict[str, Any] = {}
        if data.get(CONF_HEATER) or data.get(CONF_WATER_HEATER):
            fields[CONF_HYSTERESIS] = _number(0.1, 5, 0.1, UnitOfTemperature.CELSIUS)
        if data.get(CONF_MISTER):
            fields[CONF_MIST_SECONDS] = _number(1, 600, 1, "s")
            fields[CONF_MIST_PAUSE_MINUTES] = _number(1, 1440, 1, "min")
            fields[CONF_MIST_MAX_PER_DAY] = _number(0, 100)
            fields[CONF_MIST_TIMES] = str
        if data.get(CONF_LIGHTS):
            fields[CONF_LIGHT_RAMP_MINUTES] = _number(0, 180, 1, "min")
        schema = {}
        for key, sel in fields.items():
            if key == CONF_MIST_TIMES:
                schema[vol.Optional(key, description=_suggested(defaults, key))] = sel
            else:
                schema[vol.Required(key, default=defaults.get(key, TUNING_DEFAULTS[key]))] = sel
        return vol.Schema(schema)

    # Wijzigen

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        runtime = self._runtime()
        if runtime is None:
            return self.async_abort(reason="not_loaded")
        subentry = self._get_reconfigure_subentry()
        animal = await self.hass.async_add_executor_job(runtime.db.get_animal, subentry.subentry_id)

        if user_input is not None:
            # Ook velden die alleen het paneel kent (stamboom, herkomst) behouden.
            keep = (
                *SENSOR_KEYS, *ACTUATOR_KEYS, *TUNING_KEYS,
                "mother_id", "father_id", "generation", "brood_id", "seller", "price",
            )
            self._data = {
                **{k: v for k, v in subentry.data.items() if k in keep},
                **self._clean(user_input),
            }
            if animal is not None:
                # Dynamische velden staan in de database (het dagboek past ze aan).
                await runtime.coordinator.async_update_animal(
                    subentry.subentry_id,
                    sex=self._data.get(CONF_SEX, "unknown"),
                    stage=self._data.get(CONF_STAGE),
                    instar=self._data.get(CONF_INSTAR),
                    count=self._data.get(CONF_COUNT),
                )
            return await self.async_step_reconfigure_sensors()

        defaults = dict(subentry.data)
        if animal is not None:
            defaults.update(
                {
                    CONF_SEX: animal.sex,
                    CONF_STAGE: animal.stage,
                    CONF_INSTAR: animal.instar,
                    CONF_COUNT: animal.count,
                }
            )
        schema = await self._animal_schema(defaults)
        if schema is None:
            return self.async_abort(reason="no_species")
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    async def async_step_reconfigure_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            # Sensoren die leeggemaakt werden, ook echt verwijderen.
            self._data = {k: v for k, v in self._data.items() if k not in SENSOR_KEYS}
            self._data.update(user_input)
            return await self.async_step_reconfigure_actuators()
        return self.async_show_form(
            step_id="reconfigure_sensors", data_schema=self._sensor_schema(self._data)
        )

    async def async_step_reconfigure_actuators(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        current = self._get_reconfigure_subentry().data
        if user_input is not None:
            self._data = {k: v for k, v in self._data.items() if k not in ACTUATOR_KEYS}
            self._data.update(user_input)
            if any(user_input.get(k) for k in ACTUATOR_KEYS):
                return await self.async_step_reconfigure_control()
            return self._finish_reconfigure()
        return self.async_show_form(
            step_id="reconfigure_actuators", data_schema=self._actuator_schema(dict(current))
        )

    async def async_step_reconfigure_control(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        current = dict(self._get_reconfigure_subentry().data)
        if user_input is not None:
            self._data = {k: v for k, v in self._data.items() if k not in TUNING_KEYS}
            self._data.update(user_input)
            return self._finish_reconfigure()
        return self.async_show_form(
            step_id="reconfigure_control",
            data_schema=self._control_schema({**TUNING_DEFAULTS, **current}, self._data),
        )

    def _finish_reconfigure(self) -> SubentryFlowResult:
        # Klimaat- en sensorgegevens komen uit _data; vorige waarden van de
        # rest (bv. afstelling zonder actuatoren) worden niet meegenomen.
        return self.async_update_and_abort(
            self._get_entry(),
            self._get_reconfigure_subentry(),
            title=self._data[CONF_NAME],
            data=self._data,
        )
