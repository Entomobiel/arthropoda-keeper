"""WebSocket-API die het paneel en de kaarten gebruiken."""

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.arthropoda.const import DOMAIN

SHEET = """
species: {scientific_name: Brachypelma hamorii, group: tarantula, development: molting_adult}
care_profiles: [{temp_day: [22, 26], humidity: [55, 70], feeding_interval_days: 14}]
"""


async def _setup(hass: HomeAssistant):
    await async_setup_component(hass, "websocket_api", {})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "C"})
    await hass.async_block_till_done()
    return result["result"]


async def test_full_websocket_flow(hass: HomeAssistant, hass_ws_client) -> None:
    hass.states.async_set("sensor.t", "24", {"unit_of_measurement": "°C"})
    entry = await _setup(hass)
    ws = await hass_ws_client(hass)

    async def call(**msg):
        await ws.send_json_auto_id(msg)
        return await ws.receive_json()

    # Soort opslaan, lijst, ophalen
    res = await call(type="arthropoda/species/save", yaml=SHEET)
    assert res["success"] and res["result"]["saved"] == ["Brachypelma hamorii"]
    res = await call(type="arthropoda/species/list")
    (species,) = res["result"]["species"]
    res = await call(type="arthropoda/species/get", species_id=species["id"])
    assert "Brachypelma hamorii" in res["result"]["yaml"]

    # Labels
    res = await call(type="arthropoda/meta", language="nl")
    assert res["result"]["labels"]["entry_type"]["feeding"] == "Gevoederd"
    assert res["result"]["collection"] == "C"

    # Dier toevoegen via het paneel
    res = await call(
        type="arthropoda/animal/add",
        data={"name": "Rosie", "species_id": species["id"], "kind": "individual",
              "sex": "female", "stage": "adult", "instar": 9,
              "temperature_sensors": ["sensor.t"], "humidity_sensor": "",
              "food_plants": ["plant.braam"]},
    )
    assert res["success"], res
    animal_id = res["result"]["animal_id"]
    await hass.async_block_till_done()

    res = await call(type="arthropoda/animals")
    (animal,) = res["result"]["animals"]
    assert animal["id"] == animal_id
    assert animal["name"] == "Rosie"
    assert animal["readings"]["temperature"] == 24
    assert animal["targets"]["temperature"] in ([22, 26], [22.0, 26.0])
    assert animal["entities"]["status"] == "sensor.rosie_status"
    assert animal["device_id"]
    assert "humidity_sensor" not in animal["config"]  # lege waarde niet bewaard
    assert animal["config"]["food_plants"] == ["plant.braam"]

    # Abonnement: meteen een eerste lijst, en opnieuw na een dagboekregel
    await ws.send_json_auto_id({"type": "arthropoda/subscribe"})
    sub_id = (await ws.receive_json())["id"]
    first = await ws.receive_json()
    assert first["id"] == sub_id and first["event"]["animals"][0]["name"] == "Rosie"

    res = await call(type="arthropoda/journal/add", animal_ids=[animal_id], entry_type="molt",
                     notes="Mooi", data={"legspan_mm": 120})
    # Het antwoord en een of meer updates kunnen in willekeurige volgorde komen
    msgs = [res]
    while not any(m.get("type") == "result" and m.get("success") for m in msgs):
        msgs.append(await ws.receive_json())
    await hass.async_block_till_done()

    res = await call(type="arthropoda/journal/list", animal_id=animal_id)
    while res.get("type") != "result":
        res = await ws.receive_json()
    (entry_row,) = res["result"]["entries"]
    assert entry_row["type"] == "molt" and entry_row["notes"] == "Mooi"

    # Wijzigen: naam en stadium
    res = await call(
        type="arthropoda/animal/update", animal_id=animal_id,
        data={**animal["config"], "name": "Rosie II", "instar": 12, "sex": "female",
              "stage": "adult"},
    )
    while res.get("type") != "result":
        res = await ws.receive_json()
    assert res["success"], res
    await hass.async_block_till_done()
    assert entry.subentries[animal_id].title == "Rosie II"
    animal_db = await hass.async_add_executor_job(entry.runtime_data.db.get_animal, animal_id)
    assert animal_db.instar == 12

    # Soort in gebruik kan niet verwijderd worden
    res = await call(type="arthropoda/species/delete", species_id=species["id"])
    while res.get("type") != "result":
        res = await ws.receive_json()
    assert not res["success"] and res["error"]["code"] == "in_use"

    # Ongeldige vervelling wordt netjes geweigerd
    res = await call(type="arthropoda/journal/add", animal_ids=[animal_id],
                     entry_type="stage_change", data={"stage": "volwassen"})
    while res.get("type") != "result":
        res = await ws.receive_json()
    assert not res["success"] and res["error"]["code"] == "invalid"
