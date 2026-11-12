"""Fase 8: planten uit Plant Monitor in kasten, plantenkasten sturen, plantendagboek."""

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from test_enclosures import TEMP, _setup


def _fake_plant(hass: HomeAssistant, slug: str, name: str, temp: tuple, hum: tuple) -> str:
    """Bootst een Plant Monitor-plant na: plant.* plus min/max number-entiteiten."""
    entry = MockConfigEntry(domain="plant", title=name)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    plant = registry.async_get_or_create("plant", "plant", entry.entry_id, config_entry=entry,
                                         suggested_object_id=slug).entity_id
    hass.states.async_set(plant, "ok", {"friendly_name": name, "species": "Rubus fruticosus",
                                        "moisture_status": "Low", "problems": ["moisture low"]})
    for quantity, (lo, hi) in (("temperature", temp), ("humidity", hum)):
        for side, value in (("min", lo), ("max", hi)):
            number = registry.async_get_or_create(
                "number", "plant", f"{entry.entry_id}-{side}-{quantity}", config_entry=entry,
                suggested_object_id=f"{slug}_{side}_{quantity}",
            ).entity_id
            hass.states.async_set(number, str(value), TEMP if quantity == "temperature" else {})
    return plant


async def test_plant_cabinet_climate_and_journal(hass: HomeAssistant, hass_ws_client) -> None:
    turn_on = async_mock_service(hass, "input_boolean", "turn_on")
    turn_off = async_mock_service(hass, "input_boolean", "turn_off")
    hass.states.async_set("sensor.ikea_temp", "16", TEMP)
    hass.states.async_set("input_boolean.ikea_heater", "off")
    braam = _fake_plant(hass, "braam", "Braam", (18, 26), (40, 70))
    eik = _fake_plant(hass, "eik", "Eik", (15, 24), (40, 80))
    _, call, add, _ = await _setup(hass, hass_ws_client)

    res = await call(type="arthropoda/enclosure/save", item={
        "code": "PK-01", "name": "IKEA plantenkast", "type": "plant_cabinet",
        "config": {"temperature_sensors": ["sensor.ikea_temp"], "heater": "input_boolean.ikea_heater",
                   "plants": [braam, eik, "sensor.geen_plant"], "light_hours": 14},
    })
    assert res["success"], res
    enc_id = res["result"]["id"]
    await hass.async_block_till_done()

    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    assert enc["type"] == "plant_cabinet" and enc["plant_cabinet"] is True
    assert enc["config"]["plants"] == [braam, eik]  # geen plant.* → weggelaten
    assert enc["config"]["light_hours"] == 14
    assert enc["readings"]["temperature"] == 16
    plants = {p["entity_id"]: p for p in enc["plants"]}
    assert plants[braam]["name"] == "Braam" and plants[braam]["problems"] == ["moisture low"]
    assert plants[braam]["thresholds"] == {"temperature": [18, 26], "humidity": [40, 70]}
    assert plants[braam]["statuses"] == {"moisture": "Low"}
    # Overlap van 18–26 en 15–24 = 18–24; 16 °C is te koud → verwarming aan
    assert any("input_boolean.ikea_heater" in str(c.data.get("entity_id")) for c in turn_on)
    (heater,) = enc["actuators"]
    assert heater["target"] == [18, 24] and sorted(heater["members"]) == sorted(
        [f"plant:{enc_id}:{braam}", f"plant:{enc_id}:{eik}"]
    )

    # Plantendagboek
    res = await call(type="arthropoda/plant/log", plants=[braam, eik], entry_type="watered",
                     enclosure_id=enc_id, notes="regenwater")
    assert res["success"], res
    res = await call(type="arthropoda/plant/log", plants=[braam], entry_type="harvested")
    assert res["success"], res
    entries = (await call(type="arthropoda/plant/journal", plants=[braam]))["result"]["entries"]
    assert [e["type"] for e in entries] == ["harvested", "watered"]
    assert entries[1]["notes"] == "regenwater" and entries[1]["enclosure_id"] == enc_id
    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    plants = {p["entity_id"]: p for p in enc["plants"]}
    assert set(plants[braam]["last"]) == {"watered", "harvested"}
    assert set(plants[eik]["last"]) == {"watered"}
    res = await call(type="arthropoda/plant/log", plants=["sensor.x"], entry_type="watered")
    assert not res["success"]
    res = await call(type="arthropoda/plant/entry/delete", entry_id=entries[0]["id"])
    assert res["success"]
    entries = (await call(type="arthropoda/plant/journal", plants=[braam]))["result"]["entries"]
    assert [e["type"] for e in entries] == ["watered"]

    # Een dier in de kast → planten zijn voedsel en sturen niet meer
    turn_on.clear()
    animal = await add("Wandelende takken")
    res = await call(type="arthropoda/enclosure/assign", animal_id=animal, enclosure_id=enc_id)
    assert res["success"], res
    await hass.async_block_till_done()
    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    assert enc["plant_cabinet"] is False and enc["actuators"] == []
    assert len(enc["plants"]) == 2  # wel nog zichtbaar
    animals = {x["id"]: x for x in (await call(type="arthropoda/animals"))["result"]["animals"]}
    heater = animals[animal]["climate"]["actuators"][0]
    assert heater["members"] == [animal]  # alleen het dier (caresheet 24–28 °C)
    assert heater["target"] == [24, 28]

    # Plantensturing uitzetten in een kast zonder dieren
    await call(type="arthropoda/enclosure/assign", animal_id=animal, enclosure_id=None)
    res = await call(type="arthropoda/enclosure/save", item={
        "id": enc_id, "code": "PK-01", "type": "plant_cabinet",
        "config": {"temperature_sensors": ["sensor.ikea_temp"], "heater": "input_boolean.ikea_heater",
                   "plants": [braam], "plant_climate": False},
    })
    assert res["success"], res
    await hass.async_block_till_done()
    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    assert enc["plant_cabinet"] is False and enc["config"]["plant_climate"] is False
    assert turn_off is not None


async def test_plant_care_tasks(hass: HomeAssistant, hass_ws_client) -> None:
    """Sproeien/bemesten per plant: taak, afhandelen via het logboek, scanbewijs."""
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    gras = _fake_plant(hass, "gras", "Gras", (15, 25), (40, 80))
    eik = _fake_plant(hass, "eik", "Eik", (15, 24), (40, 80))
    entry, call, _add, _ = await _setup(hass, hass_ws_client)

    res = await call(type="arthropoda/enclosure/save", item={
        "code": "PK-02", "type": "plant_cabinet", "nfc_tag": "TAG-PK",
        "config": {"plants": [gras, eik], "plant_care": {
            gras: {"plant_water": 1, "plant_fertilize": 14},
            eik: {"plant_water": "", "plant_fertilize": 0},     # leeg/0 → geen taak
            "plant.weg": {"plant_water": 1},                    # niet in de kast → weg
        }},
    })
    assert res["success"], res
    enc_id = res["result"]["id"]
    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    assert enc["config"]["plant_care"] == {gras: {"plant_water": 1, "plant_fertilize": 14}}
    tasks = {t["kind"]: t for t in enc["tasks"]}
    assert set(tasks) == {"plant_water", "plant_fertilize"}
    water = tasks["plant_water"]
    assert water["plant"] == gras and water["label"] == "Gras"
    assert water["uid"] == f"enc{enc_id}:plant_water:{gras}"
    # Nog nooit gedaan → vandaag te doen
    assert dt_util.parse_datetime(water["due"]).date() == dt_util.now().date()

    # Sproeien noteren op het werkscherm → volgende keer morgen
    res = await call(type="arthropoda/plant/log", plants=[gras], entry_type="watered", enclosure_id=enc_id)
    assert res["success"], res
    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    water = next(t for t in enc["tasks"] if t["kind"] == "plant_water")
    assert dt_util.parse_datetime(water["due"]).date() == dt_util.now().date() + timedelta(days=1)

    # Afvinken in de takenlijst = 'bemest' in het plantenlogboek
    fert = next(t for t in enc["tasks"] if t["kind"] == "plant_fertilize")
    assert (await call(type="arthropoda/task/done", uid=fert["uid"]))["success"]
    entries = (await call(type="arthropoda/plant/journal", plants=[gras]))["result"]["entries"]
    assert [e["type"] for e in entries] == ["fertilized", "watered"]

    # Over tijd + aandringen met scanbewijs: sproeien pas na een scan van de kast
    runtime = entry.runtime_data
    await hass.async_add_executor_job(
        runtime.db.add_plant_entries, [gras], "watered", dt_util.utcnow() - timedelta(days=3), None, enc_id, {}
    )
    # (de recente sproeibeurt weghalen zodat de laatste 3 dagen oud is)
    watered = [e for e in (await call(type="arthropoda/plant/journal", plants=[gras]))["result"]["entries"]
               if e["type"] == "watered"]
    assert (await call(type="arthropoda/plant/entry/delete", entry_id=watered[0]["id"]))["success"]
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "nag_enabled": True, "require_scan": True}
    )
    await hass.async_block_till_done()
    await entry.runtime_data.coordinator.async_refresh()
    res = await call(type="arthropoda/plant/log", plants=[gras], entry_type="watered", enclosure_id=enc_id)
    assert not res["success"] and "PK-02" in res["error"]["message"]
    # Andere handelingen (snoeien) mogen gewoon
    assert (await call(type="arthropoda/plant/log", plants=[gras], entry_type="pruned"))["success"]
    hass.bus.async_fire("tag_scanned", {"tag_id": "TAG-PK", "device_id": None})
    await hass.async_block_till_done()
    res = await call(type="arthropoda/plant/log", plants=[gras], entry_type="watered", enclosure_id=enc_id)
    assert res["success"], res
