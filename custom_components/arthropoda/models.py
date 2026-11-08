"""Dataklassen voor Arthropoda Keeper (zonder Home Assistant-afhankelijkheden)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Species:
    """Een soort uit de soortendatabase."""

    id: int
    scientific_name: str
    common_names: dict[str, str] = field(default_factory=dict)
    group: str = "other"
    development: str | None = None
    habitat: str | None = None
    info: dict[str, Any] = field(default_factory=dict)
    source: str | None = None

    def display_name(self, language: str = "nl") -> str:
        """Wetenschappelijke naam, met volksnaam indien bekend."""
        common = self.common_names.get(language) or next(
            iter(self.common_names.values()), None
        )
        return f"{self.scientific_name} ({common})" if common else self.scientific_name


@dataclass(slots=True)
class CareProfile:
    """Klimaat- en verzorgingswaarden voor een levensfase en/of seizoen."""

    stage: str | None
    season: str
    months: list[int] | None
    values: dict[str, Any]


@dataclass(slots=True)
class Animal:
    """Een dier of kolonie (= een HA-apparaat)."""

    id: str
    name: str
    species_id: int | None
    kind: str
    sex: str
    stage: str | None
    instar: int | None
    count: int | None
    status: str
    season_mode: str
    premolt: bool
    born_at: str | None
    acquired_at: str | None
    origin: str | None
    info: dict[str, Any]
    created_at: datetime
    mother_id: str | None = None
    father_id: str | None = None
    generation: str | None = None
    brood_id: int | None = None
    enclosure_id: int | None = None


@dataclass(slots=True)
class Measurement:
    """Laatste meting van een bepaald type."""

    value: float
    unit: str | None
    ts: datetime


@dataclass(slots=True)
class AnimalBundle:
    """Alles wat uit de database nodig is om een dier te evalueren."""

    animal: Animal
    species: Species | None
    profiles: list[CareProfile]
    last_ts: dict[str, datetime]
    molt_count: int
    measurements: dict[str, Measurement]
    molt_times: list[datetime] = field(default_factory=list)
    # (type, tijdstip, data) van legsels en uitkomsten, chronologisch
    brood_entries: list[tuple[str, datetime, dict[str, Any]]] = field(default_factory=list)
