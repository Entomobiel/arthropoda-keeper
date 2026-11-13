"""Tests voor mierenkolonies en nestmodules (zonder Home Assistant)."""

from datetime import UTC, datetime, timedelta

from arthropoda_core import ants, nest_modules

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
LASIUS = {"ant": {"type": "generalist", "founding": "claustral",
                  "development_days": {"egg": [10, 14], "larva": [14, 20], "pupa": [14, 20]}}}
MESSOR = {"ant": {"type": "harvester", "founding": "claustral", "polymorphic": True}}


def _d(days: float) -> datetime:
    return NOW - timedelta(days=days)


def _keys(items):
    return [i["key"] for i in items]


def test_is_ant_and_settings():
    assert ants.is_ant("ant", {}) and ants.is_ant("other", {"ant": {"stage": "founding"}})
    assert not ants.is_ant("roach", {})
    cfg = ants.settings(MESSOR, {})
    assert cfg["type"] == "harvester" and cfg["food"] == {"water": 7, "seeds": 7, "protein": 7}
    assert cfg["polymorphic"] is True and cfg["queen_check_days"] == 60
    # Kolonie overschrijft: suiker erbij, zaden uit, andere controle-termijn
    cfg = ants.settings(MESSOR, {"ant": {"food": {"sugar": 10, "seeds": 0}, "queen_check_days": 30}})
    assert cfg["food"] == {"water": 7, "protein": 7, "sugar": 10} and cfg["queen_check_days"] == 30


def test_colony_state_and_stages():
    cfg = ants.settings(LASIUS, {})
    state = ants.colony_state([], cfg, _d(30), NOW)
    assert state["stage"] == "founding" and state["queen"]["status"] is None
    census = [
        (_d(40), {"queen": "seen", "eggs": 2}),
        (_d(25), {"queen": "seen", "eggs": 3, "larvae": 2}),
        (_d(10), {"queen": "not_seen", "eggs": 1, "larvae": 2, "pupae": 1}),
    ]
    state = ants.colony_state(census, cfg, _d(45), NOW)
    assert state["stage"] == "founding" and state["queen"]["status"] == "not_seen"
    assert state["queen"]["last_seen"] == _d(25).isoformat()
    assert state["first"]["eggs"] == _d(40).isoformat() and state["first"]["pupae"] == _d(10).isoformat()
    # Eerste werksters verwacht: eitjes + 38–54 dagen
    lo, hi = state["expected_workers"]
    assert lo == (_d(40) + timedelta(days=38)).isoformat() and hi == (_d(40) + timedelta(days=54)).isoformat()
    census.append((_d(1), {"queen": "seen", "workers": 6, "eggs": 2, "larvae": 1, "pupae": 2}))
    state = ants.colony_state(census, cfg, _d(45), NOW)
    assert state["stage"] == "nanitics" and state["workers"] == 6 and state["expected_workers"] is None
    census.append((NOW, {"workers": 120}))
    assert ants.colony_state(census, cfg, _d(45), NOW)["stage"] == "growing"
    census.append((NOW, {"workers": 300, "alates": True}))
    assert ants.colony_state(census, cfg, _d(45), NOW)["stage"] == "mature"
    # Vaste fase per kolonie wint
    fixed = ants.settings(LASIUS, {"ant": {"stage": "growing"}})
    assert ants.colony_state([], fixed, None, NOW)["stage"] == "growing"


def test_streams_founding_and_leftovers():
    cfg = ants.settings(LASIUS, {})
    founding = ants.colony_state([], cfg, _d(5), NOW)
    # Claustrale stichting: geen voedertaken
    assert ants.feeding_blocked(founding, cfg)
    assert ants.stream_dues(founding, cfg, {}, _d(5), paused=False) == []
    grown = ants.colony_state([(_d(2), {"queen": "seen", "workers": 50, "larvae": 1})], cfg, _d(100), NOW)
    last = {"water_refill": _d(3), "feed_sugar": _d(1), "feeding": _d(3)}
    dues = {k: (due, days) for k, due, days in ants.stream_dues(grown, cfg, last, _d(100), paused=False)}
    assert dues["ant_water"] == (_d(3) + timedelta(days=7), 7)
    assert dues["ant_sugar"][0] == _d(1) + timedelta(days=4)
    # Eiwit gegeven, nog geen resten weggehaald → taak na 2 dagen
    assert dues["ant_leftovers"][0] == _d(3) + timedelta(days=2)
    last["remove_leftovers"] = _d(1)
    assert "ant_leftovers" not in {k for k, *_ in ants.stream_dues(grown, cfg, last, _d(100), False)}
    # Veel larven → vaker eiwit (4 → 2,7 dagen)
    hungry = ants.colony_state([(_d(2), {"workers": 50, "larvae": 3})], cfg, _d(100), NOW)
    assert ants.stream_intervals(hungry, cfg)["protein"] == 2.7
    # Winterrust: geen voedertaken
    assert ants.stream_dues(grown, cfg, last, _d(100), paused=True) == []


def test_ant_insights():
    cfg = ants.settings(LASIUS, {})
    # Pas gevangen: verwachting eerste werksters vanaf de vangstdatum
    assert _keys(ants.ant_insights(ants.colony_state([], cfg, _d(5), NOW), cfg, False, NOW)) == [
        "claustral_founding", "no_census", "founding_progress"]
    old = [(_d(90), {"queen": "seen", "workers": 40, "eggs": 1})]
    keys = _keys(ants.ant_insights(ants.colony_state(old, cfg, _d(200), NOW), cfg, False, NOW))
    assert "queen_not_seen" in keys
    # In winterrust geen alarm over de koningin
    assert "queen_not_seen" not in _keys(ants.ant_insights(ants.colony_state(old, cfg, _d(200), NOW), cfg, True, NOW))
    dead = [(_d(1), {"queen": "dead", "workers": 40, "eggs": 0, "larvae": 0, "pupae": 0})]
    keys = _keys(ants.ant_insights(ants.colony_state(dead, cfg, _d(200), NOW), cfg, False, NOW))
    assert "queen_dead" in keys and "no_brood" in keys
    slow = [(_d(90), {"queen": "seen", "eggs": 2})]
    keys = _keys(ants.ant_insights(ants.colony_state(slow, cfg, _d(100), NOW), cfg, False, NOW))
    assert "founding_slow" in keys
    larvae = [(_d(1), {"queen": "seen", "workers": 40, "larvae": 3})]
    assert "larvae_protein" in _keys(ants.ant_insights(ants.colony_state(larvae, cfg, _d(200), NOW), cfg, False, NOW))


def test_nest_modules():
    raw = [{"name": "Kamer 1", "kind": "chamber", "role": "brood", "humidity_sensor": "sensor.h1",
            "humidity_min": 75, "temperature_sensor": "light.niet"},
           {"name": "Kamer 2", "wet_every_days": 7, "kind": "raar"},
           {"name": ""}]
    mods = nest_modules.clean_modules(raw)
    assert [m["name"] for m in mods] == ["Kamer 1", "Kamer 2"]
    assert "temperature_sensor" not in mods[0] and mods[1]["kind"] == "chamber" and mods[0]["id"]
    # wetted_at blijft bewaard bij opnieuw opslaan
    mods[1]["wetted_at"] = _d(2).isoformat()
    again = nest_modules.clean_modules([{k: v for k, v in m.items() if k != "wetted_at"} for m in mods], mods)
    assert again[1]["wetted_at"] == _d(2).isoformat()
    assert nest_modules.module_sensors(mods) == {"sensor.h1"}
    # Op sensor: droog → vervaldag = sinds wanneer droog
    due, dry = nest_modules.wet_due(mods[0], {"humidity": 60}, None, _d(30), NOW)
    assert due == NOW and dry == NOW
    assert nest_modules.wet_due(mods[0], {"humidity": 80}, NOW, _d(30), NOW) == (None, None)
    # Geen meting: interval vanaf laatste bevochtiging
    due, _ = nest_modules.wet_due(again[1], {}, None, _d(30), NOW)
    assert due == _d(2) + timedelta(days=7)
