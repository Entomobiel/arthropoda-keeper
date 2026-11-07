"""Acties (services): dagboek, metingen, caresheets."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.util import dt as dt_util

from .caresheet import CaresheetError, dump_documents, looks_like_path, parse_caresheets
from .const import DOMAIN, SEXES, STAGES
from .db import SpeciesExistsError
from .journal import ENTRY_TYPES
from .tasks import TASK_KINDS

ATTR_ANIMAL = "animal"
ATTR_TYPE = "type"
ATTR_TIMESTAMP = "timestamp"
ATTR_NOTES = "notes"
ATTR_DATA = "data"

_BASE = {
    vol.Required(ATTR_ANIMAL): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_TIMESTAMP): cv.datetime,
    vol.Optional(ATTR_NOTES): cv.string,
}

LOG_ENTRY_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Required(ATTR_TYPE): vol.In(list(ENTRY_TYPES)),
        vol.Optional(ATTR_DATA, default={}): dict,
    }
)

LOG_FEEDING_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Optional("prey"): cv.string,
        vol.Optional("quantity"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("prey_size"): cv.string,
        vol.Optional("plants"): cv.entity_ids,
        vol.Optional("result", default="accepted"): vol.In(["accepted", "partial", "refused"]),
    }
)

LOG_MOLT_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Optional("complete", default=True): cv.boolean,
        vol.Optional("instar_after"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("sex"): vol.In(SEXES),
        vol.Optional("exuvia_kept"): cv.boolean,
        vol.Optional("legspan_mm"): vol.Coerce(float),
        vol.Optional("length_mm"): vol.Coerce(float),
    }
)

ADD_MEASUREMENT_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Optional("length_mm"): vol.Coerce(float),
        vol.Optional("legspan_mm"): vol.Coerce(float),
        vol.Optional("weight_g"): vol.Coerce(float),
        vol.Optional("count"): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)

SET_STAGE_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Required("stage"): vol.In(STAGES),
        vol.Optional("instar"): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)

GET_JOURNAL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ANIMAL): cv.string,
        vol.Optional(ATTR_TYPE): vol.In(list(ENTRY_TYPES)),
        vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=1000)),
    }
)

IMPORT_SCHEMA = vol.Schema(
    {
        vol.Exclusive("yaml", "source"): cv.string,
        vol.Exclusive("path", "source"): cv.string,
        vol.Optional("overwrite", default=False): cv.boolean,
    }
)

SNOOZE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ANIMAL): cv.string,
        vol.Required("task"): vol.In(list(TASK_KINDS)),
        vol.Optional("days", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
    }
)

EXPORT_SCHEMA = vol.Schema(
    {
        vol.Optional("species"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("path"): cv.string,
    }
)


def _runtime(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")


def _animal_ids(hass: HomeAssistant, device_ids: list[str]) -> list[str]:
    registry = dr.async_get(hass)
    ids: list[str] = []
    for device_id in device_ids:
        device = registry.async_get(device_id)
        found = [ident for dom, ident in device.identifiers if dom == DOMAIN] if device else []
        if not found:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_animal",
                translation_placeholders={"device": device_id},
            )
        ids.extend(found)
    return ids


def _timestamp(value: datetime | None) -> datetime:
    if value is None:
        return dt_util.utcnow()
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_utc(value)


def _config_path(hass: HomeAssistant, relative: str) -> Path:
    base = Path(hass.config.path()).resolve()
    path = (base / relative.removeprefix("/config/")).resolve()
    if base not in path.parents:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="path_outside_config")
    return path


async def _log(hass: HomeAssistant, call: ServiceCall, entry_type: str, data: dict) -> ServiceResponse:
    runtime = _runtime(hass)
    ids = _animal_ids(hass, call.data[ATTR_ANIMAL])
    clean = {k: v for k, v in data.items() if v is not None}
    try:
        entry_ids = await runtime.coordinator.async_log(
            ids,
            entry_type,
            _timestamp(call.data.get(ATTR_TIMESTAMP)),
            call.data.get(ATTR_NOTES),
            clean,
        )
    except ValueError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_entry",
            translation_placeholders={"error": str(err)},
        ) from err
    return {"entry_ids": entry_ids}


def _extra(call: ServiceCall) -> dict[str, Any]:
    """Alle velden behalve de algemene (dier, tijd, notities)."""
    return {k: v for k, v in call.data.items() if k not in (ATTR_ANIMAL, ATTR_TIMESTAMP, ATTR_NOTES)}


def async_setup_services(hass: HomeAssistant) -> None:
    """Registreer alle acties."""

    async def log_entry(call: ServiceCall) -> ServiceResponse:
        return await _log(hass, call, call.data[ATTR_TYPE], call.data[ATTR_DATA])

    async def log_feeding(call: ServiceCall) -> ServiceResponse:
        data = _extra(call)
        entry_type = "feeding_refused" if data.get("result") == "refused" else "feeding"
        return await _log(hass, call, entry_type, data)

    async def log_molt(call: ServiceCall) -> ServiceResponse:
        data = _extra(call)
        entry_type = "molt" if data.get("complete", True) else "molt_problem"
        return await _log(hass, call, entry_type, data)

    async def add_measurement(call: ServiceCall) -> ServiceResponse:
        data = _extra(call)
        if not data:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_values")
        entry_type = "count" if set(data) == {"count"} else "measurement"
        return await _log(hass, call, entry_type, data)

    async def set_stage(call: ServiceCall) -> ServiceResponse:
        return await _log(hass, call, "stage_change", _extra(call))

    async def get_journal(call: ServiceCall) -> ServiceResponse:
        runtime = _runtime(hass)
        animal_id = None
        if call.data.get(ATTR_ANIMAL):
            animal_id = _animal_ids(hass, [call.data[ATTR_ANIMAL]])[0]
        entries = await hass.async_add_executor_job(
            runtime.db.get_journal, animal_id, call.data["limit"], call.data.get(ATTR_TYPE)
        )
        return {"entries": entries}

    async def import_caresheet(call: ServiceCall) -> ServiceResponse:
        runtime = _runtime(hass)
        text = call.data.get("yaml")
        relative = call.data.get("path") or looks_like_path(text)
        if relative:
            path = _config_path(hass, relative)
            try:
                text = await hass.async_add_executor_job(path.read_text, "utf-8")
            except OSError as err:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_caresheet",
                    translation_placeholders={"error": f"{relative}: {err.strerror}"},
                ) from err
        if not text:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_caresheet")
        try:
            sheets = parse_caresheets(text)
        except CaresheetError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_caresheet",
                translation_placeholders={"error": str(err)},
            ) from err
        saved, skipped = [], []
        for sheet in sheets:
            try:
                await hass.async_add_executor_job(
                    runtime.db.save_caresheet, sheet, call.data["overwrite"]
                )
                saved.append(sheet.species["scientific_name"])
            except SpeciesExistsError:
                skipped.append(sheet.species["scientific_name"])
        if saved:
            await runtime.coordinator.async_refresh()
        return {"imported": saved, "skipped_existing": skipped}

    async def export_species(call: ServiceCall) -> ServiceResponse:
        runtime = _runtime(hass)
        species_ids = None
        if call.data.get("species"):
            all_species = await hass.async_add_executor_job(runtime.db.list_species)
            wanted = {n.strip().lower() for n in call.data["species"]}
            species_ids = [s.id for s in all_species if s.scientific_name.lower() in wanted]
        docs = await hass.async_add_executor_job(runtime.db.export_species, species_ids)
        text = dump_documents(docs)
        if call.data.get("path"):
            path = _config_path(hass, call.data["path"])

            def _write() -> None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            await hass.async_add_executor_job(_write)
        return {"count": len(docs), "yaml": text}

    async def list_species(call: ServiceCall) -> ServiceResponse:
        runtime = _runtime(hass)
        species = await hass.async_add_executor_job(runtime.db.list_species)
        return {
            "species": [
                {
                    "scientific_name": s.scientific_name,
                    "common_names": s.common_names,
                    "group": s.group,
                    "source": s.source,
                }
                for s in species
            ]
        }

    async def send_digest(call: ServiceCall) -> ServiceResponse:
        sent = await _runtime(hass).digest.async_send()
        return {"sent": sent}

    async def snooze_task(call: ServiceCall) -> ServiceResponse:
        runtime = _runtime(hass)
        animal_id = _animal_ids(hass, [call.data[ATTR_ANIMAL]])[0]
        until = dt_util.start_of_local_day() + timedelta(days=call.data["days"])
        await runtime.coordinator.async_snooze(animal_id, call.data["task"], until)
        return {"until": until.isoformat()}

    hass.services.async_register(
        DOMAIN, "send_digest", send_digest, schema=vol.Schema({}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, "snooze_task", snooze_task, schema=SNOOZE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    optional = SupportsResponse.OPTIONAL
    only = SupportsResponse.ONLY
    for name, handler, schema, response in (
        ("log_entry", log_entry, LOG_ENTRY_SCHEMA, optional),
        ("log_feeding", log_feeding, LOG_FEEDING_SCHEMA, optional),
        ("log_molt", log_molt, LOG_MOLT_SCHEMA, optional),
        ("add_measurement", add_measurement, ADD_MEASUREMENT_SCHEMA, optional),
        ("set_stage", set_stage, SET_STAGE_SCHEMA, optional),
        ("get_journal", get_journal, GET_JOURNAL_SCHEMA, only),
        ("import_caresheet", import_caresheet, IMPORT_SCHEMA, optional),
        ("export_species", export_species, EXPORT_SCHEMA, optional),
        ("list_species", list_species, vol.Schema({}), only),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=schema, supports_response=response)
