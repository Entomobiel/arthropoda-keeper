"""Dagboek: actietypes en hun automatische gevolgen.

Dit bestand heeft bewust geen Home Assistant-afhankelijkheden, zodat het
los getest kan worden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import ADULT_MOLTING_DEVELOPMENT, SEXES, STAGES

# type -> categorie
ENTRY_TYPES: dict[str, str] = {
    # Voeding
    "feeding": "feeding",
    "feeding_refused": "feeding",
    "water_refill": "feeding",
    "remove_leftovers": "feeding",
    "plant_food": "feeding",
    "supplement": "feeding",
    # Mieren: voedselstromen
    "feed_sugar": "feeding",
    "feed_seeds": "feeding",
    "feed_leaves": "feeding",
    # Hygiëne
    "spot_clean": "hygiene",
    "full_clean": "hygiene",
    "substrate_change": "hygiene",
    "substrate_moisten": "hygiene",
    "pest_check": "hygiene",
    # Klimaat & water
    "misting_manual": "climate",
    "climate_adjust": "climate",
    "water_change": "climate",
    "water_test": "climate",
    "filter_clean": "climate",
    # Ontwikkeling
    "premolt_observed": "development",
    "molt": "development",
    "molt_problem": "development",
    "pupation": "development",
    "eclosion": "development",
    "stage_change": "development",
    "diapause_start": "development",
    "diapause_end": "development",
    # Kweek
    "pairing": "breeding",
    "egg_sac": "breeding",
    "ootheca": "breeding",
    "egg_laying": "breeding",
    "brood_pulled": "breeding",
    "hatch": "breeding",
    "split_colony": "breeding",
    # Metingen
    "measurement": "measurement",
    "count": "measurement",
    # Mieren: telling (koningin, werksters, broed)
    "census": "measurement",
    # Gezondheid
    "observation": "health",
    "health_issue": "health",
    "treatment": "health",
    "death": "health",
    # Verplaatsing
    "rehouse": "movement",
    "escape": "movement",
    "recaptured": "movement",
    # Administratie
    "acquired": "admin",
    "sold": "admin",
    "given_away": "admin",
    "released": "admin",
    "document_added": "admin",
    # Overig
    "note": "other",
}

# Tellers "dagen sinds ...": welke types zetten de teller op nul.
COUNTER_TYPES: dict[str, tuple[str, ...]] = {
    "feeding": ("feeding",),
    "molt": ("molt",),
    "cleaning": ("spot_clean", "full_clean", "substrate_change"),
    "substrate_change": ("substrate_change",),
    "water_change": ("water_change",),
    "misting": ("misting_manual",),
}

# Meetwaarden die in een dagboekregel kunnen zitten: sleutel -> eenheid
MEASUREMENT_FIELDS: dict[str, str] = {
    "length_mm": "mm",
    "legspan_mm": "mm",
    "weight_g": "g",
}

_STATUS_BY_TYPE = {
    "death": "deceased",
    "sold": "sold",
    "given_away": "sold",
    "released": "released",
    "escape": "escaped",
    "recaptured": "active",
}


@dataclass(slots=True)
class Effects:
    """Gevolgen van een dagboekregel."""

    animal_updates: dict[str, Any] = field(default_factory=dict)
    measurements: list[tuple[str, float, str | None]] = field(default_factory=list)


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def can_molt(stage: str | None, development: str | None) -> bool:
    """Kan een dier in deze levensfase nog vervellen?"""
    return molt_impossible(stage, development) is None


def molt_impossible(stage: str | None, development: str | None) -> str | None:
    """Reden waarom een vervelling niet kan, of None als ze wel kan.

    - Eieren en poppen vervellen niet (een pop komt uit: 'eclosion').
    - Adulten vervellen alleen bij soorten die levenslang vervellen
      (vogelspinnen, schorpioenen, pissebedden, ...).
    Bij onbekende ontwikkeling wordt niets geblokkeerd.
    """
    if stage in ("egg", "pupa"):
        return f"Een dier in de fase '{stage}' vervelt niet."
    if (
        stage == "adult"
        and development is not None
        and development not in ADULT_MOLTING_DEVELOPMENT
    ):
        return "Adulten van deze soort vervellen niet meer."
    return None


def compute_effects(animal: dict[str, Any], entry_type: str, data: dict[str, Any]) -> Effects:
    """Bepaal welke dierwaarden wijzigen door een dagboekregel.

    `animal` is een dict met minstens de sleutels `instar` en `kind`.
    """
    if entry_type not in ENTRY_TYPES:
        raise ValueError(f"Onbekend dagboektype: {entry_type}")

    eff = Effects()
    upd = eff.animal_updates

    if entry_type in ("molt", "premolt_observed"):
        reason = molt_impossible(animal.get("stage"), animal.get("development"))
        if reason:
            raise ValueError(reason)

    if entry_type == "molt":
        after = _as_int(data.get("instar_after"))
        if after is not None:
            upd["instar"] = after
        else:
            upd["instar"] = (animal.get("instar") or 0) + 1
        upd["premolt"] = 0
        sex = data.get("sex")
        if sex in SEXES and sex != "unknown":
            upd["sex"] = sex
        if data.get("stage_after") in STAGES:
            upd["stage"] = data["stage_after"]

    elif entry_type == "premolt_observed":
        upd["premolt"] = 1

    elif entry_type == "pupation":
        upd["stage"] = "pupa"

    elif entry_type == "eclosion":
        upd["stage"] = "adult"

    elif entry_type == "stage_change":
        stage = data.get("stage")
        if stage not in STAGES:
            raise ValueError(f"Ongeldige levensfase: {stage}")
        upd["stage"] = stage
        instar = _as_int(data.get("instar"))
        if instar is not None:
            upd["instar"] = instar

    elif entry_type == "diapause_start":
        upd["status"] = "diapause"
        upd["season_mode"] = "winter"

    elif entry_type == "diapause_end":
        upd["status"] = "active"
        upd["season_mode"] = "auto"

    elif entry_type in _STATUS_BY_TYPE:
        upd["status"] = _STATUS_BY_TYPE[entry_type]

    elif entry_type == "split_colony":
        remaining = _as_int(data.get("count_remaining"))
        if remaining is not None:
            upd["count"] = remaining

    # Metingen en tellingen kunnen bij elk type meegegeven worden
    # (bv. lengte meten bij een vervelling).
    for key, unit in MEASUREMENT_FIELDS.items():
        if data.get(key) is not None:
            try:
                eff.measurements.append((key, float(data[key]), unit))
            except (TypeError, ValueError) as err:
                raise ValueError(f"Ongeldige waarde voor {key}: {data[key]}") from err

    if entry_type == "census":
        workers = _as_int(data.get("workers"))
        if workers is not None:
            if workers < 0:
                raise ValueError("Aantal werksters kan niet negatief zijn")
            data = {**data, "count": workers}

    count = _as_int(data.get("count"))
    if count is not None and entry_type in ("count", "measurement", "hatch", "census"):
        if entry_type != "hatch":
            upd["count"] = count
        eff.measurements.append(("count", float(count), None))

    return eff
