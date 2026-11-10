"""WebSocket-API voor het zijbalkpaneel en de dashboardkaarten.

Commando's (allemaal `arthropoda/...`):
  subscribe              live lijst van alle dieren (bij elke wijziging opnieuw)
  animals                dezelfde lijst, eenmalig
  meta                   labels (handelingen, fases, ...) in de taal van de gebruiker
  animal/add             nieuw dier (maakt een subentry aan)
  animal/update          dier wijzigen (subentry + dynamische velden)
  journal/list|add|delete
  species/list|get|save|delete
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util

from .ai_import import ImportFailed, ai_entities, async_extract, async_inat_photos
from .caresheet import CaresheetError, dump_documents, parse_caresheets
from .http_views import document_dir, photo_dir
from .nfc import EVENT_TAG_SCANNED, deep_link
from .const import (
    ACTUATOR_KEYS,
    CONF_COUNT,
    CONF_INSTAR,
    CONF_REQUIRE_SCAN,
    CONF_SEX,
    CONF_SPECIES_ID,
    CONF_STAGE,
    DOMAIN,
    INITIAL_FIELDS_UI,
    KINDS,
    MULTI_ACTUATOR_KEYS,
    ORIGINS,
    SENSOR_KEYS,
    SEXES,
    SIGNAL_UPDATE,
    STAGES,
    SUBENTRY_ANIMAL,
    TUNING_KEYS,
)
from .db import SpeciesExistsError
from .journal import ENTRY_TYPES
from .plants import (
    CONF_LIGHT_HOURS,
    CONF_PLANT_CLIMATE,
    CONF_PLANTS,
    PLANT_ENTRY_TYPES,
    plant_info,
)

EVENT_PLANT_ENTRY = "arthropoda_plant_entry"

STATIC_UI_KEYS = (
    CONF_NAME, CONF_SPECIES_ID, "kind", "born_at", "acquired_at", "origin",
    # stamboom en herkomst (fase 6)
    "mother_id", "father_id", "generation", "brood_id", "seller", "price",
)
ALLOWED_KEYS = {*STATIC_UI_KEYS, *INITIAL_FIELDS_UI, *SENSOR_KEYS, *ACTUATOR_KEYS, *TUNING_KEYS}


# --- hulpfuncties ----------------------------------------------------------


def _runtime(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry, entry.runtime_data
    return None, None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _entity_ids(hass: HomeAssistant, animal_id: str) -> dict[str, str]:
    """Entiteits-ID's van een dier (op basis van unique_id → werkt na hernoemen)."""
    registry = er.async_get(hass)
    result = {}
    for platform, key in (
        ("sensor", "status"),
        ("sensor", "temperature"),
        ("sensor", "humidity"),
        ("sensor", "water_temperature"),
        ("sensor", "climate_control_status"),
        ("switch", "climate_control"),
        ("switch", "maintenance"),
        ("select", "season_mode"),
        ("image", "photo"),
        ("binary_sensor", "problem"),
    ):
        entity_id = registry.async_get_entity_id(platform, DOMAIN, f"{animal_id}_{key}")
        if entity_id:
            result[key] = entity_id
    return result


def serialize_animals(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Alle dieren in een vorm die de frontend kan tonen."""
    entry, runtime = _runtime(hass)
    if runtime is None:
        return []
    coordinator, controller = runtime.coordinator, runtime.controller
    registry = er.async_get(hass)
    animals = []
    for animal_id, snap in (coordinator.data or {}).items():
        animal, species = snap.animal, snap.bundle.species
        entities = _entity_ids(hass, animal_id)
        status_entry = registry.async_get(entities["status"]) if "status" in entities else None
        if not snap.monitored:
            state = "inactive"
        else:
            state = "problem" if snap.problems else "ok"
        climate_status = "monitoring"
        if snap.has_actuators:
            climate_status = "active" if snap.climate_enabled and snap.monitored else "paused"
        if controller.maintenance_active(animal_id):
            climate_status = "maintenance"
        animals.append(
            {
                "id": animal_id,
                "name": animal.name,
                "kind": animal.kind,
                "sex": animal.sex,
                "stage": animal.stage,
                "instar": animal.instar,
                "count": animal.count,
                "status": animal.status,
                "season_mode": animal.season_mode,
                "season": snap.season,
                "premolt": animal.premolt,
                "can_molt": snap.can_molt,
                "acquired_at": animal.acquired_at,
                "born_at": animal.born_at,
                "origin": animal.origin,
                "species": (
                    {
                        "id": species.id,
                        "scientific_name": species.scientific_name,
                        "common_names": species.common_names,
                        "group": species.group,
                        "development": species.development,
                        "habitat": species.habitat,
                        "feeder": bool(species.info.get("feeder")),
                        "diapause": species.info.get("diapause"),
                    }
                    if species
                    else None
                ),
                "diapause": snap.diapause,
                "state": state,
                "problems": snap.problems,
                "is_day": snap.is_day,
                "feeding_paused": snap.feeding_paused,
                "readings": {
                    "temperature": snap.readings.temperature,
                    "temperatures": snap.readings.temperatures,
                    "humidity": snap.readings.humidity,
                    "water_temperature": snap.readings.water_temperature,
                    "unavailable": snap.readings.unavailable,
                },
                "targets": {
                    "temperature": snap.target_temperature,
                    "humidity": snap.values.get("humidity"),
                    "water_temperature": snap.values.get("water_temp"),
                },
                "profile": snap.values,
                "days_since": snap.days_since,
                "molt_count": snap.bundle.molt_count,
                "measurements": {
                    kind: {"value": m.value, "unit": m.unit, "ts": _iso(m.ts)}
                    for kind, m in snap.bundle.measurements.items()
                },
                "tasks": [
                    {"kind": t.kind, "due": _iso(t.due), "uid": t.uid} for t in snap.tasks
                ],
                "next_feeding": _iso(snap.next_feeding),
                "next_molt": _iso(snap.next_molt),
                "climate": {
                    "status": climate_status,
                    "maintenance_until": _iso(controller.maintenance_until(animal_id)),
                    "actuators": [
                        r.as_dict() for r in controller.results.values() if animal_id in r.members
                    ],
                },
                # Eigen configuratie (voor het wijzigformulier) en het klimaat dat
                # echt gebruikt wordt (eventueel dat van de kast).
                "config": dict(coordinator.animal_configs.get(animal_id, {})),
                "climate_config": dict(snap.config),
                "enclosure_id": animal.enclosure_id,
                "device_id": status_entry.device_id if status_entry else None,
                "entities": entities,
            }
        )
    # Stamboom: ouders staan in de configuratie, kinderen worden afgeleid.
    by_id = {a["id"]: a for a in animals}
    for a in animals:
        cfg = a["config"]
        a["lineage"] = {
            "mother_id": cfg.get("mother_id"),
            "father_id": cfg.get("father_id"),
            "generation": cfg.get("generation"),
            "brood_id": cfg.get("brood_id"),
            "children": [],
        }
    for a in animals:
        for parent_key in ("mother_id", "father_id"):
            parent = by_id.get(a["lineage"][parent_key])
            if parent is not None:
                parent["lineage"]["children"].append(a["id"])
    animals.sort(key=lambda a: a["name"].lower())
    return animals


def serialize_enclosures(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Alle kasten met bewoners, taken en klimaat (voor paneel en werkscherm)."""
    _, runtime = _runtime(hass)
    if runtime is None:
        return []
    coordinator, controller, nag = runtime.coordinator, runtime.controller, runtime.nag
    data = coordinator.data or {}
    tasks_by_enc: dict[int, list[dict[str, Any]]] = {}
    for task in coordinator.enclosure_tasks:
        tasks_by_enc.setdefault(task.enclosure_id, []).append(
            {"uid": task.uid, "kind": task.kind, "due": _iso(task.due), "label": task.label}
        )
    result = []
    for enc_id, enc in sorted(coordinator.enclosures.items(), key=lambda kv: kv[1]["code"].lower()):
        residents = coordinator.residents(enc_id, monitored_only=False)
        active = [a for a in residents if a in data and data[a].monitored]
        readings = coordinator.enclosure_readings(enc_id)
        plants = []
        for entity_id in (enc.get("config") or {}).get(CONF_PLANTS) or []:
            info = plant_info(hass, entity_id)
            info["last"] = coordinator.plant_last.get(entity_id, {})
            plants.append(info)
        plant_cabinet = coordinator.plant_cabinet(enc_id)
        member_prefix = f"plant:{enc_id}:"
        result.append(
            {
                **{k: v for k, v in enc.items() if k != "config"},
                "config": {k: v for k, v in (enc.get("config") or {}).items() if k != "snooze"},
                "residents": active,
                "former_residents": [a for a in residents if a not in active],
                "empty": not active,
                "tasks": sorted(tasks_by_enc.get(enc_id, []), key=lambda t: t["due"]),
                "too_small_for": [
                    data[a].animal.name for a in active if "enclosure_too_small" in data[a].problems
                ],
                "readings": (
                    {
                        "temperature": readings.temperature,
                        "humidity": readings.humidity,
                        "water_temperature": readings.water_temperature,
                    }
                    if readings
                    else None
                ),
                # Scanbewijs: recent gescand (taken over tijd mogen dan afgevinkt worden).
                "scan": (
                    {
                        "required": bool(nag.enabled and nag.opt(CONF_REQUIRE_SCAN) and nag.verifiable(enc_id)),
                        "recent": nag.scanned_recently(enc_id),
                    }
                    if nag is not None
                    else None
                ),
                "plants": plants,
                # Planten sturen het klimaat (alleen zonder dieren in de kast).
                "plant_cabinet": plant_cabinet,
                "actuators": [
                    r.as_dict() for r in controller.results.values()
                    if plant_cabinet and any(str(m).startswith(member_prefix) for m in r.members)
                ],
                "link": deep_link(enc["code"]),
            }
        )
    return result


def _error(connection, msg, code: str, message: str) -> None:
    connection.send_error(msg["id"], code, message)


def _require(hass, connection, msg):
    entry, runtime = _runtime(hass)
    if runtime is None:
        _error(connection, msg, "not_loaded", "Arthropoda Keeper is niet geladen")
    return entry, runtime


# --- dieren -----------------------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): "arthropoda/subscribe"})
@callback
def ws_subscribe(hass: HomeAssistant, connection, msg) -> None:
    """Stuurt de lijst met dieren bij elke wijziging (ook na herladen)."""

    @callback
    def push() -> None:
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {"animals": serialize_animals(hass), "enclosures": serialize_enclosures(hass)},
            )
        )

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_UPDATE, push)
    connection.send_result(msg["id"])
    push()


@websocket_api.websocket_command({vol.Required("type"): "arthropoda/animals"})
@callback
def ws_animals(hass: HomeAssistant, connection, msg) -> None:
    connection.send_result(msg["id"], {"animals": serialize_animals(hass)})


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/meta", vol.Optional("language"): str}
)
@websocket_api.async_response
async def ws_meta(hass: HomeAssistant, connection, msg) -> None:
    """Labels voor keuzelijsten, in de taal van de gebruiker."""
    language = msg.get("language") or hass.config.language
    translations = await async_get_translations(hass, language, "selector", {DOMAIN})
    prefix = f"component.{DOMAIN}.selector."
    labels: dict[str, dict[str, str]] = {}
    for key, value in translations.items():
        if key.startswith(prefix):
            group, _, option = key[len(prefix):].partition(".options.")
            labels.setdefault(group, {})[option] = value
    entry, _ = _runtime(hass)
    connection.send_result(
        msg["id"],
        {
            "labels": labels,
            "entry_types": [{"type": t, "category": c} for t, c in ENTRY_TYPES.items()],
            "stages": STAGES,
            "sexes": SEXES,
            "kinds": KINDS,
            "origins": ORIGINS,
            "entry_id": entry.entry_id if entry else None,
            "collection": entry.title if entry else None,
        },
    )


def _clean_animal_data(data: dict[str, Any]) -> dict[str, Any]:
    """Alleen gekende velden, lege waarden weg, getallen als getal."""
    clean: dict[str, Any] = {}
    for key, value in data.items():
        if key not in ALLOWED_KEYS or value in (None, "", []):
            continue
        if key in (CONF_INSTAR, CONF_COUNT):
            value = int(value)
        elif key in MULTI_ACTUATOR_KEYS or key in ("temperature_sensors", "food_plants"):
            value = [v for v in cv.ensure_list(value) if v]
        elif key in TUNING_KEYS and key != "mist_times":
            value = float(value)
        elif key in (CONF_SPECIES_ID, "brood_id"):
            value = str(value)
        elif key == "price":
            value = float(value)
        clean[key] = value
    return clean


ANIMAL_DATA = vol.Schema({str: vol.Any(str, int, float, list, None)})


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/animal/add", vol.Required("data"): ANIMAL_DATA}
)
@websocket_api.async_response
async def ws_animal_add(hass: HomeAssistant, connection, msg) -> None:
    entry, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    data = _clean_animal_data(msg["data"])
    if not data.get(CONF_NAME) or not data.get(CONF_SPECIES_ID):
        _error(connection, msg, "invalid", "Naam en soort zijn verplicht")
        return
    subentry = ConfigSubentry(
        data=data, subentry_type=SUBENTRY_ANIMAL, title=data[CONF_NAME], unique_id=None
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    connection.send_result(msg["id"], {"animal_id": subentry.subentry_id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/animal/update",
        vol.Required("animal_id"): str,
        vol.Required("data"): ANIMAL_DATA,
    }
)
@websocket_api.async_response
async def ws_animal_update(hass: HomeAssistant, connection, msg) -> None:
    """Dier wijzigen. Alle velden worden vervangen door wat meegestuurd wordt."""
    entry, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    subentry = entry.subentries.get(msg["animal_id"])
    if subentry is None:
        _error(connection, msg, "not_found", "Onbekend dier")
        return
    data = _clean_animal_data(msg["data"])
    if not data.get(CONF_NAME) or not data.get(CONF_SPECIES_ID):
        _error(connection, msg, "invalid", "Naam en soort zijn verplicht")
        return
    # Dynamische velden: ook in de database (het dagboek past ze verder aan).
    await runtime.coordinator.async_update_animal(
        msg["animal_id"],
        sex=data.get(CONF_SEX, "unknown"),
        stage=data.get(CONF_STAGE),
        instar=data.get(CONF_INSTAR),
        count=data.get(CONF_COUNT),
    )
    hass.config_entries.async_update_subentry(entry, subentry, data=data, title=data[CONF_NAME])
    connection.send_result(msg["id"])


# --- dagboek ----------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/journal/list",
        vol.Optional("animal_id"): str,
        vol.Optional("entry_type"): str,
        vol.Optional("limit", default=100): vol.All(int, vol.Range(min=1, max=2000)),
    }
)
@websocket_api.async_response
async def ws_journal_list(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    entries = await hass.async_add_executor_job(
        runtime.db.get_journal, msg.get("animal_id"), msg["limit"], msg.get("entry_type")
    )
    connection.send_result(msg["id"], {"entries": entries})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/journal/add",
        vol.Required("animal_ids"): [str],
        vol.Required("entry_type"): vol.In(list(ENTRY_TYPES)),
        vol.Optional("timestamp"): str,
        vol.Optional("notes"): vol.Any(str, None),
        vol.Optional("data", default={}): dict,
    }
)
@websocket_api.async_response
async def ws_journal_add(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    ts = None
    if msg.get("timestamp"):
        ts = dt_util.parse_datetime(msg["timestamp"])
        if ts is None:
            _error(connection, msg, "invalid", "Ongeldig tijdstip")
            return
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=dt_util.get_default_time_zone())
    try:
        ids = await runtime.coordinator.async_log(
            msg["animal_ids"], msg["entry_type"], ts, msg.get("notes") or None, msg["data"]
        )
    except (ValueError, KeyError) as err:
        _error(connection, msg, "invalid", str(err))
        return
    connection.send_result(msg["id"], {"entry_ids": ids})


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/journal/delete", vol.Required("entry_id"): int}
)
@websocket_api.async_response
async def ws_journal_delete(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    deleted = await hass.async_add_executor_job(runtime.db.delete_entry, msg["entry_id"])
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"], {"deleted": deleted})


# --- soorten ----------------------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): "arthropoda/species/list"})
@websocket_api.async_response
async def ws_species_list(hass: HomeAssistant, connection, msg) -> None:
    entry, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    species = await hass.async_add_executor_job(runtime.db.list_species)
    used: dict[str, list[str]] = {}
    for sub in entry.subentries.values():
        used.setdefault(str(sub.data.get(CONF_SPECIES_ID)), []).append(sub.title)
    connection.send_result(
        msg["id"],
        {
            "species": [
                {
                    "id": s.id,
                    "scientific_name": s.scientific_name,
                    "common_names": s.common_names,
                    "group": s.group,
                    "development": s.development,
                    "habitat": s.habitat,
                    "source": s.source,
                    "feeder": bool(s.info.get("feeder")),
                    "photo": s.info.get("photo"),
                    "used_by": used.get(str(s.id), []),
                }
                for s in species
            ]
        },
    )


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/species/get", vol.Required("species_id"): int}
)
@websocket_api.async_response
async def ws_species_get(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    docs = await hass.async_add_executor_job(runtime.db.export_species, [msg["species_id"]])
    if not docs:
        _error(connection, msg, "not_found", "Onbekende soort")
        return
    connection.send_result(msg["id"], {"caresheet": docs[0], "yaml": dump_documents(docs)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/species/save",
        vol.Required("yaml"): str,
        vol.Optional("overwrite", default=False): bool,
        # Bestaande soort bijwerken (ook bij een nieuwe naam) in plaats van op naam te zoeken.
        vol.Optional("species_id"): vol.Any(int, None),
    }
)
@websocket_api.async_response
async def ws_species_save(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    try:
        sheets = parse_caresheets(msg["yaml"])
    except CaresheetError as err:
        _error(connection, msg, "invalid_caresheet", str(err))
        return
    species_id = msg.get("species_id")
    if species_id is not None and len(sheets) != 1:
        _error(connection, msg, "invalid", "Bij het bewerken van een soort hoort precies één caresheet.")
        return
    saved, skipped = [], []
    for sheet in sheets:
        try:
            await hass.async_add_executor_job(
                runtime.db.save_caresheet, sheet, msg["overwrite"], species_id
            )
            saved.append(sheet.species["scientific_name"])
        except SpeciesExistsError:
            if species_id is not None:
                _error(connection, msg, "exists",
                       f"Er bestaat al een andere soort met de naam {sheet.species['scientific_name']}.")
                return
            skipped.append(sheet.species["scientific_name"])
    if saved:
        await runtime.coordinator.async_refresh()
        hass.async_create_background_task(
            async_auto_species_photos(hass, runtime, saved), "arthropoda species photos"
        )
    connection.send_result(msg["id"], {"saved": saved, "skipped": skipped})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/species/delete",
        vol.Required("species_id"): int,
        # Dieren van deze soort eerst naar een andere soort verplaatsen.
        vol.Optional("reassign_to"): vol.Any(int, None),
    }
)
@websocket_api.async_response
async def ws_species_delete(hass: HomeAssistant, connection, msg) -> None:
    entry, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    in_use = [
        sub
        for sub in entry.subentries.values()
        if str(sub.data.get(CONF_SPECIES_ID)) == str(msg["species_id"])
    ]
    target = msg.get("reassign_to")
    if in_use and target is None:
        names = ", ".join(sub.title for sub in in_use)
        _error(connection, msg, "in_use", f"Soort in gebruik door: {names}")
        return
    if in_use:
        if target == msg["species_id"] or await hass.async_add_executor_job(
            runtime.db.get_species, target
        ) is None:
            _error(connection, msg, "invalid", "Kies een andere, bestaande soort.")
            return
        # Eerst alle databasewerk: een configuratiewijziging herlaadt de integratie
        # (en sluit dan de database), dus die komt pas helemaal op het einde.
        for sub in in_use:
            await hass.async_add_executor_job(
                lambda sid=sub.subentry_id: runtime.db.update_animal(sid, species_id=target)
            )
    deleted = await hass.async_add_executor_job(runtime.db.delete_species, msg["species_id"])
    moved = [sub.title for sub in in_use]
    for sub in in_use:
        hass.config_entries.async_update_subentry(
            entry, sub, data={**sub.data, CONF_SPECIES_ID: str(target)}
        )
    connection.send_result(msg["id"], {"deleted": deleted, "moved": moved})


# --- AI en foto's -------------------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): "arthropoda/ai/entities"})
@callback
def ws_ai_entities(hass: HomeAssistant, connection, msg) -> None:
    connection.send_result(msg["id"], {"entities": ai_entities(hass)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/caresheet/extract",
        vol.Optional("entity_id"): vol.Any(str, None),
        vol.Exclusive("url", "source"): str,
        vol.Exclusive("media_content_id", "source"): str,
        vol.Optional("source_name"): vol.Any(str, None),
        vol.Optional("hint"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_caresheet_extract(hass: HomeAssistant, connection, msg) -> None:
    """AI leest een caresheet; het resultaat wordt NIET opgeslagen (eerst nakijken)."""
    if not msg.get("url") and not msg.get("media_content_id"):
        _error(connection, msg, "invalid", "Geef een webadres of een bestand op.")
        return
    try:
        result = await async_extract(
            hass,
            entity_id=msg.get("entity_id") or None,
            url=msg.get("url"),
            media_content_id=msg.get("media_content_id"),
            source_name=msg.get("source_name"),
            hint=msg.get("hint"),
        )
    except ImportFailed as err:
        _error(connection, msg, "import_failed", str(err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/species/photo/search", vol.Required("species_id"): int}
)
@websocket_api.async_response
async def ws_species_photo_search(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    species = await hass.async_add_executor_job(runtime.db.get_species, msg["species_id"])
    if species is None:
        _error(connection, msg, "not_found", "Onbekende soort")
        return
    try:
        photos = await async_inat_photos(hass, species.scientific_name)
    except ImportFailed as err:
        _error(connection, msg, "import_failed", str(err))
        return
    connection.send_result(
        msg["id"], {"photos": photos, "current": species.info.get("photo")}
    )


PHOTO_SCHEMA = vol.Schema(
    {
        vol.Required("url"): vol.All(str, vol.Match(r"^https://")),
        vol.Optional("large_url"): str,
        vol.Optional("attribution"): str,
        vol.Optional("license"): str,
        vol.Optional("source_url"): str,
        vol.Optional("taxon"): vol.Any(str, None),
    },
    extra=vol.REMOVE_EXTRA,
)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/species/photo/set",
        vol.Required("species_id"): int,
        vol.Required("photo"): vol.Any(None, PHOTO_SCHEMA),
    }
)
@websocket_api.async_response
async def ws_species_photo_set(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    photo = msg["photo"]
    if photo:
        photo = {**photo, "set_at": dt_util.utcnow().isoformat()}
    await hass.async_add_executor_job(runtime.db.set_species_photo, msg["species_id"], photo)
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/animal/photo/delete", vol.Required("animal_id"): str}
)
@websocket_api.async_response
async def ws_animal_photo_delete(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    snap = (runtime.coordinator.data or {}).get(msg["animal_id"])
    if snap is None:
        _error(connection, msg, "not_found", "Onbekend dier")
        return
    photo = snap.animal.info.get("photo")
    if photo and photo.get("file"):
        path = photo_dir(hass) / photo["file"]
        await hass.async_add_executor_job(lambda: path.unlink(missing_ok=True))
    info = {k: v for k, v in snap.animal.info.items() if k != "photo"}
    await runtime.coordinator.async_update_animal(msg["animal_id"], info=info)
    connection.send_result(msg["id"])


async def async_auto_species_photos(hass: HomeAssistant, runtime, names: list[str]) -> None:
    """Nieuwe soorten zonder foto: eerste open-licentiefoto van iNaturalist nemen."""
    changed = False
    for name in names:
        species = await hass.async_add_executor_job(runtime.db.find_species, name)
        if species is None or species.info.get("photo"):
            continue
        try:
            photos = await async_inat_photos(hass, name, limit=1)
        except ImportFailed:
            continue
        if photos:
            photo = {**photos[0], "set_at": dt_util.utcnow().isoformat()}
            await hass.async_add_executor_job(runtime.db.set_species_photo, species.id, photo)
            changed = True
    if changed:
        await runtime.coordinator.async_refresh()


# --- kweek, voorraad, documenten, metingen (fase 6) -------------------------


@websocket_api.websocket_command({vol.Required("type"): "arthropoda/breeding/list"})
@websocket_api.async_response
async def ws_breeding_list(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return

    def _load():
        return runtime.db.list_broods(), runtime.db.list_pairings()

    broods, pairings = await hass.async_add_executor_job(_load)
    connection.send_result(msg["id"], {"broods": broods, "pairings": pairings})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/brood/update",
        vol.Required("brood_id"): int,
        vol.Optional("status"): vol.In(["incubating", "hatched", "failed"]),
        vol.Optional("count_hatched"): vol.Any(int, None),
        vol.Optional("count_laid"): vol.Any(int, None),
        vol.Optional("father_id"): vol.Any(str, None),
        vol.Optional("notes"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_brood_update(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    fields = {k: v for k, v in msg.items() if k not in ("type", "id", "brood_id")}
    if fields.get("status") == "hatched":
        fields.setdefault("hatched_at", dt_util.utcnow().isoformat(timespec="seconds"))
    await hass.async_add_executor_job(lambda: runtime.db.update_brood(msg["brood_id"], **fields))
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): "arthropoda/stock/list"})
@websocket_api.async_response
async def ws_stock_list(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    stock = await hass.async_add_executor_job(runtime.db.list_stock)
    connection.send_result(msg["id"], {"stock": stock})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/stock/save",
        vol.Required("item"): vol.Schema(
            {
                vol.Optional("id"): vol.Any(int, None),
                vol.Required("name"): vol.All(str, vol.Length(min=1)),
                vol.Optional("size"): vol.Any(str, None),
                vol.Optional("quantity"): vol.Any(int, float, None),
                vol.Optional("unit"): vol.Any(str, None),
                vol.Optional("min_quantity"): vol.Any(int, float, None),
                vol.Optional("colony_id"): vol.Any(str, None),
                vol.Optional("notes"): vol.Any(str, None),
            }
        ),
    }
)
@websocket_api.async_response
async def ws_stock_save(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    item = {k: (v if v != "" else None) for k, v in msg["item"].items()}
    stock_id = await hass.async_add_executor_job(runtime.db.save_stock, item)
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"], {"id": stock_id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/stock/adjust",
        vol.Required("stock_id"): int,
        vol.Required("delta"): vol.Any(int, float),
    }
)
@websocket_api.async_response
async def ws_stock_adjust(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    quantity = await hass.async_add_executor_job(runtime.db.adjust_stock, msg["stock_id"], msg["delta"])
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"], {"quantity": quantity})


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/stock/delete", vol.Required("stock_id"): int}
)
@websocket_api.async_response
async def ws_stock_delete(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    await hass.async_add_executor_job(runtime.db.delete_stock, msg["stock_id"])
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/documents/list", vol.Optional("animal_id"): vol.Any(str, None)}
)
@websocket_api.async_response
async def ws_documents_list(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    from homeassistant.components.http.auth import async_sign_path

    docs = await hass.async_add_executor_job(runtime.db.list_documents, msg.get("animal_id"))
    for doc in docs:
        doc["url"] = (
            async_sign_path(
                hass, f"/api/arthropoda/document/{doc['id']}", timedelta(hours=1),
                refresh_token_id=connection.refresh_token_id,
            )
            if doc.get("file")
            else None
        )
    connection.send_result(msg["id"], {"documents": docs})


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/documents/delete", vol.Required("document_id"): int}
)
@websocket_api.async_response
async def ws_documents_delete(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    doc = await hass.async_add_executor_job(runtime.db.delete_document, msg["document_id"])
    if doc and doc.get("file"):
        path = document_dir(hass) / doc["file"]
        await hass.async_add_executor_job(lambda: path.unlink(missing_ok=True))
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/measurements/list", vol.Required("animal_id"): str}
)
@websocket_api.async_response
async def ws_measurements_list(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    rows = await hass.async_add_executor_job(runtime.db.list_measurements, msg["animal_id"])
    snap = (runtime.coordinator.data or {}).get(msg["animal_id"])
    molts = [_iso(t) for t in snap.bundle.molt_times] if snap else []
    connection.send_result(msg["id"], {"measurements": rows, "molts": molts})


@websocket_api.websocket_command({vol.Required("type"): "arthropoda/species/photo/auto_all"})
@websocket_api.async_response
async def ws_species_photo_auto_all(hass: HomeAssistant, connection, msg) -> None:
    """Zoek een foto voor alle soorten die er nog geen hebben."""
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    species = await hass.async_add_executor_job(runtime.db.list_species)
    missing = [s.scientific_name for s in species if not s.info.get("photo")]
    await async_auto_species_photos(hass, runtime, missing)
    after = await hass.async_add_executor_job(runtime.db.list_species)
    found = [s.scientific_name for s in after if s.scientific_name in missing and s.info.get("photo")]
    connection.send_result(msg["id"], {"searched": len(missing), "found": found})


# --- kasten (fase 7) -----------------------------------------------------------

ENCLOSURE_SCHEMA = vol.Schema(
    {
        vol.Optional("id"): vol.Any(int, None),
        vol.Required("code"): vol.All(str, vol.Strip, vol.Length(min=1, max=20)),
        vol.Optional("name"): vol.Any(str, None),
        vol.Optional("type"): vol.Any(str, None),
        vol.Optional("length_cm"): vol.Any(int, float, None),
        vol.Optional("width_cm"): vol.Any(int, float, None),
        vol.Optional("height_cm"): vol.Any(int, float, None),
        vol.Optional("material"): vol.Any(str, None),
        vol.Optional("ventilation"): vol.Any(str, None),
        vol.Optional("location"): vol.Any(str, None),
        vol.Optional("acquired_at"): vol.Any(str, None),
        vol.Optional("price"): vol.Any(int, float, None),
        vol.Optional("seller"): vol.Any(str, None),
        vol.Optional("status"): vol.Any(str, None),
        vol.Optional("nfc_tag"): vol.Any(str, None),
        vol.Optional("notes"): vol.Any(str, None),
        vol.Optional("config"): dict,
        vol.Optional("equipment"): [
            vol.Schema(
                {
                    vol.Optional("name"): vol.Any(str, None),
                    vol.Optional("type"): vol.Any(str, None),
                    vol.Optional("interval_days"): vol.Any(int, float, None),
                    vol.Optional("serviced_at"): vol.Any(str, None),
                    vol.Optional("notes"): vol.Any(str, None),
                },
                extra=vol.REMOVE_EXTRA,
            )
        ],
    },
    extra=vol.REMOVE_EXTRA,
)


@websocket_api.websocket_command({vol.Required("type"): "arthropoda/enclosures/list"})
@callback
def ws_enclosures_list(hass: HomeAssistant, connection, msg) -> None:
    connection.send_result(msg["id"], {"enclosures": serialize_enclosures(hass)})


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/enclosure/save", vol.Required("item"): ENCLOSURE_SCHEMA}
)
@websocket_api.async_response
async def ws_enclosure_save(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    item = {k: (None if v == "" else v) for k, v in msg["item"].items()}
    if item.get("config") is not None:
        # Alleen klimaatvelden; lege waarden weglaten; snooze behouden.
        old = runtime.coordinator.enclosures.get(item.get("id") or -1, {}).get("config") or {}
        cfg = _clean_animal_data(item["config"])
        cfg = {k: v for k, v in cfg.items() if k in (*SENSOR_KEYS, *ACTUATOR_KEYS, *TUNING_KEYS)}
        raw = item["config"]
        plants = [e for e in cv.ensure_list(raw.get(CONF_PLANTS) or []) if str(e).startswith("plant.")]
        if plants:
            cfg[CONF_PLANTS] = plants
        if raw.get(CONF_LIGHT_HOURS) not in (None, ""):
            cfg[CONF_LIGHT_HOURS] = max(0.0, min(24.0, float(raw[CONF_LIGHT_HOURS])))
        if raw.get(CONF_PLANT_CLIMATE) is False:
            cfg[CONF_PLANT_CLIMATE] = False
        if old.get("snooze"):
            cfg["snooze"] = old["snooze"]
        item["config"] = cfg
    elif item.get("id") in runtime.coordinator.enclosures:
        item["config"] = runtime.coordinator.enclosures[item["id"]].get("config") or {}
    if item.get("equipment") is None and item.get("id") in runtime.coordinator.enclosures:
        item["equipment"] = runtime.coordinator.enclosures[item["id"]].get("equipment") or []
    try:
        enc_id = await hass.async_add_executor_job(runtime.db.save_enclosure, item)
    except (ValueError, KeyError) as err:
        _error(connection, msg, "invalid", str(err))
        return
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"], {"id": enc_id})


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/enclosure/delete", vol.Required("enclosure_id"): int}
)
@websocket_api.async_response
async def ws_enclosure_delete(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    await hass.async_add_executor_job(runtime.db.delete_enclosure, msg["enclosure_id"])
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/enclosure/assign",
        vol.Required("animal_id"): str,
        vol.Required("enclosure_id"): vol.Any(int, None),
    }
)
@websocket_api.async_response
async def ws_enclosure_assign(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    if msg["enclosure_id"] is not None and msg["enclosure_id"] not in runtime.coordinator.enclosures:
        _error(connection, msg, "not_found", "Onbekende kast")
        return
    try:
        await runtime.coordinator.async_assign(msg["animal_id"], msg["enclosure_id"])
    except KeyError:
        _error(connection, msg, "not_found", "Onbekend dier")
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/enclosure/log",
        vol.Required("enclosure_id"): int,
        vol.Required("entry_type"): vol.In(list(ENTRY_TYPES)),
        vol.Optional("animal_ids"): [str],
        vol.Optional("notes"): vol.Any(str, None),
        vol.Optional("data", default={}): dict,
    }
)
@websocket_api.async_response
async def ws_enclosure_log(hass: HomeAssistant, connection, msg) -> None:
    """Handeling in een kast; standaard voor alle bewoners."""
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    residents = runtime.coordinator.residents(msg["enclosure_id"])
    ids = [a for a in msg.get("animal_ids") or residents if a in residents]
    if not ids:
        _error(connection, msg, "invalid", "Deze kast heeft geen (gekozen) bewoners.")
        return
    try:
        entry_ids = await runtime.coordinator.async_log(
            ids, msg["entry_type"], None, msg.get("notes") or None,
            {**msg["data"], "enclosure_id": msg["enclosure_id"]},
        )
    except ValueError as err:
        _error(connection, msg, "invalid", str(err))
        return
    connection.send_result(msg["id"], {"entry_ids": entry_ids, "animals": ids})


# --- scanbewijs (fase 9) ----------------------------------------------------------


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/enclosure/scanned", vol.Required("code"): str}
)
@websocket_api.async_response
async def ws_enclosure_scanned(hass: HomeAssistant, connection, msg) -> None:
    """Werkscherm geopend via de QR-code van een kast: geldt als aanwezigheid."""
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    code = msg["code"].strip().lower()
    enc = next((e for e in runtime.coordinator.enclosures.values() if e["code"].lower() == code), None)
    if enc is None:
        _error(connection, msg, "not_found", "Onbekende kast")
        return
    runtime.nag.note_scan(enc["id"])
    async_dispatcher_send(hass, SIGNAL_UPDATE)
    connection.send_result(msg["id"], {"enclosure_id": enc["id"]})


# --- planten (fase 8) ----------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/plant/log",
        vol.Required("plants"): [vol.All(str, vol.Match(r"^plant\."))],
        vol.Required("entry_type"): vol.In(PLANT_ENTRY_TYPES),
        vol.Optional("enclosure_id"): vol.Any(int, None),
        vol.Optional("notes"): vol.Any(str, None),
        vol.Optional("data", default={}): dict,
    }
)
@websocket_api.async_response
async def ws_plant_log(hass: HomeAssistant, connection, msg) -> None:
    """Handeling voor planten (water, bemesten, snoeien, ...) noteren."""
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    ts = dt_util.utcnow()
    try:
        ids = await hass.async_add_executor_job(
            runtime.db.add_plant_entries, msg["plants"], msg["entry_type"], ts,
            msg.get("notes") or None, msg.get("enclosure_id"), msg["data"],
        )
    except ValueError as err:
        _error(connection, msg, "invalid", str(err))
        return
    for plant, entry_id in zip(msg["plants"], ids, strict=True):
        hass.bus.async_fire(
            EVENT_PLANT_ENTRY,
            {"entry_id": entry_id, "plant": plant, "type": msg["entry_type"],
             "timestamp": ts.isoformat(), "notes": msg.get("notes"),
             "enclosure_id": msg.get("enclosure_id")},
        )
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"], {"entry_ids": ids})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "arthropoda/plant/journal",
        vol.Optional("plants"): [str],
        vol.Optional("limit", default=50): vol.All(int, vol.Range(min=1, max=500)),
    }
)
@websocket_api.async_response
async def ws_plant_journal(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    entries = await hass.async_add_executor_job(
        runtime.db.list_plant_entries, msg.get("plants"), msg["limit"]
    )
    connection.send_result(msg["id"], {"entries": entries})


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/plant/entry/delete", vol.Required("entry_id"): int}
)
@websocket_api.async_response
async def ws_plant_entry_delete(hass: HomeAssistant, connection, msg) -> None:
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    await hass.async_add_executor_job(runtime.db.delete_plant_entry, msg["entry_id"])
    await runtime.coordinator.async_refresh()
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "arthropoda/task/done", vol.Required("uid"): str}
)
@websocket_api.async_response
async def ws_task_done(hass: HomeAssistant, connection, msg) -> None:
    """Taak afvinken (dier of kast), zoals in de takenlijst."""
    _, runtime = _require(hass, connection, msg)
    if runtime is None:
        return
    task = next((t for t in runtime.coordinator.all_tasks() if t.uid == msg["uid"]), None)
    if task is None:
        _error(connection, msg, "not_found", "Deze taak bestaat niet (meer).")
        return
    await runtime.coordinator.async_complete_task(task)
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): "arthropoda/nfc/listen"})
@callback
def ws_nfc_listen(hass: HomeAssistant, connection, msg) -> None:
    """Wacht op de eerstvolgende gescande NFC-tag (om hem aan een kast te koppelen)."""

    @callback
    def _scanned(event) -> None:
        connection.send_message(
            websocket_api.event_message(
                msg["id"], {"tag_id": event.data.get("tag_id"), "device_id": event.data.get("device_id")}
            )
        )

    connection.subscriptions[msg["id"]] = hass.bus.async_listen(EVENT_TAG_SCANNED, _scanned)
    connection.send_result(msg["id"])


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    for command in (
        ws_enclosures_list,
        ws_enclosure_save,
        ws_enclosure_delete,
        ws_enclosure_assign,
        ws_enclosure_log,
        ws_enclosure_scanned,
        ws_plant_log,
        ws_plant_journal,
        ws_plant_entry_delete,
        ws_task_done,
        ws_nfc_listen,
        ws_breeding_list,
        ws_brood_update,
        ws_stock_list,
        ws_stock_save,
        ws_stock_adjust,
        ws_stock_delete,
        ws_documents_list,
        ws_documents_delete,
        ws_measurements_list,
        ws_species_photo_auto_all,
        ws_ai_entities,
        ws_caresheet_extract,
        ws_species_photo_search,
        ws_species_photo_set,
        ws_animal_photo_delete,
        ws_subscribe,
        ws_animals,
        ws_meta,
        ws_animal_add,
        ws_animal_update,
        ws_journal_list,
        ws_journal_add,
        ws_journal_delete,
        ws_species_list,
        ws_species_get,
        ws_species_save,
        ws_species_delete,
    ):
        websocket_api.async_register_command(hass, command)
