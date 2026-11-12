"""SQLite-database voor Arthropoda Keeper.

Alle methoden zijn synchroon en worden vanuit Home Assistant in de executor
uitgevoerd (hass.async_add_executor_job). Geen HA-afhankelijkheden.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .caresheet import ParsedCaresheet, build_document, profile_parts, split_species
from .journal import COUNTER_TYPES, ENTRY_TYPES, compute_effects
from .models import Animal, AnimalBundle, CareProfile, Measurement, Species

SCHEMA_VERSION = 5

_SCHEMA_V1 = """
CREATE TABLE species (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scientific_name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    common_names    TEXT NOT NULL DEFAULT '{}',
    grp             TEXT NOT NULL DEFAULT 'other',
    development     TEXT,
    habitat         TEXT,
    info            TEXT NOT NULL DEFAULT '{}',
    source          TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE care_profile (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    species_id  INTEGER NOT NULL REFERENCES species(id) ON DELETE CASCADE,
    stage       TEXT,
    season      TEXT NOT NULL DEFAULT 'normal',
    months      TEXT,
    vals        TEXT NOT NULL DEFAULT '{}',
    sort        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_profile_species ON care_profile(species_id);

CREATE TABLE animal (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    species_id   INTEGER REFERENCES species(id) ON DELETE SET NULL,
    kind         TEXT NOT NULL DEFAULT 'individual',
    sex          TEXT NOT NULL DEFAULT 'unknown',
    stage        TEXT,
    instar       INTEGER,
    count        INTEGER,
    status       TEXT NOT NULL DEFAULT 'active',
    season_mode  TEXT NOT NULL DEFAULT 'auto',
    premolt      INTEGER NOT NULL DEFAULT 0,
    born_at      TEXT,
    acquired_at  TEXT,
    origin       TEXT,
    info         TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE TABLE journal_entry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id   TEXT NOT NULL REFERENCES animal(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,
    ts          TEXT NOT NULL,
    notes       TEXT,
    data        TEXT NOT NULL DEFAULT '{}',
    group_id    TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_journal_animal_type_ts ON journal_entry(animal_id, type, ts);

CREATE TABLE measurement (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id   TEXT NOT NULL REFERENCES animal(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    value       REAL NOT NULL,
    unit        TEXT,
    ts          TEXT NOT NULL,
    journal_id  INTEGER REFERENCES journal_entry(id) ON DELETE SET NULL
);
CREATE INDEX idx_measurement_animal_kind_ts ON measurement(animal_id, kind, ts);
"""

# Versie 2 (fase 6): kweek, stamboom, voorraad, documenten.
# Alleen toevoegingen: bestaande gegevens blijven ongewijzigd.
_SCHEMA_V2 = """
ALTER TABLE animal ADD COLUMN mother_id TEXT;
ALTER TABLE animal ADD COLUMN father_id TEXT;
ALTER TABLE animal ADD COLUMN generation TEXT;
ALTER TABLE animal ADD COLUMN brood_id INTEGER;

CREATE TABLE pairing (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id    TEXT NOT NULL,
    partner_id   TEXT,
    partner_text TEXT,
    ts           TEXT NOT NULL,
    outcome      TEXT,
    notes        TEXT,
    journal_id   INTEGER REFERENCES journal_entry(id) ON DELETE SET NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE brood (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    mother_id      TEXT NOT NULL,
    father_id      TEXT,
    type           TEXT NOT NULL,
    laid_at        TEXT NOT NULL,
    incubation     TEXT,
    count_laid     INTEGER,
    status         TEXT NOT NULL DEFAULT 'incubating',
    hatched_at     TEXT,
    count_hatched  INTEGER,
    notes          TEXT,
    journal_id     INTEGER REFERENCES journal_entry(id) ON DELETE SET NULL,
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_brood_mother ON brood(mother_id, status);

CREATE TABLE feeder_stock (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    size          TEXT,
    quantity      REAL NOT NULL DEFAULT 0,
    unit          TEXT,
    min_quantity  REAL,
    colony_id     TEXT,
    notes         TEXT,
    updated_at    TEXT NOT NULL
);

CREATE TABLE document (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id     TEXT,
    species_id    INTEGER,
    type          TEXT NOT NULL,
    title         TEXT NOT NULL,
    file          TEXT,
    content_type  TEXT,
    issued_at     TEXT,
    expires_at    TEXT,
    notes         TEXT,
    created_at    TEXT NOT NULL
);

INSERT INTO brood (mother_id, type, laid_at, count_laid, status, journal_id, created_at)
    SELECT animal_id, type, ts, json_extract(data, '$.count'), 'incubating', id, created_at
    FROM journal_entry WHERE type IN ('egg_sac', 'ootheca', 'egg_laying');

UPDATE brood SET status = 'hatched',
    hatched_at = (SELECT MIN(j.ts) FROM journal_entry j
                  WHERE j.animal_id = brood.mother_id AND j.type = 'hatch' AND j.ts >= brood.laid_at)
    WHERE EXISTS (SELECT 1 FROM journal_entry j
                  WHERE j.animal_id = brood.mother_id AND j.type = 'hatch' AND j.ts >= brood.laid_at)
"""

# Versie 3 (fase 7): kasten / terraria. Alleen toevoegingen.
_SCHEMA_V3 = """
CREATE TABLE enclosure (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name         TEXT,
    type         TEXT NOT NULL DEFAULT 'terrarium',
    length_cm    REAL,
    width_cm     REAL,
    height_cm    REAL,
    material     TEXT,
    ventilation  TEXT,
    location     TEXT,
    acquired_at  TEXT,
    price        REAL,
    seller       TEXT,
    status       TEXT NOT NULL DEFAULT 'in_use',
    nfc_tag      TEXT,
    config       TEXT NOT NULL DEFAULT '{}',
    equipment    TEXT NOT NULL DEFAULT '[]',
    notes        TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
ALTER TABLE animal ADD COLUMN enclosure_id INTEGER
"""

# Versie 4 (fase 8): dagboek voor planten (Plant Monitor, plant.*). Alleen toevoegingen.
_SCHEMA_V4 = """
CREATE TABLE plant_entry (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    plant        TEXT NOT NULL,
    ts           TEXT NOT NULL,
    type         TEXT NOT NULL,
    notes        TEXT,
    enclosure_id INTEGER,
    data         TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL
);
CREATE INDEX idx_plant_entry_plant ON plant_entry(plant, ts)
"""

_SCHEMA_V5 = """
CREATE TABLE plant_profile (
    plant            TEXT PRIMARY KEY,
    kind             TEXT NOT NULL DEFAULT 'crop',
    days_to_ready    REAL,
    days_in_use      REAL,
    days_to_recover  REAL,
    sow_every_days   REAL,
    days_to_germinate REAL,
    updated_at       TEXT NOT NULL
);
CREATE TABLE plant_pot (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    plant              TEXT NOT NULL,
    kind               TEXT NOT NULL,
    label              TEXT,
    status             TEXT NOT NULL,
    enclosure_id       INTEGER,
    home_enclosure_id  INTEGER,
    sown_at            TEXT,
    status_since       TEXT NOT NULL,
    ready_at           TEXT,
    cycles             INTEGER NOT NULL DEFAULT 0,
    notes              TEXT,
    stages             TEXT NOT NULL DEFAULT '{}',
    photos             TEXT NOT NULL DEFAULT '[]',
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
CREATE INDEX idx_plant_pot_status ON plant_pot(status, plant)
"""

_MIGRATIONS: dict[int, str] = {
    1: _SCHEMA_V1, 2: _SCHEMA_V2, 3: _SCHEMA_V3, 4: _SCHEMA_V4, 5: _SCHEMA_V5,
}

# Bakjes met voedselplanten (zie food.py)
POT_KINDS = ("crop", "perennial")
POT_STATUSES = ("growing", "recovering", "in_use", "done", "failed")
POT_FIELDS = (
    "plant", "kind", "label", "status", "enclosure_id", "home_enclosure_id", "sown_at",
    "status_since", "ready_at", "cycles", "notes", "stages", "photos",
)
POT_JSON = {"stages": dict, "photos": list}
PROFILE_FIELDS = ("kind", "days_to_ready", "days_in_use", "days_to_recover", "sow_every_days", "days_to_germinate")

ENCLOSURE_TYPES = ("terrarium", "faunabox", "breeding_box", "formicarium", "aquarium", "net_cage", "plant_cabinet", "other")
ENCLOSURE_STATUSES = ("in_use", "empty", "maintenance")
ENCLOSURE_FIELDS = (
    "code", "name", "type", "length_cm", "width_cm", "height_cm", "material", "ventilation",
    "location", "acquired_at", "price", "seller", "status", "nfc_tag", "notes",
)

BROOD_STATUSES = ("incubating", "hatched", "failed")
EGG_TYPES = ("egg_sac", "ootheca", "egg_laying")
DOCUMENT_TYPES = ("invoice", "cites", "permit", "breeder_statement", "health", "other")

# Velden die bij elke herstart uit de HA-configuratie overgenomen worden.
STATIC_FIELDS = (
    "name", "species_id", "kind", "born_at", "acquired_at", "origin",
    "mother_id", "father_id", "generation", "brood_id",
)
# Velden die alleen bij het aanmaken overgenomen worden; daarna beheert het
# dagboek ze (een vervelling verhoogt bv. het stadium).
INITIAL_FIELDS = ("sex", "stage", "instar", "count")
UPDATABLE_FIELDS = {
    *STATIC_FIELDS,
    *INITIAL_FIELDS,
    "status",
    "season_mode",
    "premolt",
    "info",
    "enclosure_id",
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        raise ValueError("Tijdstip zonder tijdzone")
    return ts.astimezone(UTC).isoformat(timespec="seconds")


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def diapause_period(start_iso: str, species_diapause: dict[str, Any], planned_end: str | None) -> dict:
    """Vroegste/laatste einde van een diapauze (uit de soort) en het geplande einde."""
    start = _parse(start_iso)
    period: dict[str, Any] = {"start": start_iso}
    for key, field in (("min_days", "earliest_end"), ("max_days", "latest_end")):
        try:
            days = float(species_diapause.get(key)) if species_diapause.get(key) is not None else None
        except (TypeError, ValueError):
            days = None
        if days is not None:
            period[field] = (start + timedelta(days=days)).isoformat(timespec="seconds")
    if planned_end:
        period["planned_end"] = str(planned_end)[:10]
    return period


class SpeciesExistsError(Exception):
    """Soort bestaat al en overschrijven is niet gevraagd."""


class Database:
    """Dunne laag rond sqlite3, thread-safe via een lock."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    # --- verbinding -------------------------------------------------------

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        self._conn = conn
        self._migrate()

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database is niet geopend")
        return self._conn

    def _migrate(self) -> None:
        with self._lock:
            version = self.conn.execute("PRAGMA user_version").fetchone()[0]
            if 0 < version < SCHEMA_VERSION:
                # Reservekopie vóór elke migratie van een bestaande database.
                backup_path = self.path.with_name(f"{self.path.name}.bak-v{version}")
                backup = sqlite3.connect(backup_path)
                try:
                    self.conn.backup(backup)
                finally:
                    backup.close()
            for target in range(version + 1, SCHEMA_VERSION + 1):
                self.conn.execute("BEGIN")
                try:
                    for statement in _MIGRATIONS[target].split(";"):
                        if statement.strip():
                            self.conn.execute(statement)
                    self.conn.execute(f"PRAGMA user_version = {target}")
                    self.conn.execute("COMMIT")
                except Exception:
                    self.conn.execute("ROLLBACK")
                    raise

    def _tx(self):
        """Context manager voor een transactie."""
        db = self

        class _Tx:
            def __enter__(self_inner):
                db._lock.acquire()
                db.conn.execute("BEGIN")
                return db.conn

            def __exit__(self_inner, exc_type, exc, tb):
                try:
                    db.conn.execute("ROLLBACK" if exc_type else "COMMIT")
                finally:
                    db._lock.release()
                return False

        return _Tx()

    # --- soorten ----------------------------------------------------------

    @staticmethod
    def _row_to_species(row: sqlite3.Row) -> Species:
        return Species(
            id=row["id"],
            scientific_name=row["scientific_name"],
            common_names=json.loads(row["common_names"]),
            group=row["grp"],
            development=row["development"],
            habitat=row["habitat"],
            info=json.loads(row["info"]),
            source=row["source"],
        )

    def list_species(self) -> list[Species]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM species ORDER BY scientific_name"
            ).fetchall()
        return [self._row_to_species(r) for r in rows]

    def get_species(self, species_id: int) -> Species | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM species WHERE id = ?", (species_id,)
            ).fetchone()
        return self._row_to_species(row) if row else None

    def find_species(self, scientific_name: str) -> Species | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM species WHERE scientific_name = ?", (scientific_name.strip(),)
            ).fetchone()
        return self._row_to_species(row) if row else None

    def get_profiles(self, species_id: int) -> list[CareProfile]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM care_profile WHERE species_id = ? ORDER BY sort, id",
                (species_id,),
            ).fetchall()
        return [
            CareProfile(
                stage=r["stage"],
                season=r["season"],
                months=json.loads(r["months"]) if r["months"] else None,
                values=json.loads(r["vals"]),
            )
            for r in rows
        ]

    def save_caresheet(
        self, sheet: ParsedCaresheet, overwrite: bool = False, species_id: int | None = None
    ) -> tuple[int, bool]:
        """Bewaar een soort met profielen. Geeft (id, nieuw aangemaakt) terug.

        Met `species_id` wordt precies die soort bijgewerkt, ook als de
        wetenschappelijke naam gewijzigd is (geen kopie meer bij hernoemen).
        """
        core, info = split_species(sheet.species)
        now = _now()
        with self._tx() as conn:
            same_name = conn.execute(
                "SELECT id FROM species WHERE scientific_name = ?", (core["scientific_name"],)
            ).fetchone()
            if species_id is not None:
                row = conn.execute("SELECT id FROM species WHERE id = ?", (species_id,)).fetchone()
                if row is None:
                    raise KeyError(species_id)
                if same_name and same_name["id"] != species_id:
                    raise SpeciesExistsError(core["scientific_name"])
                conn.execute(
                    "UPDATE species SET scientific_name = ? WHERE id = ?",
                    (core["scientific_name"], species_id),
                )
            else:
                row = same_name
                if row and not overwrite:
                    raise SpeciesExistsError(core["scientific_name"])
            if row:
                # De soortfoto staat niet in de caresheet: bij overschrijven behouden.
                old_info = json.loads(
                    conn.execute("SELECT info FROM species WHERE id = ?", (row["id"],)).fetchone()["info"]
                )
                if "photo" in old_info and "photo" not in info:
                    info["photo"] = old_info["photo"]
            params = (
                json.dumps(core["common_names"], ensure_ascii=False),
                core["group"],
                core["development"],
                core["habitat"],
                json.dumps(info, ensure_ascii=False),
                sheet.source,
                now,
            )
            if row:
                species_id = row["id"]
                conn.execute(
                    "UPDATE species SET common_names=?, grp=?, development=?, habitat=?,"
                    " info=?, source=?, updated_at=? WHERE id=?",
                    (*params, species_id),
                )
                conn.execute("DELETE FROM care_profile WHERE species_id = ?", (species_id,))
                created = False
            else:
                cur = conn.execute(
                    "INSERT INTO species (common_names, grp, development, habitat, info,"
                    " source, updated_at, scientific_name, created_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (*params, core["scientific_name"], now),
                )
                species_id = cur.lastrowid
                created = True
            for sort, profile in enumerate(sheet.profiles):
                stage, season, months, values = profile_parts(profile)
                conn.execute(
                    "INSERT INTO care_profile (species_id, stage, season, months, vals, sort)"
                    " VALUES (?,?,?,?,?,?)",
                    (
                        species_id,
                        stage,
                        season,
                        json.dumps(months) if months else None,
                        json.dumps(values, ensure_ascii=False),
                        sort,
                    ),
                )
        return species_id, created

    def set_species_photo(self, species_id: int, photo: dict[str, Any] | None) -> bool:
        """Soortfoto instellen of wissen (in de vrije info van de soort)."""
        with self._lock:
            row = self.conn.execute("SELECT info FROM species WHERE id = ?", (species_id,)).fetchone()
            if row is None:
                return False
            info = json.loads(row["info"])
            if photo:
                info["photo"] = photo
            else:
                info.pop("photo", None)
            self.conn.execute(
                "UPDATE species SET info = ?, updated_at = ? WHERE id = ?",
                (json.dumps(info, ensure_ascii=False), _now(), species_id),
            )
        return True

    def delete_species(self, species_id: int) -> bool:
        """Soort verwijderen (profielen gaan mee; dieren verwijzen dan naar niets)."""
        with self._lock:
            cur = self.conn.execute("DELETE FROM species WHERE id = ?", (species_id,))
        return cur.rowcount > 0

    def export_species(self, species_ids: Iterable[int] | None = None) -> list[dict[str, Any]]:
        """Soorten als caresheet-dicts (alle soorten als ids None is)."""
        species = self.list_species()
        if species_ids is not None:
            wanted = set(species_ids)
            species = [s for s in species if s.id in wanted]
        docs = []
        for sp in species:
            core = {
                "scientific_name": sp.scientific_name,
                "common_names": sp.common_names,
                "group": sp.group,
                "development": sp.development,
                "habitat": sp.habitat,
            }
            profiles = [
                (p.stage, p.season, p.months, p.values) for p in self.get_profiles(sp.id)
            ]
            info = {k: v for k, v in sp.info.items() if k != "photo"}
            docs.append(build_document(core, info, profiles, sp.source))
        return docs

    # --- dieren -----------------------------------------------------------

    def sync_animals(self, configs: dict[str, dict[str, Any]]) -> None:
        """Synchroniseer de dieren met de HA-subentries.

        configs: subentry_id -> subentry-data. Nieuwe dieren worden aangemaakt,
        bestaande krijgen de statische velden bij, verwijderde worden
        gearchiveerd (de geschiedenis blijft bewaard).
        """
        now = _now()
        with self._tx() as conn:
            existing = {
                r["id"]: r["status"] for r in conn.execute("SELECT id, status FROM animal")
            }
            for animal_id, cfg in configs.items():
                static = {k: cfg.get(k) for k in STATIC_FIELDS}
                static["species_id"] = int(static["species_id"]) if static["species_id"] else None
                static["kind"] = static["kind"] or "individual"
                static["brood_id"] = int(static["brood_id"]) if static["brood_id"] else None
                if animal_id in existing:
                    sets = ", ".join(f"{k} = ?" for k in static)
                    conn.execute(
                        f"UPDATE animal SET {sets}, updated_at = ? WHERE id = ?",
                        (*static.values(), now, animal_id),
                    )
                    if existing[animal_id] == "archived":
                        conn.execute(
                            "UPDATE animal SET status = 'active' WHERE id = ?", (animal_id,)
                        )
                else:
                    initial = {k: cfg.get(k) for k in INITIAL_FIELDS}
                    if initial["instar"] is not None:
                        initial["instar"] = int(initial["instar"])
                    if initial["count"] is not None:
                        initial["count"] = int(initial["count"])
                    initial["sex"] = initial["sex"] or "unknown"
                    fields = {**static, **initial}
                    cols = ", ".join(fields)
                    marks = ", ".join("?" for _ in fields)
                    conn.execute(
                        f"INSERT INTO animal (id, {cols}, created_at, updated_at)"
                        f" VALUES (?, {marks}, ?, ?)",
                        (animal_id, *fields.values(), now, now),
                    )
            for animal_id, status in existing.items():
                if animal_id not in configs and status in ("active", "diapause"):
                    conn.execute(
                        "UPDATE animal SET status = 'archived', updated_at = ? WHERE id = ?",
                        (now, animal_id),
                    )

    @staticmethod
    def _row_to_animal(row: sqlite3.Row) -> Animal:
        return Animal(
            id=row["id"],
            name=row["name"],
            species_id=row["species_id"],
            kind=row["kind"],
            sex=row["sex"],
            stage=row["stage"],
            instar=row["instar"],
            count=row["count"],
            status=row["status"],
            season_mode=row["season_mode"],
            premolt=bool(row["premolt"]),
            born_at=row["born_at"],
            acquired_at=row["acquired_at"],
            origin=row["origin"],
            info=json.loads(row["info"]),
            created_at=_parse(row["created_at"]),
            mother_id=row["mother_id"],
            father_id=row["father_id"],
            generation=row["generation"],
            brood_id=row["brood_id"],
            enclosure_id=row["enclosure_id"],
        )

    def get_animal(self, animal_id: str) -> Animal | None:
        with self._lock:
            row = self.conn.execute("SELECT * FROM animal WHERE id = ?", (animal_id,)).fetchone()
        return self._row_to_animal(row) if row else None

    def update_animal(self, animal_id: str, **fields: Any) -> None:
        unknown = set(fields) - UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"Onbekende velden: {unknown}")
        if not fields:
            return
        if "info" in fields:
            fields["info"] = json.dumps(fields["info"], ensure_ascii=False)
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self._lock:
            self.conn.execute(
                f"UPDATE animal SET {sets}, updated_at = ? WHERE id = ?",
                (*fields.values(), _now(), animal_id),
            )

    def load_bundles(self, animal_ids: Iterable[str]) -> dict[str, AnimalBundle]:
        bundles: dict[str, AnimalBundle] = {}
        species_cache: dict[int, tuple[Species | None, list[CareProfile]]] = {}
        for animal_id in animal_ids:
            animal = self.get_animal(animal_id)
            if animal is None:
                continue
            species, profiles = None, []
            if animal.species_id is not None:
                if animal.species_id not in species_cache:
                    species_cache[animal.species_id] = (
                        self.get_species(animal.species_id),
                        self.get_profiles(animal.species_id),
                    )
                species, profiles = species_cache[animal.species_id]
            with self._lock:
                last = {
                    r["type"]: _parse(r["last"])
                    for r in self.conn.execute(
                        "SELECT type, MAX(ts) AS last FROM journal_entry"
                        " WHERE animal_id = ? GROUP BY type",
                        (animal_id,),
                    )
                }
                molt_times = [
                    _parse(r["ts"])
                    for r in self.conn.execute(
                        "SELECT ts FROM journal_entry WHERE animal_id = ? AND type = 'molt'"
                        " ORDER BY ts",
                        (animal_id,),
                    )
                ]
                brood_entries = [
                    (r["type"], _parse(r["ts"]), json.loads(r["data"]))
                    for r in self.conn.execute(
                        "SELECT type, ts, data FROM journal_entry WHERE animal_id = ?"
                        " AND type IN ('egg_sac', 'ootheca', 'egg_laying', 'hatch')"
                        " ORDER BY ts",
                        (animal_id,),
                    )
                ]
                feeding_history = [
                    (r["type"], _parse(r["ts"]))
                    for r in self.conn.execute(
                        "SELECT type, ts FROM journal_entry WHERE animal_id = ?"
                        " AND type IN ('feeding', 'feeding_refused') ORDER BY ts DESC, id DESC LIMIT 8",
                        (animal_id,),
                    )
                ]
                adult_row = self.conn.execute(
                    "SELECT MAX(ts) AS ts FROM journal_entry WHERE animal_id = ? AND ("
                    " type = 'eclosion'"
                    " OR (type = 'molt' AND json_extract(data, '$.stage_after') = 'adult')"
                    " OR (type = 'stage_change' AND json_extract(data, '$.stage') = 'adult'))",
                    (animal_id,),
                ).fetchone()
                count_history = [
                    (_parse(r["ts"]), r["value"])
                    for r in self.conn.execute(
                        "SELECT ts, value FROM (SELECT ts, value FROM measurement"
                        " WHERE animal_id = ? AND kind = 'count' ORDER BY ts DESC LIMIT 12) ORDER BY ts",
                        (animal_id,),
                    )
                ]
                measurements = {
                    r["kind"]: Measurement(r["value"], r["unit"], _parse(r["ts"]))
                    for r in self.conn.execute(
                        "SELECT m.kind, m.value, m.unit, m.ts FROM measurement m"
                        " JOIN (SELECT kind, MAX(ts) AS ts FROM measurement"
                        "       WHERE animal_id = ? GROUP BY kind) latest"
                        " ON m.kind = latest.kind AND m.ts = latest.ts"
                        " WHERE m.animal_id = ?",
                        (animal_id, animal_id),
                    )
                }
            last_ts = {
                counter: max((last[t] for t in types if t in last), default=None)
                for counter, types in COUNTER_TYPES.items()
            }
            bundles[animal_id] = AnimalBundle(
                animal=animal,
                species=species,
                profiles=profiles,
                last_ts={k: v for k, v in last_ts.items() if v is not None},
                molt_count=len(molt_times),
                measurements=measurements,
                molt_times=molt_times,
                brood_entries=brood_entries,
                feeding_history=feeding_history,
                premolt_since=last.get("premolt_observed"),
                adult_since=_parse(adult_row["ts"]) if adult_row and adult_row["ts"] else None,
                count_history=count_history,
            )
        return bundles

    # --- dagboek ----------------------------------------------------------

    def add_entries(
        self,
        animal_ids: list[str],
        entry_type: str,
        ts: datetime,
        notes: str | None = None,
        data: dict[str, Any] | None = None,
        group_id: str | None = None,
    ) -> list[int]:
        """Voeg een dagboekregel toe voor één of meer dieren en pas de gevolgen toe.

        Alles gebeurt in één transactie: bij een fout wordt niets bewaard.
        """
        if entry_type not in ENTRY_TYPES:
            raise ValueError(f"Onbekend dagboektype: {entry_type}")
        data = data or {}
        ts_iso = _iso(ts)
        now = _now()
        ids: list[int] = []
        with self._tx() as conn:
            for animal_id in animal_ids:
                row = conn.execute(
                    "SELECT a.*, s.development, s.info AS species_info FROM animal a"
                    " LEFT JOIN species s ON s.id = a.species_id WHERE a.id = ?",
                    (animal_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(animal_id)
                effects = compute_effects(dict(row), entry_type, data)
                cur = conn.execute(
                    "INSERT INTO journal_entry (animal_id, type, ts, notes, data, group_id,"
                    " created_at) VALUES (?,?,?,?,?,?,?)",
                    (
                        animal_id,
                        entry_type,
                        ts_iso,
                        notes,
                        json.dumps(data, ensure_ascii=False, default=str),
                        group_id,
                        now,
                    ),
                )
                entry_id = cur.lastrowid
                ids.append(entry_id)
                for kind, value, unit in effects.measurements:
                    conn.execute(
                        "INSERT INTO measurement (animal_id, kind, value, unit, ts, journal_id)"
                        " VALUES (?,?,?,?,?,?)",
                        (animal_id, kind, value, unit, ts_iso, entry_id),
                    )
                if effects.animal_updates:
                    sets = ", ".join(f"{k} = ?" for k in effects.animal_updates)
                    conn.execute(
                        f"UPDATE animal SET {sets}, updated_at = ? WHERE id = ?",
                        (*effects.animal_updates.values(), now, animal_id),
                    )
                self._breeding_and_stock_effects(conn, row, entry_type, ts_iso, data, entry_id, now)
        return ids

    @staticmethod
    def _breeding_and_stock_effects(conn, row, entry_type, ts_iso, data, entry_id, now) -> None:
        """Kweek-, voorraad- en diapauzegevolgen van een dagboekregel (binnen de transactie)."""
        animal_id = row["id"]
        if entry_type in ("diapause_start", "diapause_end"):
            info = json.loads(row["info"] or "{}")
            if entry_type == "diapause_start":
                info["diapause"] = diapause_period(
                    ts_iso, json.loads(row["species_info"] or "{}").get("diapause") or {},
                    data.get("planned_end"),
                )
            else:
                info.pop("diapause", None)
            conn.execute(
                "UPDATE animal SET info = ?, updated_at = ? WHERE id = ?",
                (json.dumps(info, ensure_ascii=False), now, animal_id),
            )
        if entry_type in EGG_TYPES:
            species_info = json.loads(row["species_info"] or "{}")
            incubation = data.get("incubation_days") or species_info.get("incubation_days")
            conn.execute(
                "INSERT INTO brood (mother_id, father_id, type, laid_at, incubation, count_laid,"
                " status, notes, journal_id, created_at) VALUES (?,?,?,?,?,?,'incubating',?,?,?)",
                (
                    animal_id,
                    data.get("father_id"),
                    entry_type,
                    ts_iso,
                    json.dumps(incubation) if incubation else None,
                    data.get("count"),
                    data.get("notes"),
                    entry_id,
                    now,
                ),
            )
        elif entry_type == "hatch":
            params: tuple = (ts_iso, data.get("count"))
            if data.get("brood_id"):
                conn.execute(
                    "UPDATE brood SET status = 'hatched', hatched_at = ?, count_hatched = ?"
                    " WHERE id = ?",
                    (*params, int(data["brood_id"])),
                )
            else:
                conn.execute(
                    "UPDATE brood SET status = 'hatched', hatched_at = ?, count_hatched = ?"
                    " WHERE mother_id = ? AND status = 'incubating' AND laid_at <= ?",
                    (*params, animal_id, ts_iso),
                )
        elif entry_type == "pairing":
            conn.execute(
                "INSERT INTO pairing (animal_id, partner_id, partner_text, ts, outcome, notes,"
                " journal_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    animal_id,
                    data.get("partner_id"),
                    data.get("partner"),
                    ts_iso,
                    data.get("outcome"),
                    None,
                    entry_id,
                    now,
                ),
            )
        if entry_type == "feeding" and data.get("stock_id"):
            # Voorraad verminderen; is de voorraad een eigen kolonie, dan daalt ook die.
            quantity = float(data.get("quantity") or 1)
            stock = conn.execute(
                "SELECT * FROM feeder_stock WHERE id = ?", (int(data["stock_id"]),)
            ).fetchone()
            if stock is not None:
                conn.execute(
                    "UPDATE feeder_stock SET quantity = MAX(quantity - ?, 0), updated_at = ?"
                    " WHERE id = ?",
                    (quantity, now, stock["id"]),
                )
                if stock["colony_id"]:
                    conn.execute(
                        "UPDATE animal SET count = MAX(COALESCE(count, 0) - ?, 0), updated_at = ?"
                        " WHERE id = ?",
                        (int(quantity), now, stock["colony_id"]),
                    )

    # --- kasten -----------------------------------------------------------

    @staticmethod
    def _row_to_enclosure(row: sqlite3.Row) -> dict[str, Any]:
        enc = {k: row[k] for k in ("id", *ENCLOSURE_FIELDS, "created_at", "updated_at")}
        enc["config"] = json.loads(row["config"] or "{}")
        enc["equipment"] = json.loads(row["equipment"] or "[]")
        dims = [enc["length_cm"], enc["width_cm"], enc["height_cm"]]
        enc["volume_l"] = round(dims[0] * dims[1] * dims[2] / 1000, 1) if all(dims) else None
        return enc

    def list_enclosures(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM enclosure ORDER BY code").fetchall()
        return [self._row_to_enclosure(r) for r in rows]

    def get_enclosure(self, enclosure_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute("SELECT * FROM enclosure WHERE id = ?", (enclosure_id,)).fetchone()
        return self._row_to_enclosure(row) if row else None

    def find_enclosure(self, *, code: str | None = None, nfc_tag: str | None = None) -> dict[str, Any] | None:
        column, value = ("code", code) if code is not None else ("nfc_tag", nfc_tag)
        with self._lock:
            row = self.conn.execute(
                f"SELECT * FROM enclosure WHERE {column} = ?", (str(value).strip(),)
            ).fetchone()
        return self._row_to_enclosure(row) if row else None

    def save_enclosure(self, item: dict[str, Any]) -> int:
        """Kast toevoegen (zonder id) of bijwerken (met id)."""
        code = (item.get("code") or "").strip()
        if not code:
            raise ValueError("Code is verplicht")
        if item.get("type") and item["type"] not in ENCLOSURE_TYPES:
            raise ValueError(f"Ongeldig type: {item['type']}")
        if item.get("status") and item["status"] not in ENCLOSURE_STATUSES:
            raise ValueError(f"Ongeldige status: {item['status']}")
        fields = {k: item.get(k) for k in ENCLOSURE_FIELDS}
        fields["code"] = code
        fields["type"] = fields["type"] or "terrarium"
        fields["status"] = fields["status"] or "in_use"
        fields["nfc_tag"] = (fields["nfc_tag"] or None)
        fields["config"] = json.dumps(item.get("config") or {}, ensure_ascii=False)
        fields["equipment"] = json.dumps(item.get("equipment") or [], ensure_ascii=False)
        now = _now()
        with self._lock:
            clash = self.conn.execute(
                "SELECT id FROM enclosure WHERE code = ?", (code,)
            ).fetchone()
            if clash and clash["id"] != item.get("id"):
                raise ValueError(f"De code {code} wordt al gebruikt")
            if fields["nfc_tag"]:
                tag_clash = self.conn.execute(
                    "SELECT code FROM enclosure WHERE nfc_tag = ? AND id != ?",
                    (fields["nfc_tag"], item.get("id") or -1),
                ).fetchone()
                if tag_clash:
                    raise ValueError(f"Deze NFC-tag hoort al bij kast {tag_clash['code']}")
            if item.get("id"):
                sets = ", ".join(f"{k} = ?" for k in fields)
                cur = self.conn.execute(
                    f"UPDATE enclosure SET {sets}, updated_at = ? WHERE id = ?",
                    (*fields.values(), now, int(item["id"])),
                )
                if cur.rowcount == 0:
                    raise KeyError(item["id"])
                return int(item["id"])
            cols = ", ".join(fields)
            marks = ", ".join("?" for _ in fields)
            cur = self.conn.execute(
                f"INSERT INTO enclosure ({cols}, created_at, updated_at) VALUES ({marks}, ?, ?)",
                (*fields.values(), now, now),
            )
            return cur.lastrowid

    def delete_enclosure(self, enclosure_id: int) -> bool:
        """Kast verwijderen; bewoners worden losgekoppeld (blijven bestaan)."""
        with self._tx() as conn:
            conn.execute("UPDATE animal SET enclosure_id = NULL WHERE enclosure_id = ?", (enclosure_id,))
            cur = conn.execute("DELETE FROM enclosure WHERE id = ?", (enclosure_id,))
        return cur.rowcount > 0

    def service_equipment(self, enclosure_id: int, index: int, day: str) -> bool:
        """Uitrusting vervangen/gereinigd op `day` (JJJJ-MM-DD)."""
        enc = self.get_enclosure(enclosure_id)
        if enc is None or not 0 <= index < len(enc["equipment"]):
            return False
        enc["equipment"][index]["serviced_at"] = day
        with self._lock:
            self.conn.execute(
                "UPDATE enclosure SET equipment = ?, updated_at = ? WHERE id = ?",
                (json.dumps(enc["equipment"], ensure_ascii=False), _now(), enclosure_id),
            )
        return True

    # --- plantendagboek -----------------------------------------------------

    def add_plant_entries(
        self,
        plants: list[str],
        entry_type: str,
        ts: datetime,
        notes: str | None = None,
        enclosure_id: int | None = None,
        data: dict[str, Any] | None = None,
    ) -> list[int]:
        """Handeling voor één of meer planten noteren."""
        if not plants:
            raise ValueError("Geen planten gekozen")
        stamp, now = _iso(ts), _now()
        ids = []
        with self._tx() as conn:
            for plant in plants:
                cur = conn.execute(
                    "INSERT INTO plant_entry (plant, ts, type, notes, enclosure_id, data, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (plant, stamp, entry_type, notes, enclosure_id,
                     json.dumps(data or {}, ensure_ascii=False), now),
                )
                ids.append(cur.lastrowid)
        return ids

    def list_plant_entries(self, plants: list[str] | None = None, limit: int = 50) -> list[dict[str, Any]]:
        query = "SELECT * FROM plant_entry"
        args: list[Any] = []
        if plants is not None:
            if not plants:
                return []
            query += f" WHERE plant IN ({', '.join('?' for _ in plants)})"
            args += plants
        query += " ORDER BY ts DESC, id DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self.conn.execute(query, args).fetchall()
        return [
            {**{k: row[k] for k in ("id", "plant", "ts", "type", "notes", "enclosure_id")},
             "data": json.loads(row["data"] or "{}")}
            for row in rows
        ]

    def last_plant_entries(self, plants: list[str]) -> dict[str, dict[str, str]]:
        """{plant: {type: laatste tijdstip}}."""
        if not plants:
            return {}
        with self._lock:
            rows = self.conn.execute(
                f"SELECT plant, type, MAX(ts) AS ts FROM plant_entry WHERE plant IN "
                f"({', '.join('?' for _ in plants)}) GROUP BY plant, type",
                plants,
            ).fetchall()
        result: dict[str, dict[str, str]] = {}
        for row in rows:
            result.setdefault(row["plant"], {})[row["type"]] = row["ts"]
        return result

    def delete_plant_entry(self, entry_id: int) -> bool:
        with self._lock:
            cur = self.conn.execute("DELETE FROM plant_entry WHERE id = ?", (entry_id,))
        return cur.rowcount > 0

    # --- voedselplanten: profielen en bakjes --------------------------------

    def list_plant_profiles(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM plant_profile").fetchall()
        return {row["plant"]: {k: row[k] for k in PROFILE_FIELDS} for row in rows}

    def save_plant_profile(self, plant: str, profile: dict[str, Any]) -> None:
        if profile.get("kind") not in POT_KINDS:
            raise ValueError(f"Onbekende soort plant: {profile.get('kind')}")
        values = [profile.get(k) for k in PROFILE_FIELDS]
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO plant_profile (plant, {', '.join(PROFILE_FIELDS)}, updated_at)"
                f" VALUES (?, {', '.join('?' for _ in PROFILE_FIELDS)}, ?)"
                f" ON CONFLICT(plant) DO UPDATE SET "
                + ", ".join(f"{k} = excluded.{k}" for k in (*PROFILE_FIELDS, "updated_at")),
                (plant, *values, _now()),
            )

    def delete_plant_profile(self, plant: str) -> bool:
        with self._lock:
            cur = self.conn.execute("DELETE FROM plant_profile WHERE plant = ?", (plant,))
        return cur.rowcount > 0

    def list_pots(self, active_only: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM plant_pot"
        if active_only:
            query += " WHERE status NOT IN ('done', 'failed')"
        query += " ORDER BY id"
        with self._lock:
            rows = self.conn.execute(query).fetchall()
        return [self._row_to_pot(row) for row in rows]

    def last_sown(self) -> dict[str, str]:
        """{plant: laatste zaaidatum} over alle bakjes (ook opgegeten)."""
        with self._lock:
            rows = self.conn.execute(
                "SELECT plant, MAX(sown_at) AS ts FROM plant_pot WHERE sown_at IS NOT NULL GROUP BY plant"
            ).fetchall()
        return {row["plant"]: row["ts"] for row in rows}

    def get_pot(self, pot_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute("SELECT * FROM plant_pot WHERE id = ?", (pot_id,)).fetchone()
        return self._row_to_pot(row) if row else None

    @staticmethod
    def _row_to_pot(row: sqlite3.Row) -> dict[str, Any]:
        pot = {"id": row["id"], **{k: row[k] for k in POT_FIELDS}}
        for key, kind in POT_JSON.items():
            pot[key] = json.loads(pot[key]) if pot[key] else kind()
        return pot

    def add_pots(self, pots: list[dict[str, Any]]) -> list[int]:
        now, ids = _now(), []
        with self._tx() as conn:
            for pot in pots:
                if pot.get("kind") not in POT_KINDS or pot.get("status") not in POT_STATUSES:
                    raise ValueError("Ongeldig bakje")
                cur = conn.execute(
                    f"INSERT INTO plant_pot ({', '.join(POT_FIELDS)}, created_at, updated_at)"
                    f" VALUES ({', '.join('?' for _ in POT_FIELDS)}, ?, ?)",
                    (*[self._pot_value(k, pot.get(k, 0 if k == "cycles" else None)) for k in POT_FIELDS], now, now),
                )
                ids.append(cur.lastrowid)
        return ids

    def update_pot(self, pot_id: int, **fields: Any) -> None:
        unknown = set(fields) - set(POT_FIELDS)
        if unknown:
            raise ValueError(f"Onbekende velden: {', '.join(sorted(unknown))}")
        if "status" in fields and fields["status"] not in POT_STATUSES:
            raise ValueError(f"Onbekende status: {fields['status']}")
        with self._tx() as conn:
            cur = conn.execute(
                f"UPDATE plant_pot SET {', '.join(f'{k} = ?' for k in fields)}, updated_at = ? WHERE id = ?",
                (*[self._pot_value(k, v) for k, v in fields.items()], _now(), pot_id),
            )
            if cur.rowcount == 0:
                raise KeyError(pot_id)

    @staticmethod
    def _pot_value(key: str, value: Any) -> Any:
        if key in POT_JSON:
            return json.dumps(value if value is not None else POT_JSON[key](), ensure_ascii=False)
        return value

    # --- kweek ------------------------------------------------------------

    def list_broods(self, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        query = (
            "SELECT b.*, s.info AS species_info FROM brood b"
            " LEFT JOIN animal a ON a.id = b.mother_id"
            " LEFT JOIN species s ON s.id = a.species_id"
        )
        params: list[Any] = []
        if status:
            query += " WHERE b.status = ?"
            params.append(status)
        query += " ORDER BY b.laid_at DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self.conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            incubation = json.loads(r["incubation"]) if r["incubation"] else (
                json.loads(r["species_info"] or "{}").get("incubation_days")
            )
            expected = None
            if incubation is not None:
                lo, hi = (incubation, incubation) if not isinstance(incubation, list) else incubation
                laid = _parse(r["laid_at"])
                expected = [
                    (laid + timedelta(days=float(lo))).isoformat(),
                    (laid + timedelta(days=float(hi))).isoformat(),
                ]
            result.append(
                {
                    "id": r["id"],
                    "mother_id": r["mother_id"],
                    "father_id": r["father_id"],
                    "type": r["type"],
                    "laid_at": r["laid_at"],
                    "incubation": incubation,
                    "expected": expected,
                    "count_laid": r["count_laid"],
                    "status": r["status"],
                    "hatched_at": r["hatched_at"],
                    "count_hatched": r["count_hatched"],
                    "notes": r["notes"],
                }
            )
        return result

    def update_brood(self, brood_id: int, **fields: Any) -> bool:
        allowed = {"status", "father_id", "count_laid", "count_hatched", "hatched_at", "notes"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if "status" in fields and fields["status"] not in BROOD_STATUSES:
            raise ValueError(f"Ongeldige status: {fields['status']}")
        if not fields:
            return False
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self._lock:
            cur = self.conn.execute(f"UPDATE brood SET {sets} WHERE id = ?", (*fields.values(), brood_id))
        return cur.rowcount > 0

    def list_pairings(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM pairing ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def list_measurements(self, animal_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT kind, value, unit, ts FROM measurement WHERE animal_id = ? ORDER BY ts",
                (animal_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # --- voorraad ---------------------------------------------------------

    def list_stock(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM feeder_stock ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def save_stock(self, item: dict[str, Any]) -> int:
        fields = {k: item.get(k) for k in ("name", "size", "quantity", "unit", "min_quantity", "colony_id", "notes")}
        if not fields["name"]:
            raise ValueError("Naam is verplicht")
        fields["quantity"] = float(fields["quantity"] or 0)
        now = _now()
        with self._lock:
            if item.get("id"):
                sets = ", ".join(f"{k} = ?" for k in fields)
                self.conn.execute(
                    f"UPDATE feeder_stock SET {sets}, updated_at = ? WHERE id = ?",
                    (*fields.values(), now, int(item["id"])),
                )
                return int(item["id"])
            cols = ", ".join(fields)
            marks = ", ".join("?" for _ in fields)
            cur = self.conn.execute(
                f"INSERT INTO feeder_stock ({cols}, updated_at) VALUES ({marks}, ?)",
                (*fields.values(), now),
            )
            return cur.lastrowid

    def adjust_stock(self, stock_id: int, delta: float) -> float | None:
        with self._lock:
            self.conn.execute(
                "UPDATE feeder_stock SET quantity = MAX(quantity + ?, 0), updated_at = ? WHERE id = ?",
                (delta, _now(), stock_id),
            )
            row = self.conn.execute(
                "SELECT quantity FROM feeder_stock WHERE id = ?", (stock_id,)
            ).fetchone()
        return row["quantity"] if row else None

    def delete_stock(self, stock_id: int) -> bool:
        with self._lock:
            cur = self.conn.execute("DELETE FROM feeder_stock WHERE id = ?", (stock_id,))
        return cur.rowcount > 0

    # --- documenten -------------------------------------------------------

    def add_document(self, doc: dict[str, Any]) -> int:
        if doc.get("type") not in DOCUMENT_TYPES:
            raise ValueError(f"Ongeldig documenttype: {doc.get('type')}")
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO document (animal_id, species_id, type, title, file, content_type,"
                " issued_at, expires_at, notes, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    doc.get("animal_id"),
                    doc.get("species_id"),
                    doc["type"],
                    doc.get("title") or doc["type"],
                    doc.get("file"),
                    doc.get("content_type"),
                    doc.get("issued_at"),
                    doc.get("expires_at"),
                    doc.get("notes"),
                    _now(),
                ),
            )
        return cur.lastrowid

    def list_documents(self, animal_id: str | None = None) -> list[dict[str, Any]]:
        query, params = "SELECT * FROM document", []
        if animal_id:
            query += " WHERE animal_id = ?"
            params.append(animal_id)
        query += " ORDER BY COALESCE(issued_at, created_at) DESC"
        with self._lock:
            rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_document(self, doc_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute("SELECT * FROM document WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None

    def delete_document(self, doc_id: int) -> dict[str, Any] | None:
        doc = self.get_document(doc_id)
        if doc:
            with self._lock:
                self.conn.execute("DELETE FROM document WHERE id = ?", (doc_id,))
        return doc

    def get_journal(
        self,
        animal_id: str | None = None,
        limit: int = 50,
        entry_type: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM journal_entry"
        where, params = [], []
        if animal_id:
            where.append("animal_id = ?")
            params.append(animal_id)
        if entry_type:
            where.append("type = ?")
            params.append(entry_type)
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY ts DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self.conn.execute(query, params).fetchall()
        return [
            {
                "id": r["id"],
                "animal_id": r["animal_id"],
                "type": r["type"],
                "category": ENTRY_TYPES.get(r["type"], "other"),
                "timestamp": r["ts"],
                "notes": r["notes"],
                "data": json.loads(r["data"]),
                "group_id": r["group_id"],
            }
            for r in rows
        ]

    def get_journal_between(
        self, start: datetime, end: datetime, limit: int = 2000
    ) -> list[dict[str, Any]]:
        """Dagboekregels in een periode, met de naam van het dier (voor de kalender)."""
        with self._lock:
            rows = self.conn.execute(
                "SELECT j.*, a.name AS animal_name FROM journal_entry j"
                " JOIN animal a ON a.id = j.animal_id"
                " WHERE j.ts >= ? AND j.ts < ? ORDER BY j.ts LIMIT ?",
                (_iso(start), _iso(end), limit),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "animal_id": r["animal_id"],
                "animal_name": r["animal_name"],
                "type": r["type"],
                "timestamp": _parse(r["ts"]),
                "notes": r["notes"],
                "data": json.loads(r["data"]),
            }
            for r in rows
        ]

    def delete_entry(self, entry_id: int) -> bool:
        """Verwijder een dagboekregel (gevolgen worden niet teruggedraaid)."""
        with self._lock:
            cur = self.conn.execute("DELETE FROM journal_entry WHERE id = ?", (entry_id,))
        return cur.rowcount > 0
