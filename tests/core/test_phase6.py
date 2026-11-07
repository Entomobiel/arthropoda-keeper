"""Fase 6: migratie van bestaande databases, kweek, voorraad, documenten."""

from datetime import UTC, datetime, timedelta
import json
import sqlite3

import pytest

from arthropoda_core import db as dbmod
from arthropoda_core.caresheet import parse_caresheets
from arthropoda_core.db import Database

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
SHEET = """
species:
  scientific_name: Sphodromantis lineola
  group: mantis
  development: hemimetabolous
  incubation_days: [28, 42]
care_profiles: [{feeding_interval_days: 3}]
"""


def _make_v1_database(path):
    """Database zoals ze er bij de gebruiker nu uitziet (schema versie 1, met gegevens)."""
    conn = sqlite3.connect(path)
    for statement in dbmod._SCHEMA_V1.split(";"):
        if statement.strip():
            conn.execute(statement)
    now = T0.isoformat()
    conn.execute(
        "INSERT INTO species (scientific_name, common_names, grp, info, source, created_at, updated_at)"
        " VALUES ('Sphodromantis lineola', '{\"nl\": \"Afrikaanse bidsprinkhaan\"}', 'mantis',"
        " '{\"incubation_days\": [28, 42], \"photo\": {\"url\": \"https://x/y.jpg\"}}', 'eigen', ?, ?)",
        (now, now),
    )
    conn.execute(
        "INSERT INTO care_profile (species_id, stage, season, vals, sort) VALUES (1, NULL, 'normal',"
        " '{\"temp_day\": [24, 30]}', 0)"
    )
    conn.execute(
        "INSERT INTO animal (id, name, species_id, kind, sex, stage, instar, status, info, created_at, updated_at)"
        " VALUES ('a1', 'Mantis vrouw', 1, 'individual', 'female', 'adult', 7, 'active', '{\"photo\": {\"file\": \"a1.jpg\"}}', ?, ?)",
        (now, now),
    )
    rows = [
        ("a1", "feeding", T0, "{}"),
        ("a1", "ootheca", T0 + timedelta(days=5), '{"count": 1}'),
        ("a1", "hatch", T0 + timedelta(days=40), '{"count": 80}'),
        ("a1", "ootheca", T0 + timedelta(days=50), "{}"),
    ]
    for animal_id, kind, ts, data in rows:
        conn.execute(
            "INSERT INTO journal_entry (animal_id, type, ts, data, created_at) VALUES (?,?,?,?,?)",
            (animal_id, kind, ts.isoformat(), data, now),
        )
    conn.execute(
        "INSERT INTO measurement (animal_id, kind, value, unit, ts) VALUES ('a1', 'length_mm', 75, 'mm', ?)",
        (now,),
    )
    conn.execute("PRAGMA user_version = 1")
    conn.commit()
    conn.close()


def test_migration_keeps_all_data(tmp_path):
    path = tmp_path / "arthropoda.db"
    _make_v1_database(path)

    database = Database(path)
    database.open()
    try:
        assert database.conn.execute("PRAGMA user_version").fetchone()[0] == dbmod.SCHEMA_VERSION
        # Reservekopie van de oude database
        backup = tmp_path / "arthropoda.db.bak-v1"
        assert backup.exists()
        assert sqlite3.connect(backup).execute("PRAGMA user_version").fetchone()[0] == 1

        # Soort, profiel, foto en dier ongewijzigd
        (species,) = database.list_species()
        assert species.scientific_name == "Sphodromantis lineola"
        assert species.common_names == {"nl": "Afrikaanse bidsprinkhaan"}
        assert species.info["photo"]["url"] == "https://x/y.jpg"
        assert database.get_profiles(species.id)[0].values == {"temp_day": [24, 30]}
        animal = database.get_animal("a1")
        assert (animal.name, animal.instar, animal.sex) == ("Mantis vrouw", 7, "female")
        assert animal.info["photo"]["file"] == "a1.jpg"
        assert animal.mother_id is None

        # Dagboek en metingen ongewijzigd
        assert len(database.get_journal("a1")) == 4
        assert database.list_measurements("a1")[0]["value"] == 75

        # Bestaande ootheken zijn legsels geworden: de eerste uitgekomen, de tweede nog niet
        broods = sorted(database.list_broods(), key=lambda b: b["laid_at"])
        assert [b["status"] for b in broods] == ["hatched", "incubating"]
        assert broods[0]["count_laid"] == 1
        assert broods[1]["expected"] is not None  # incubatieduur uit de soort

        # Een tweede keer openen doet niets meer
        database.close()
        database.open()
        assert len(database.list_broods()) == 2
    finally:
        database.close()


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "t.db")
    database.open()
    (sheet,) = parse_caresheets(SHEET)
    database.save_caresheet(sheet)
    database.sync_animals({
        "f": {"name": "Vrouw", "species_id": "1", "sex": "female", "stage": "adult"},
        "m": {"name": "Man", "species_id": "1", "sex": "male", "stage": "adult"},
        "col": {"name": "Krekels", "kind": "colony", "count": 200},
    })
    yield database
    database.close()


def test_breeding_flow(db):
    db.add_entries(["f"], "pairing", T0, data={"partner_id": "m", "outcome": "success"})
    db.add_entries(["f"], "ootheca", T0 + timedelta(days=10), data={"father_id": "m", "count": 1})
    (pairing,) = db.list_pairings()
    assert (pairing["animal_id"], pairing["partner_id"], pairing["outcome"]) == ("f", "m", "success")
    (brood,) = db.list_broods()
    assert brood["status"] == "incubating" and brood["father_id"] == "m"
    laid = T0 + timedelta(days=10)
    assert brood["expected"] == [(laid + timedelta(days=28)).isoformat(), (laid + timedelta(days=42)).isoformat()]

    db.add_entries(["f"], "hatch", T0 + timedelta(days=45), data={"count": 60})
    (brood,) = db.list_broods()
    assert (brood["status"], brood["count_hatched"]) == ("hatched", 60)

    # Nakomelingen: ouders en generatie komen uit de configuratie
    db.sync_animals({
        "f": {"name": "Vrouw", "species_id": "1"}, "m": {"name": "Man", "species_id": "1"},
        "col": {"name": "Krekels", "kind": "colony"},
        "kids": {"name": "L1 lineola", "species_id": "1", "kind": "colony", "count": 60,
                 "mother_id": "f", "father_id": "m", "generation": "F1", "brood_id": str(brood["id"])},
    })
    kids = db.get_animal("kids")
    assert (kids.mother_id, kids.father_id, kids.generation, kids.brood_id) == ("f", "m", "F1", brood["id"])

    assert db.update_brood(brood["id"], status="failed")
    with pytest.raises(ValueError):
        db.update_brood(brood["id"], status="weg")


def test_stock_decreases_on_feeding(db):
    stock_id = db.save_stock({"name": "Huiskrekel", "size": "L3", "quantity": 50, "min_quantity": 20})
    colony_stock = db.save_stock({"name": "Eigen krekels", "quantity": 200, "colony_id": "col"})
    db.add_entries(["f", "m"], "feeding", T0, data={"stock_id": stock_id, "quantity": 2})
    stock = {s["id"]: s for s in db.list_stock()}
    assert stock[stock_id]["quantity"] == 46  # 2 dieren × 2
    db.add_entries(["f"], "feeding", T0, data={"stock_id": colony_stock, "quantity": 5})
    assert db.get_animal("col").count == 195
    assert db.adjust_stock(stock_id, -100) == 0  # nooit negatief
    assert db.adjust_stock(stock_id, 30) == 30
    db.save_stock({"id": stock_id, "name": "Huiskrekel", "quantity": 10, "min_quantity": 20})
    assert {s["id"]: s for s in db.list_stock()}[stock_id]["quantity"] == 10
    assert db.delete_stock(stock_id)


def test_documents(db):
    doc_id = db.add_document({"animal_id": "f", "type": "cites", "title": "CITES-certificaat",
                              "file": "doc1.pdf", "expires_at": "2027-01-01"})
    (doc,) = db.list_documents("f")
    assert (doc["id"], doc["title"], doc["expires_at"]) == (doc_id, "CITES-certificaat", "2027-01-01")
    assert db.delete_document(doc_id)["file"] == "doc1.pdf"
    assert db.list_documents() == []
    with pytest.raises(ValueError):
        db.add_document({"type": "geheim", "title": "x"})


def test_measurement_history(db):
    for i, length in enumerate((20, 28, 35)):
        db.add_entries(["f"], "measurement", T0 + timedelta(days=30 * i), data={"length_mm": length})
    history = db.list_measurements("f")
    assert [h["value"] for h in history] == [20, 28, 35]
    assert json.dumps(history)  # serialiseerbaar voor de frontend


DIAPAUSE_SHEET = """
species:
  scientific_name: Lasius niger
  group: ant
  development: holometabolous
  diapause: {min_days: 90, max_days: 150, start_months: [10, 11], stage: adult}
care_profiles: [{feeding_interval_days: 3}]
---
species:
  scientific_name: Acheta domesticus
  group: orthoptera
  feeder: true
care_profiles: [{feeding_interval_days: 2}]
"""


def test_diapause_period_and_task(tmp_path):
    from arthropoda_core.tasks import compute_tasks, project

    database = Database(tmp_path / "d.db")
    database.open()
    try:
        for sheet in parse_caresheets(DIAPAUSE_SHEET):
            database.save_caresheet(sheet)
        lasius = database.find_species("Lasius niger")
        cricket = database.find_species("Acheta domesticus")
        assert lasius.info["diapause"]["min_days"] == 90
        assert cricket.info["feeder"] is True

        database.sync_animals({"k": {"name": "Kolonie 1", "species_id": str(lasius.id), "kind": "colony"}})
        database.add_entries(["k"], "diapause_start", T0)
        animal = database.get_animal("k")
        assert animal.status == "diapause"
        dia = animal.info["diapause"]
        assert dia["earliest_end"] == (T0 + timedelta(days=90)).isoformat()
        assert dia["latest_end"] == (T0 + timedelta(days=150)).isoformat()

        tasks = compute_tasks("k", {}, {}, T0, True, None, dia)
        (task,) = [t for t in tasks if t.kind == "diapause_end"]
        assert task.due == T0 + timedelta(days=90) and task.journal_type == "diapause_end"
        # eenmalige taak: één keer in de kalender, geen herhaling
        assert project(task, T0 + timedelta(days=400)) == [task.due]

        # Zelf gepland einde gaat voor
        database.add_entries(["k"], "diapause_start", T0, data={"planned_end": "2027-02-15"})
        dia = database.get_animal("k").info["diapause"]
        assert dia["planned_end"] == "2027-02-15"
        (task,) = [t for t in compute_tasks("k", {}, {}, T0, True, None, dia) if t.kind == "diapause_end"]
        assert task.due.date().isoformat() == "2027-02-15"

        database.add_entries(["k"], "diapause_end", T0 + timedelta(days=120))
        animal = database.get_animal("k")
        assert animal.status == "active" and "diapause" not in animal.info
    finally:
        database.close()
