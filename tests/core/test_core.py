"""Tests voor de kernlogica (zonder Home Assistant)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from arthropoda_core.caresheet import (
    CaresheetError,
    dump_documents,
    parse_caresheets,
    relax_caresheets,
)
from arthropoda_core.db import Database, SpeciesExistsError
from arthropoda_core.journal import compute_effects
from arthropoda_core.models import CareProfile
from arthropoda_core.profile import Readings, evaluate, resolve_profile

CARESHEETS = Path(__file__).resolve().parents[2] / "caresheets"

SHEET = """
format: arthropoda-caresheet/1
species:
  scientific_name: Testus maximus
  common_names: {nl: Testbeest}
  group: tarantula
  development: molting_adult
care_profiles:
  - temp_day: [22, 26]
    temp_night: [18, 22]
    humidity: [55, 65]
    feeding_interval_days: 14
  - stage: juvenile
    temp_day: [24, 27]
    feeding_interval_days: 5
  - season: winter
    months: [12, 1, 2]
    temp_day: [18, 22]
    feeding_interval_days: 28
"""


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    database.open()
    yield database
    database.close()


# --- caresheets -----------------------------------------------------------


def test_parse_caresheet():
    (sheet,) = parse_caresheets(SHEET)
    assert sheet.species["scientific_name"] == "Testus maximus"
    assert sheet.profiles[0]["temp_day"] == [22.0, 26.0]
    assert sheet.profiles[2]["season"] == "winter"


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("species: {scientific_name: Abc def, group: vogel}", "group"),
        ("species: {scientific_name: Abc def}\ncare_profiles: [{temp_day: [30, 20]}]", "minimum"),
        ("species: {scientific_name: Abc def}\ncare_profiles: [{tmp_day: [20, 30]}]", "tmp_day"),
        ("{{{", "YAML"),
        ("", "geen caresheets"),
    ],
)
def test_parse_caresheet_errors(text, fragment):
    with pytest.raises(CaresheetError, match=fragment):
        parse_caresheets(text)


def test_example_caresheets_are_valid():
    files = sorted(CARESHEETS.glob("*.yaml"))
    assert files, "geen voorbeeld-caresheets gevonden"
    for file in files:
        assert parse_caresheets(file.read_text(encoding="utf-8")), file.name


def test_roundtrip_export(db):
    (sheet,) = parse_caresheets(SHEET)
    db.save_caresheet(sheet)
    text = dump_documents(db.export_species())
    (again,) = parse_caresheets(text)
    assert again.species["scientific_name"] == "Testus maximus"
    assert again.profiles == sheet.profiles


def test_save_existing_species(db):
    (sheet,) = parse_caresheets(SHEET)
    sid, created = db.save_caresheet(sheet)
    assert created
    with pytest.raises(SpeciesExistsError):
        db.save_caresheet(sheet)
    sid2, created2 = db.save_caresheet(sheet, overwrite=True)
    assert (sid2, created2) == (sid, False)
    assert len(db.get_profiles(sid)) == 3


# --- profielen ------------------------------------------------------------


def _profiles():
    (sheet,) = parse_caresheets(SHEET)
    return [
        CareProfile(p.get("stage"), p.get("season", "normal"), p.get("months"),
                    {k: v for k, v in p.items() if k not in ("stage", "season", "months")})
        for p in sheet.profiles
    ]


def test_resolve_profile_stage_and_season():
    profiles = _profiles()
    values, season = resolve_profile(profiles, "juvenile", "auto", 6)
    assert season == "normal"
    assert values["temp_day"] == [24, 27]
    assert values["temp_night"] == [18, 22]  # uit het generieke profiel
    assert values["feeding_interval_days"] == 5

    values, season = resolve_profile(profiles, "adult", "auto", 1)
    assert season == "winter"
    assert values["temp_day"] == [18, 22]
    assert values["feeding_interval_days"] == 28

    # nimf valt terug op juveniel
    values, _ = resolve_profile(profiles, "nymph", "normal", 1)
    assert values["feeding_interval_days"] == 5

    # handmatig winter, ook in juni
    _, season = resolve_profile(profiles, "adult", "winter", 6)
    assert season == "winter"


def test_evaluate():
    values = {"temp_day": [22, 26], "temp_night": [18, 22], "humidity": [55, 65],
              "feeding_interval_days": 14}
    ok = evaluate(values, Readings([24.0], 60), True, {"feeding": 3}, False)
    assert ok == []

    problems = evaluate(values, Readings([21.0, 27.0], 70), True, {"feeding": 20}, False)
    assert set(problems) == {"temperature_low", "temperature_high", "humidity_high",
                             "feeding_overdue"}

    # 's nachts is 20 °C goed; voederen gepauzeerd (premolt)
    assert evaluate(values, Readings([20.0], 60), False, {"feeding": 20}, True) == []

    unavailable = evaluate(values, Readings(unavailable=["sensor.x"]), True, {}, False)
    assert unavailable == ["sensor_unavailable"]

    # 31 °C = dagmaximum 26 + 5 → kritiek
    critical = evaluate(values, Readings([31.0]), True, {}, False)
    assert critical == ["temperature_critical", "temperature_high"]
    assert evaluate({**values, "temp_max_safe": 35}, Readings([31.0]), True, {}, False) == [
        "temperature_high"
    ]


# --- dagboek --------------------------------------------------------------


def test_effects():
    eff = compute_effects({"instar": 4}, "molt", {"sex": "female", "legspan_mm": 45})
    assert eff.animal_updates == {"instar": 5, "premolt": 0, "sex": "female"}
    assert eff.measurements == [("legspan_mm", 45.0, "mm")]

    assert compute_effects({}, "molt", {}).animal_updates["instar"] == 1
    assert compute_effects({}, "death", {}).animal_updates == {"status": "deceased"}
    assert compute_effects({}, "count", {"count": 120}).animal_updates == {"count": 120}
    with pytest.raises(ValueError):
        compute_effects({}, "dansen", {})
    # Adulte bidsprinkhaan vervelt niet, adulte vogelspin wel
    with pytest.raises(ValueError, match="Adulten"):
        compute_effects({"stage": "adult", "development": "hemimetabolous"}, "molt", {})
    assert compute_effects(
        {"stage": "adult", "development": "molting_adult", "instar": 9}, "molt", {}
    ).animal_updates["instar"] == 10
    with pytest.raises(ValueError):
        compute_effects({"stage": "pupa"}, "premolt_observed", {})
    with pytest.raises(ValueError):
        compute_effects({}, "stage_change", {"stage": "volwassen"})


def test_animal_lifecycle(db):
    (sheet,) = parse_caresheets(SHEET)
    sid, _ = db.save_caresheet(sheet)
    db.sync_animals({"a1": {"name": "Rosie", "species_id": str(sid), "kind": "individual",
                            "stage": "juvenile", "instar": 6}})
    t0 = datetime(2026, 11, 1, 18, 0, tzinfo=UTC)
    db.add_entries(["a1"], "feeding", t0, data={"prey": "krekel"})
    db.add_entries(["a1"], "premolt_observed", t0 + timedelta(days=2))
    db.add_entries(["a1"], "molt", t0 + timedelta(days=5), data={"legspan_mm": 52})

    animal = db.get_animal("a1")
    assert (animal.instar, animal.premolt, animal.stage) == (7, False, "juvenile")

    bundle = db.load_bundles(["a1"])["a1"]
    assert bundle.molt_count == 1
    assert bundle.last_ts["feeding"] == t0
    assert bundle.measurements["legspan_mm"].value == 52
    assert len(bundle.profiles) == 3
    assert [e["type"] for e in db.get_journal("a1")] == ["molt", "premolt_observed", "feeding"]

    # dynamische velden blijven bij een herstart; verwijderd dier wordt gearchiveerd
    db.sync_animals({"a1": {"name": "Rosie II", "species_id": str(sid), "stage": "adult"}})
    animal = db.get_animal("a1")
    assert (animal.name, animal.stage) == ("Rosie II", "juvenile")
    db.sync_animals({})
    assert db.get_animal("a1").status == "archived"


def test_failed_entry_rolls_back(db):
    db.sync_animals({"a1": {"name": "A"}})
    with pytest.raises(KeyError):
        db.add_entries(["a1", "bestaat-niet"], "feeding", datetime.now(UTC))
    assert db.get_journal("a1") == []


def test_relax_moves_unknown_and_invalid_fields_to_extra():
    text = """
species:
  scientific_name: Hymenopus coronatus
  group: mantis
  time_to_adulthood_months: [4, 6]
  diet: vliegen en motten
care_profiles:
  - temp_day: [25, 30]
    ventilation: good
    flowers_needed: true
"""
    relaxed, moved = relax_caresheets(text)
    assert set(moved) == {
        "species › time_to_adulthood_months",
        "care_profiles › 1 › ventilation",
        "care_profiles › 1 › flowers_needed",
    }
    (sheet,) = parse_caresheets(relaxed)
    assert sheet.species["extra"]["time_to_adulthood_months"] == [4, 6]
    assert sheet.species["diet"] == {"info": "vliegen en motten"}
    assert sheet.profiles[0]["extra"] == {"ventilation": "good", "flowers_needed": True}
    assert sheet.profiles[0]["temp_day"] == [25.0, 30.0]


def test_strict_parse_still_rejects_typos():
    with pytest.raises(CaresheetError, match="time_to_adulthood_months"):
        parse_caresheets("species: {scientific_name: Abc def, time_to_adulthood_months: 3}")


def test_species_fields_in_profile_are_moved_to_species():
    text = """
species:
  scientific_name: Lasius niger
  group: ant
care_profiles:
  - temp_day: [20, 26]
    diapause: {min_days: 90, max_days: 150}
    feeder: false
incubation_days: [30, 40]
"""
    (sheet,) = parse_caresheets(text)
    assert sheet.species["diapause"] == {"min_days": 90.0, "max_days": 150.0}
    assert sheet.species["feeder"] is False
    assert sheet.species["incubation_days"] == [30.0, 40.0]
    assert "diapause" not in sheet.profiles[0]
