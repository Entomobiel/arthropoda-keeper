"""Fase 7: kasten, klimaat via de kast, taken per kast, NFC."""

from datetime import timedelta

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.arthropoda.const import DOMAIN

SHEET = """
species:
  scientific_name: Gromphadorhina portentosa
  group: roach
  feeder: true
  enclosure: {min_size_cm: [40, 30, 30]}
care_profiles: [{temp_day: [24, 28], humidity: [60, 70], cleaning_interval_days: 7}]
"""
TEMP = {"unit_of_measurement": "°C", "device_class": "temperature"}


async def _setup(hass: HomeAssistant, ws_client):
    await async_setup_component(hass, "websocket_api", {})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "C"})
    await hass.async_block_till_done()
    ws = await ws_client(hass)

    async def call(**msg):
        await ws.send_json_auto_id(msg)
        while True:
            res = await ws.receive_json()
            if res.get("type") == "result":
                return res

    await call(type="arthropoda/species/save", yaml=SHEET)
    (species,) = (await call(type="arthropoda/species/list"))["result"]["species"]

    async def add(name):
        res = await call(type="arthropoda/animal/add",
                         data={"name": name, "species_id": species["id"], "kind": "colony"})
        await hass.async_block_till_done()
        return res["result"]["animal_id"]

    return result["result"], call, add, ws


async def test_enclosure_climate_tasks_and_size(hass: HomeAssistant, hass_ws_client) -> None:
    turn_on = async_mock_service(hass, "input_boolean", "turn_on")
    async_mock_service(hass, "input_boolean", "turn_off")
    hass.states.async_set("sensor.pico_temp", "22", TEMP)
    hass.states.async_set("input_boolean.pico_heater", "off")
    entry, call, add, _ = await _setup(hass, hass_ws_client)
    a = await add("Sisskakkerlakken A")
    b = await add("Sisskakkerlakken B")

    res = await call(type="arthropoda/enclosure/save", item={
        "code": "KB-01", "name": "Kweekkast 1", "type": "breeding_box",
        "length_cm": 30, "width_cm": 30, "height_cm": 30,
        "config": {"temperature_sensors": ["sensor.pico_temp"], "heater": "input_boolean.pico_heater"},
        "equipment": [{"name": "Warmtemat", "interval_days": 30,
                       "serviced_at": (dt_util.now().date() - timedelta(days=40)).isoformat()}],
    })
    assert res["success"], res
    enc_id = res["result"]["id"]
    for animal in (a, b):
        res = await call(type="arthropoda/enclosure/assign", animal_id=animal, enclosure_id=enc_id)
        assert res["success"], res
    await hass.async_block_till_done()

    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    assert enc["code"] == "KB-01" and sorted(enc["residents"]) == sorted([a, b])
    assert enc["volume_l"] == 27.0
    assert enc["link"] == "homeassistant://navigate/arthropoda?enclosure=KB-01"
    # Klimaat komt van de kast: meting en verwarming
    assert enc["readings"]["temperature"] == 22
    assert any("input_boolean.pico_heater" in str(c.data.get("entity_id")) for c in turn_on)
    animals = {x["id"]: x for x in (await call(type="arthropoda/animals"))["result"]["animals"]}
    assert animals[a]["climate_config"]["climate_from_enclosure"] == enc_id
    assert "heater" not in animals[a]["config"]  # eigen configuratie onaangetast
    # Kast te klein (30 cm < 40 cm minimum)
    assert "enclosure_too_small" in animals[a]["problems"]
    assert sorted(enc["too_small_for"]) == ["Sisskakkerlakken A", "Sisskakkerlakken B"]
    # Verhuis staat in het dagboek
    journal = (await call(type="arthropoda/journal/list", animal_id=a))["result"]["entries"]
    assert journal[0]["type"] == "rehouse" and journal[0]["data"]["to"] == "KB-01"

    # Eén schoonmaaktaak voor de kast, geen per dier; uitrusting vervallen
    kinds = {(t["kind"], t["label"]) for t in enc["tasks"]}
    assert ("cleaning", None) in kinds and ("equipment", "Warmtemat") in kinds
    assert not [t for t in animals[a]["tasks"] if t["kind"] == "cleaning"]
    items = (await hass.services.async_call(
        "todo", "get_items", {"entity_id": "todo.c_maintenance"}, blocking=True, return_response=True
    ))["todo.c_maintenance"]["items"]
    equipment = next(i for i in items if i["uid"].startswith(f"enc{enc_id}:equipment"))
    assert "Warmtemat" in equipment["summary"] and "KB-01" in equipment["summary"]

    # Taak afvinken → onderhoud genoteerd, taak weg
    res = await call(type="arthropoda/task/done", uid=equipment["uid"])
    assert res["success"], res
    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    assert enc["equipment"][0]["serviced_at"] == dt_util.now().date().isoformat()
    (next_service,) = [t for t in enc["tasks"] if t["kind"] == "equipment"]
    assert dt_util.parse_datetime(next_service["due"]).date() == dt_util.now().date() + timedelta(days=30)

    # Handeling via de kast → voor alle bewoners
    res = await call(type="arthropoda/enclosure/log", enclosure_id=enc_id, entry_type="spot_clean")
    assert res["success"] and sorted(res["result"]["animals"]) == sorted([a, b])
    for animal in (a, b):
        journal = (await call(type="arthropoda/journal/list", animal_id=animal))["result"]["entries"]
        assert journal[0]["type"] == "spot_clean" and journal[0]["data"]["enclosure_id"] == enc_id
    # Alleen voor één bewoner
    res = await call(type="arthropoda/enclosure/log", enclosure_id=enc_id, entry_type="feeding",
                     animal_ids=[b])
    assert res["result"]["animals"] == [b]

    # Code moet uniek zijn
    res = await call(type="arthropoda/enclosure/save", item={"code": "kb-01"})
    assert not res["success"] and "kb-01" in res["error"]["message"].lower()

    # Kast verwijderen → dieren blijven, zonder kast
    await call(type="arthropoda/enclosure/delete", enclosure_id=enc_id)
    animals = {x["id"]: x for x in (await call(type="arthropoda/animals"))["result"]["animals"]}
    assert animals[a]["enclosure_id"] is None
    assert "climate_from_enclosure" not in animals[a]["climate_config"]


async def test_nfc_tag_opens_work_screen(hass: HomeAssistant, hass_ws_client) -> None:
    notify = async_mock_service(hass, "notify", "mobile_app_gsm_van_jan")
    entry, call, add, ws = await _setup(hass, hass_ws_client)
    rosie = await add("Kakkerlakken")
    phone_entry = MockConfigEntry(domain="mobile_app")
    phone_entry.add_to_hass(hass)
    phone = dr.async_get(hass).async_get_or_create(
        config_entry_id=phone_entry.entry_id, identifiers={("mobile_app", "abc")}, name="Gsm van Jan"
    )

    # Koppelen: luisteren naar de volgende scan
    await ws.send_json_auto_id({"type": "arthropoda/nfc/listen"})
    sub = await ws.receive_json()
    assert sub["success"]
    hass.bus.async_fire("tag_scanned", {"tag_id": "TAG-123", "device_id": phone.id})
    event = await ws.receive_json()
    assert event["event"]["tag_id"] == "TAG-123"

    res = await call(type="arthropoda/enclosure/save",
                     item={"code": "T-07", "name": "Terrarium 7", "nfc_tag": "TAG-123"})
    enc_id = res["result"]["id"]
    await call(type="arthropoda/enclosure/assign", animal_id=rosie, enclosure_id=enc_id)

    # Scannen → melding naar die gsm met link naar het werkscherm
    scanned = []
    hass.bus.async_listen("arthropoda_enclosure_scanned", lambda e: scanned.append(e.data))
    hass.bus.async_fire("tag_scanned", {"tag_id": "TAG-123", "device_id": phone.id})
    await hass.async_block_till_done()
    assert scanned and scanned[0]["code"] == "T-07"
    (msg,) = notify
    assert msg.data["title"] == "T-07 – Terrarium 7"
    assert msg.data["message"] == "Kakkerlakken"
    assert msg.data["data"]["clickAction"] == "/arthropoda?enclosure=T-07"
    assert msg.data["data"]["url"] == "/arthropoda?enclosure=T-07"

    # Dezelfde tag mag niet aan twee kasten
    res = await call(type="arthropoda/enclosure/save", item={"code": "T-08", "nfc_tag": "TAG-123"})
    assert not res["success"] and "T-07" in res["error"]["message"]

    # Onbekende tag → niets
    hass.bus.async_fire("tag_scanned", {"tag_id": "ANDERE", "device_id": phone.id})
    await hass.async_block_till_done()
    assert len(notify) == 1
