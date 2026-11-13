"""Mierenmodule in HA: kolonie, telling, voedselstromen, stichting, nestmodules."""

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.arthropoda.const import DOMAIN

MESSOR = """
species:
  scientific_name: Messor barbarus
  group: ant
  ant: {type: harvester, founding: claustral, polymorphic: true,
        development_days: {egg: [10, 14], larva: [14, 20], pupa: [14, 20]}}
care_profiles: [{temp_day: [24, 28]}]
"""


async def test_ant_colony_flow(hass: HomeAssistant, hass_ws_client) -> None:
    await async_setup_component(hass, "websocket_api", {})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "C"})
    await hass.async_block_till_done()
    entry = result["result"]
    ws = await hass_ws_client(hass)

    async def call(**msg):
        await ws.send_json_auto_id(msg)
        while True:
            res = await ws.receive_json()
            if res.get("type") == "result":
                return res

    assert (await call(type="arthropoda/species/save", yaml=MESSOR))["success"]
    (species,) = (await call(type="arthropoda/species/list"))["result"]["species"]
    caught = (dt_util.now().date() - timedelta(days=20)).isoformat()
    res = await call(type="arthropoda/animal/add", data={
        "name": "Messor Q1", "species_id": species["id"], "kind": "colony",
        "acquired_at": caught, "origin": "wild_caught"})
    await hass.async_block_till_done()
    q1 = res["result"]["animal_id"]
    assert (await call(type="arthropoda/ant/update", animal_id=q1,
                       changes={"caught_place": "Montpellier"}))["success"]

    async def colony():
        animals = (await call(type="arthropoda/animals"))["result"]["animals"]
        return next(a for a in animals if a["id"] == q1)

    # Pas gevangen, claustraal: stichtingsfase, geen voedertaken
    a = await colony()
    assert a["ant"]["state"]["stage"] == "founding"
    assert a["ant"]["settings"]["caught_place"] == "Montpellier" and a["ant"]["settings"]["type"] == "harvester"
    assert not [t for t in a["tasks"] if t["kind"].startswith("ant_") or t["kind"] == "feeding"]
    keys = [i["key"] for i in a["insights"]]
    assert "claustral_founding" in keys and "founding_progress" in keys

    # Telling met eerste werksters → nanitics, voedselstromen (water, zaden, eiwit)
    assert (await call(type="arthropoda/journal/add", animal_ids=[q1], entry_type="census",
                       data={"queen": "seen", "workers": 8, "eggs": 2, "larvae": 3, "pupae": 1}))["success"]
    a = await colony()
    assert a["ant"]["state"]["stage"] == "nanitics" and a["ant"]["state"]["workers"] == 8 and a["count"] == 8
    kinds = {t["kind"] for t in a["tasks"]}
    assert {"ant_water", "ant_seeds", "ant_protein"} <= kinds and "feeding" not in kinds
    # Veel larven → eiwit vaker
    assert a["ant"]["intervals"]["protein"] < a["ant"]["settings"]["food"]["protein"]

    # Zaden geven → zadentaak schuift op; eiwit → restjes-taak
    assert (await call(type="arthropoda/journal/add", animal_ids=[q1], entry_type="feed_seeds"))["success"]
    assert (await call(type="arthropoda/journal/add", animal_ids=[q1], entry_type="feeding"))["success"]
    a = await colony()
    seeds = next(t for t in a["tasks"] if t["kind"] == "ant_seeds")
    assert dt_util.parse_datetime(seeds["due"]).date() == dt_util.now().date() + timedelta(days=7)
    assert any(t["kind"] == "ant_leftovers" for t in a["tasks"])
    assert "seeds" in a["ant"]["last"]
    # Taak 'resten verwijderen' afvinken
    left = next(t for t in a["tasks"] if t["kind"] == "ant_leftovers")
    assert (await call(type="arthropoda/task/done", uid=left["uid"]))["success"]
    a = await colony()
    assert not any(t["kind"] == "ant_leftovers" for t in a["tasks"])

    # Suiker toevoegen, eiwit uitzetten per kolonie
    assert (await call(type="arthropoda/ant/update", animal_id=q1,
                       changes={"food": {"sugar": 10, "protein": 0}}))["success"]
    a = await colony()
    assert "sugar" in a["ant"]["settings"]["food"] and "protein" not in a["ant"]["settings"]["food"]

    # Lade met gipsmodules: sensor + interval
    hass.states.async_set("sensor.kamer1_vocht", "60", {"unit_of_measurement": "%"})
    res = await call(type="arthropoda/enclosure/save", item={"code": "L-01", "type": "formicarium", "config": {
        "modules": [
            {"name": "Kamer 1", "role": "brood", "humidity_sensor": "sensor.kamer1_vocht", "humidity_min": 75},
            {"name": "Kamer 2", "wet_every_days": 5},
            {"name": "Foerageerbak", "kind": "outworld"},
        ]}})
    assert res["success"], res
    enc_id = res["result"]["id"]
    encs = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    enc = next(e for e in encs if e["id"] == enc_id)
    assert [m["name"] for m in enc["modules"]] == ["Kamer 1", "Kamer 2", "Foerageerbak"]
    assert enc["modules"][0]["values"]["humidity"] == 60
    wet = sorted((t for t in enc["tasks"] if t["kind"] == "module_wet"), key=lambda t: t["label"])
    assert [t["label"] for t in wet] == ["Kamer 1", "Kamer 2"]
    # Kamer 1 te droog → nu; bevochtigd + sensor stijgt → taak weg
    assert (await call(type="arthropoda/module/wetted", enclosure_id=enc_id, index=0))["success"]
    hass.states.async_set("sensor.kamer1_vocht", "85", {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    await entry.runtime_data.coordinator.async_refresh()
    encs = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    enc = next(e for e in encs if e["id"] == enc_id)
    assert [t["label"] for t in enc["tasks"] if t["kind"] == "module_wet"] == ["Kamer 2"]
    assert enc["modules"][0]["wetted_at"]
    # Kamer 2 afvinken via de takenlijst → volgende keer over 5 dagen
    k2 = next(t for t in enc["tasks"] if t["kind"] == "module_wet")
    assert (await call(type="arthropoda/task/done", uid=k2["uid"]))["success"]
    encs = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    enc = next(e for e in encs if e["id"] == enc_id)
    k2 = next(t for t in enc["tasks"] if t["kind"] == "module_wet")
    assert dt_util.parse_datetime(k2["due"]).date() == dt_util.now().date() + timedelta(days=5)

    # Koningin dood gemeld → waarschuwing
    assert (await call(type="arthropoda/journal/add", animal_ids=[q1], entry_type="census",
                       data={"queen": "dead", "workers": 6}))["success"]
    a = await colony()
    assert "queen_dead" in [i["key"] for i in a["insights"]]
