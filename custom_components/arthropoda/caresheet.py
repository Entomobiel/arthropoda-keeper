"""Caresheet-formaat (YAML): inlezen, valideren en exporteren.

Formaat `arthropoda-caresheet/1`, zie caresheets/README.md in de repo.
Geen Home Assistant-afhankelijkheden (alleen voluptuous en PyYAML, die in
HA aanwezig zijn).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import voluptuous as vol
import yaml

from .const import (
    DEVELOPMENT,
    GROUPS,
    HABITATS,
    SEASONS,
    STAGES,
    SUBSTRATE_MOISTURE,
    VENTILATION,
)

FORMAT_ID = "arthropoda-caresheet/1"


class CaresheetError(ValueError):
    """Ongeldige caresheet."""


def _range(value: Any) -> list[float]:
    """[min, max] met min ≤ max."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise vol.Invalid("verwacht een bereik [min, max]")
    lo, hi = (float(v) for v in value)
    if lo > hi:
        raise vol.Invalid(f"minimum ({lo}) is groter dan maximum ({hi})")
    return [lo, hi]


_POS = vol.All(vol.Coerce(float), vol.Range(min=0))
_FREE_DICT = vol.Schema({}, extra=vol.ALLOW_EXTRA)

# Velden van een verzorgingsprofiel (zonder stage/season/months).
PROFILE_VALUE_SCHEMA: dict[Any, Any] = {
    vol.Optional("temp_day"): _range,
    vol.Optional("temp_night"): _range,
    vol.Optional("temp_max_safe"): vol.Coerce(float),
    vol.Optional("humidity"): _range,
    vol.Optional("water_temp"): _range,
    vol.Optional("ph"): _range,
    vol.Optional("light_hours"): vol.All(vol.Coerce(float), vol.Range(min=0, max=24)),
    vol.Optional("uv"): bool,
    vol.Optional("substrate_moisture"): vol.In(SUBSTRATE_MOISTURE),
    vol.Optional("misting"): str,
    vol.Optional("ventilation"): vol.In(VENTILATION),
    vol.Optional("feeding_interval_days"): _POS,
    vol.Optional("cleaning_interval_days"): _POS,
    vol.Optional("substrate_change_interval_days"): _POS,
    vol.Optional("water_change_interval_days"): _POS,
    vol.Optional("post_molt_fast_days"): _POS,
    vol.Optional("notes"): str,
    vol.Optional("extra"): _FREE_DICT,
}

PROFILE_SCHEMA = vol.Schema(
    {
        vol.Optional("stage"): vol.In(STAGES),
        vol.Optional("season", default="normal"): vol.In(SEASONS),
        vol.Optional("months"): [vol.All(vol.Coerce(int), vol.Range(min=1, max=12))],
        **PROFILE_VALUE_SCHEMA,
    }
)

# Vrije informatievelden van een soort (worden als JSON bewaard).
INFO_KEYS = (
    "taxonomy",
    "lifespan",
    "adult_size",
    "diet",
    "enclosure",
    "legal",
    "temperament",
    "venom",
    "urticating_hairs",
    "incubation_days",
    "development_time",
    "diapause",
    "feeder",
    "notes",
    "extra",
)

DIAPAUSE_SCHEMA = vol.Schema(
    {
        vol.Optional("min_days"): _POS,
        vol.Optional("max_days"): _POS,
        vol.Optional("start_months"): [vol.All(vol.Coerce(int), vol.Range(min=1, max=12))],
        vol.Optional("stage"): vol.In(STAGES),
        vol.Optional("notes"): str,
    },
    extra=vol.ALLOW_EXTRA,
)

SPECIES_SCHEMA = vol.Schema(
    {
        vol.Required("scientific_name"): vol.All(str, vol.Strip, vol.Length(min=3)),
        vol.Optional("common_names", default={}): {str: str},
        vol.Optional("group", default="other"): vol.In(GROUPS),
        vol.Optional("development"): vol.In(DEVELOPMENT),
        vol.Optional("habitat"): vol.In(HABITATS),
        vol.Optional("taxonomy"): _FREE_DICT,
        vol.Optional("lifespan"): _FREE_DICT,
        vol.Optional("adult_size"): _FREE_DICT,
        vol.Optional("diet"): _FREE_DICT,
        vol.Optional("enclosure"): _FREE_DICT,
        vol.Optional("legal"): _FREE_DICT,
        vol.Optional("temperament"): str,
        vol.Optional("venom"): str,
        vol.Optional("urticating_hairs"): bool,
        vol.Optional("incubation_days"): vol.Any(_POS, _range),
        vol.Optional("development_time"): _FREE_DICT,
        # Winterrust / diapauze: {min_days, max_days, start_months, stage, notes}
        vol.Optional("diapause"): DIAPAUSE_SCHEMA,
        # Voederdier (bv. krekels, kakkerlakken, fruitvliegjes)
        vol.Optional("feeder"): bool,
        vol.Optional("notes"): str,
        # Vrij blok voor alles wat (nog) geen eigen veld heeft.
        vol.Optional("extra"): _FREE_DICT,
    }
)

DOCUMENT_SCHEMA = vol.Schema(
    {
        vol.Optional("format", default=FORMAT_ID): FORMAT_ID,
        vol.Required("species"): SPECIES_SCHEMA,
        vol.Optional("care_profiles", default=[]): [PROFILE_SCHEMA],
        vol.Optional("source"): vol.Any(str, None),
    }
)


@dataclass(slots=True)
class ParsedCaresheet:
    """Een gevalideerde caresheet, klaar voor de database."""

    species: dict[str, Any]
    profiles: list[dict[str, Any]]
    source: str | None


def split_species(species: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Splits in kolommen (naam, groep, ...) en vrije info."""
    core = {
        "scientific_name": species["scientific_name"],
        "common_names": species.get("common_names", {}),
        "group": species.get("group", "other"),
        "development": species.get("development"),
        "habitat": species.get("habitat"),
    }
    info = {k: species[k] for k in INFO_KEYS if k in species}
    return core, info


def profile_parts(profile: dict[str, Any]) -> tuple[str | None, str, list[int] | None, dict]:
    """(stage, season, months, values) uit een gevalideerd profiel."""
    values = {k: v for k, v in profile.items() if k not in ("stage", "season", "months")}
    return profile.get("stage"), profile.get("season", "normal"), profile.get("months"), values


def looks_like_path(text: str | None) -> str | None:
    """Als iemand een bestandsnaam in het YAML-veld zet, die naam teruggeven."""
    value = (text or "").strip()
    if value and "\n" not in value and value.lower().endswith((".yaml", ".yml")):
        return value
    return None


def _schema_keys(schema: vol.Schema) -> set[str]:
    return {str(key) for key in schema.schema}


# Velden die bij de soort horen, ook als ze per ongeluk in een profiel of
# los bovenaan staan.
SPECIES_LEVEL_KEYS = ("diapause", "feeder", "incubation_days", "development_time")


def hoist_species_fields(doc: Any) -> Any:
    """Verplaats soortvelden uit profielen/bovenaan naar `species` (ongewijzigd als ze er al staan)."""
    if not isinstance(doc, dict) or not isinstance(doc.get("species"), dict):
        return doc
    species = doc["species"]
    for key in SPECIES_LEVEL_KEYS:
        if key in doc:
            value = doc.pop(key)
            species.setdefault(key, value)
    for profile in doc.get("care_profiles") or []:
        if isinstance(profile, dict):
            for key in SPECIES_LEVEL_KEYS:
                if key in profile:
                    value = profile.pop(key)
                    species.setdefault(key, value)
    return doc


def relax_document(doc: Any) -> tuple[Any, list[str]]:
    """Maak een (AI-)caresheet bruikbaar zonder informatie te verliezen.

    Onbekende of ongeldige velden worden naar het vrije blok `extra` verplaatst
    in plaats van de hele caresheet te weigeren. Geeft (document, verplaatste
    velden) terug. Alleen de wetenschappelijke naam blijft verplicht.
    """
    if not isinstance(doc, dict) or not isinstance(doc.get("species"), dict):
        return doc, []
    doc = hoist_species_fields(doc)
    moved: list[str] = []
    species = doc["species"]

    def move(container: dict, key: str, label: str) -> None:
        container.setdefault("extra", {})
        if not isinstance(container["extra"], dict):
            container["extra"] = {"text": container["extra"]}
        container["extra"][key] = container.pop(key)
        moved.append(label)

    # Onbekende velden bovenaan en in de soort → species.extra
    for key in [k for k in doc if k not in _schema_keys(DOCUMENT_SCHEMA)]:
        species.setdefault("extra", {})[key] = doc.pop(key)
        moved.append(key)
    species_keys = _schema_keys(SPECIES_SCHEMA)
    for key in [k for k in species if k not in species_keys]:
        move(species, key, f"species › {key}")
    # Vrije velden als gewone tekst opgegeven → in een object verpakken
    for key in ("taxonomy", "lifespan", "adult_size", "diet", "enclosure", "legal", "development_time"):
        if key in species and not isinstance(species[key], dict):
            species[key] = {"info": species[key]}
    profiles = doc.get("care_profiles")
    if not isinstance(profiles, list):
        if profiles is not None:
            move(species, "care_profiles", "care_profiles")
            doc.pop("care_profiles", None)
        profiles = []
    profile_keys = _schema_keys(PROFILE_SCHEMA)
    for index, profile in enumerate(profiles):
        if isinstance(profile, dict):
            for key in [k for k in profile if k not in profile_keys]:
                move(profile, key, f"care_profiles › {index + 1} › {key}")

    # Velden met een ongeldige waarde (bv. ventilation: good) ook verplaatsen.
    for _ in range(50):
        try:
            DOCUMENT_SCHEMA(doc)
            break
        except vol.MultipleInvalid as err:
            path = list(err.errors[0].path)
        except vol.Invalid as err:
            path = list(err.path)
        if len(path) >= 2 and path[0] == "species" and path[1] != "scientific_name":
            if path[1] not in species:
                break
            move(species, str(path[1]), f"species › {path[1]}")
        elif len(path) >= 3 and path[0] == "care_profiles" and isinstance(path[1], int):
            profile = profiles[path[1]] if path[1] < len(profiles) else None
            if not isinstance(profile, dict) or path[2] not in profile:
                break
            move(profile, str(path[2]), f"care_profiles › {path[1] + 1} › {path[2]}")
        else:
            break
    return doc, moved


def relax_caresheets(text: str) -> tuple[str, list[str]]:
    """relax_document voor YAML-tekst (één of meer documenten)."""
    try:
        docs = [d for d in yaml.safe_load_all(text) if d is not None]
    except yaml.YAMLError:
        return text, []
    flat: list[Any] = []
    for doc in docs:
        flat.extend(doc if isinstance(doc, list) else [doc])
    moved: list[str] = []
    relaxed = []
    for doc in flat:
        doc, fields = relax_document(doc)
        relaxed.append(doc)
        moved.extend(fields)
    return dump_documents(relaxed), moved


def _format_error(err: vol.Invalid, index: int) -> str:
    path = " › ".join(str(p) for p in err.path) or "(document)"
    return f"caresheet {index + 1}, veld {path}: {err.msg}"


def parse_caresheets(text: str) -> list[ParsedCaresheet]:
    """Lees één of meer caresheets uit YAML-tekst.

    Ondersteunt meerdere documenten gescheiden door `---`, of een lijst.
    """
    try:
        docs = [d for d in yaml.safe_load_all(text) if d is not None]
    except yaml.YAMLError as err:
        raise CaresheetError(f"Geen geldige YAML: {err}") from err

    flat: list[Any] = []
    for doc in docs:
        flat.extend(doc if isinstance(doc, list) else [doc])
    if not flat:
        raise CaresheetError("Het bestand bevat geen caresheets.")

    result: list[ParsedCaresheet] = []
    for index, doc in enumerate(flat):
        if not isinstance(doc, dict):
            raise CaresheetError(
                f"caresheet {index + 1}: dit is geen caresheet (verwacht 'species:' en "
                "'care_profiles:'). Plak de inhoud van het bestand, of vul de bestandsnaam in "
                "bij 'Bestand'."
            )
        doc = hoist_species_fields(doc)
        try:
            valid = DOCUMENT_SCHEMA(doc)
        except vol.MultipleInvalid as err:
            raise CaresheetError(_format_error(err.errors[0], index)) from err
        except vol.Invalid as err:
            raise CaresheetError(_format_error(err, index)) from err
        result.append(
            ParsedCaresheet(
                species=valid["species"],
                profiles=valid["care_profiles"],
                source=valid.get("source"),
            )
        )
    return result


def build_document(
    core: dict[str, Any],
    info: dict[str, Any],
    profiles: list[tuple[str | None, str, list[int] | None, dict[str, Any]]],
    source: str | None,
) -> dict[str, Any]:
    """Omgekeerde richting: database → caresheet-dict."""
    species = {k: v for k, v in core.items() if v not in (None, {}, "")}
    species.update(info)
    out_profiles = []
    for stage, season, months, values in profiles:
        prof: dict[str, Any] = {}
        if stage:
            prof["stage"] = stage
        if season != "normal":
            prof["season"] = season
        if months:
            prof["months"] = months
        prof.update(values)
        out_profiles.append(prof)
    doc: dict[str, Any] = {"format": FORMAT_ID, "species": species, "care_profiles": out_profiles}
    if source:
        doc["source"] = source
    return doc


def dump_documents(docs: list[dict[str, Any]]) -> str:
    """Schrijf caresheets als YAML (meerdere documenten met ---)."""
    return yaml.safe_dump_all(docs, allow_unicode=True, sort_keys=False, default_flow_style=None)
