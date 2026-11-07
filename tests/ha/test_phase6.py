"""Fase 6 in HA: kweek, stamboom, voorraad, documenten, opvolging."""

from datetime import timedelta
from http import HTTPStatus

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.arthropoda.const import DOMAIN

SHEET = """
species:
  scientific_name: Sphodromantis lineola
  group: mantis
  development: hemimetabolous
  incubation_days: [28, 42]
care_profiles: [{feeding_interval_days: 3}]
"""


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

    async def add(data):
        res = await call(type="arthropoda/animal/add", data={"species_id": species["id"], **data})
        assert res["success"], res
        await hass.async_block_till_done()
        return res["result"]["animal_id"]

    return result["result"], call, add


async def test_breeding_and_lineage(hass: HomeAssistant, hass_ws_client) -> None:
    entry, call, add = await _setup(hass, hass_ws_client)
    female = await add({"name": "Vrouw", "sex": "female", "stage": "adult"})
    male = await add({"name": "Man", "sex": "male", "stage": "adult"})

    await call(type="arthropoda/journal/add", animal_ids=[female], entry_type="pairing",
               data={"partner_id": male, "outcome": "success"})
    laid = dt_util.utcnow() - timedelta(days=25)
    await call(type="arthropoda/journal/add", animal_ids=[female], entry_type="ootheca",
               timestamp=laid.isoformat(), data={"father_id": male})
    await hass.async_block_till_done()

    res = await call(type="arthropoda/breeding/list")
    (brood,) = res["result"]["broods"]
    assert brood["status"] == "incubating" and brood["expected"]
    assert res["result"]["pairings"][0]["partner_id"] == male

    # Uitkomst over 3 dagen → in de kalender en in de samenvatting
    coordinator = entry.runtime_data.coordinator
    assert [b["id"] for b in coordinator.broods_due()] == [brood["id"]]
    events = await hass.services.async_call(
        "calendar", "get_events",
        {"entity_id": "calendar.c_calendar", "start_date_time": dt_util.now(),
         "end_date_time": dt_util.now() + timedelta(days=30)},
        blocking=True, return_response=True,
    )
    assert any("Vrouw" in e["summary"] and "ootheca" in e["summary"].lower()
               for e in events["calendar.c_calendar"]["events"])

    # Uitgekomen → nakomelingen registreren met ouders en generatie
    await call(type="arthropoda/brood/update", brood_id=brood["id"], status="hatched", count_hatched=60)
    kids = await add({"name": "L1 lineola", "kind": "colony", "count": 60, "stage": "nymph",
                      "mother_id": female, "father_id": male, "generation": "F1",
                      "brood_id": brood["id"]})
    animals = {a["id"]: a for a in (await call(type="arthropoda/animals"))["result"]["animals"]}
    assert animals[kids]["lineage"]["generation"] == "F1"
    assert animals[kids]["lineage"]["mother_id"] == female
    assert animals[female]["lineage"]["children"] == [kids]
    assert animals[male]["lineage"]["children"] == [kids]
    db_kids = await hass.async_add_executor_job(entry.runtime_data.db.get_animal, kids)
    assert db_kids.mother_id == female and db_kids.generation == "F1"

    # Wijzigen via het tandwiel (HA-formulier) behoudt de stamboom
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, "animal"),
                                   context={"source": "reconfigure", "subentry_id": kids})
    result = await flow.async_configure(result["flow_id"], {
        "name": "L1 lineola", "species_id": animals[kids]["config"]["species_id"],
        "kind": "colony", "sex": "mixed"})
    result = await flow.async_configure(result["flow_id"], {})
    result = await flow.async_configure(result["flow_id"], {})
    assert result["reason"] == "reconfigure_successful"
    assert entry.subentries[kids].data["mother_id"] == female
    assert entry.subentries[kids].data["generation"] == "F1"


async def test_stock(hass: HomeAssistant, hass_ws_client) -> None:
    entry, call, add = await _setup(hass, hass_ws_client)
    mantis = await add({"name": "Mantis"})
    colony = await add({"name": "Fruitvliegjes", "kind": "colony", "count": 500})

    res = await call(type="arthropoda/stock/save",
                     item={"name": "Huisvlieg", "quantity": 30, "min_quantity": 25, "unit": "st"})
    stock_id = res["result"]["id"]
    res = await call(type="arthropoda/stock/save",
                     item={"name": "Eigen fruitvliegjes", "quantity": 500, "colony_id": colony})
    colony_stock = res["result"]["id"]

    await call(type="arthropoda/journal/add", animal_ids=[mantis], entry_type="feeding",
               data={"stock_id": stock_id, "quantity": 10})
    await call(type="arthropoda/journal/add", animal_ids=[mantis], entry_type="feeding",
               data={"stock_id": colony_stock, "quantity": 20})
    await hass.async_block_till_done()

    stock = {s["id"]: s for s in (await call(type="arthropoda/stock/list"))["result"]["stock"]}
    assert stock[stock_id]["quantity"] == 20
    low = hass.states.get("sensor.c_low_stock")
    assert low.state == "1" and low.attributes["items"][0]["name"] == "Huisvlieg"
    animals = {a["id"]: a for a in (await call(type="arthropoda/animals"))["result"]["animals"]}
    assert animals[colony]["count"] == 480  # kolonie mee verminderd

    res = await call(type="arthropoda/stock/adjust", stock_id=stock_id, delta=50)
    assert res["result"]["quantity"] == 70
    await hass.async_block_till_done()
    assert hass.states.get("sensor.c_low_stock").state == "0"


async def test_documents(hass: HomeAssistant, hass_ws_client, hass_client) -> None:
    await async_setup_component(hass, "http", {})
    entry, call, add = await _setup(hass, hass_ws_client)
    rosie = await add({"name": "Rosie", "seller": "Kweker Jan", "price": 25})
    client = await hass_client()

    form = aiohttp.FormData()
    form.add_field("animal_id", rosie)
    form.add_field("type", "cites")
    form.add_field("title", "CITES-certificaat")
    form.add_field("expires_at", (dt_util.now().date() + timedelta(days=10)).isoformat())
    form.add_field("file", b"%PDF-1.4 cites", filename="cites.pdf", content_type="application/pdf")
    resp = await client.post("/api/arthropoda/document", data=form)
    assert resp.status == HTTPStatus.OK, await resp.text()
    await hass.async_block_till_done()

    (doc,) = (await call(type="arthropoda/documents/list", animal_id=rosie))["result"]["documents"]
    assert doc["title"] == "CITES-certificaat" and "authSig=" in doc["url"]
    # Ondertekende link werkt zonder aanmelding
    anon = await hass_client()
    resp = await anon.get(doc["url"])
    assert resp.status == HTTPStatus.OK
    assert await resp.read() == b"%PDF-1.4 cites"

    # Vervalt binnen 30 dagen → samenvatting
    assert [d["id"] for d in entry.runtime_data.coordinator.expiring_documents()] == [doc["id"]]
    res = await hass.services.async_call(DOMAIN, "send_digest", {}, blocking=True, return_response=True)
    assert res["sent"] is True

    animals = {a["id"]: a for a in (await call(type="arthropoda/animals"))["result"]["animals"]}
    assert animals[rosie]["config"]["seller"] == "Kweker Jan"
    assert animals[rosie]["config"]["price"] == 25

    await call(type="arthropoda/documents/delete", document_id=doc["id"])
    assert (await call(type="arthropoda/documents/list"))["result"]["documents"] == []


async def test_measurement_history(hass: HomeAssistant, hass_ws_client) -> None:
    _, call, add = await _setup(hass, hass_ws_client)
    rosie = await add({"name": "Rosie", "stage": "nymph"})
    for days, length in ((60, 20), (30, 28), (0, 35)):
        await call(type="arthropoda/journal/add", animal_ids=[rosie], entry_type="measurement",
                   timestamp=(dt_util.utcnow() - timedelta(days=days)).isoformat(),
                   data={"length_mm": length})
    await call(type="arthropoda/journal/add", animal_ids=[rosie], entry_type="molt")
    res = await call(type="arthropoda/measurements/list", animal_id=rosie)
    assert [m["value"] for m in res["result"]["measurements"]] == [20, 28, 35]
    assert len(res["result"]["molts"]) == 1


async def test_diapause_todo_and_calendar(hass: HomeAssistant, hass_ws_client) -> None:
    entry, call, add = await _setup(hass, hass_ws_client)
    await call(type="arthropoda/species/save", yaml=(
        "species: {scientific_name: Lasius niger, group: ant, diapause: {min_days: 90, max_days: 120}}\n"
        "---\n"
        "species: {scientific_name: Acheta domesticus, group: orthoptera, feeder: true}\n"
    ))
    species = {s["scientific_name"]: s for s in (await call(type="arthropoda/species/list"))["result"]["species"]}
    assert species["Acheta domesticus"]["feeder"] is True
    res = await call(type="arthropoda/animal/add",
                     data={"name": "Kolonie", "species_id": species["Lasius niger"]["id"], "kind": "colony"})
    colony = res["result"]["animal_id"]
    await hass.async_block_till_done()

    # 100 dagen geleden in diapauze → vroegste einde (90 d) voorbij → taak vandaag
    started = dt_util.utcnow() - timedelta(days=100)
    await call(type="arthropoda/journal/add", animal_ids=[colony], entry_type="diapause_start",
               timestamp=started.isoformat())
    await hass.async_block_till_done()
    animals = {a["id"]: a for a in (await call(type="arthropoda/animals"))["result"]["animals"]}
    assert animals[colony]["status"] == "diapause" and animals[colony]["diapause"]["earliest_end"]

    items = (await hass.services.async_call(
        "todo", "get_items", {"entity_id": "todo.c_maintenance"}, blocking=True, return_response=True
    ))["todo.c_maintenance"]["items"]
    (item,) = [i for i in items if i["uid"].endswith(":diapause_end")]
    assert "Kolonie" in item["summary"]

    events = (await hass.services.async_call(
        "calendar", "get_events",
        {"entity_id": "calendar.c_calendar", "start_date_time": dt_util.now() - timedelta(days=30),
         "end_date_time": dt_util.now() + timedelta(days=60)},
        blocking=True, return_response=True,
    ))["calendar.c_calendar"]["events"]
    assert any(e["summary"].startswith("Diapause may end: Kolonie") for e in events)

    # Afvinken → diapauze voorbij
    await hass.services.async_call(
        "todo", "update_item",
        {"entity_id": "todo.c_maintenance", "item": item["uid"], "status": "completed"}, blocking=True,
    )
    await hass.async_block_till_done()
    animals = {a["id"]: a for a in (await call(type="arthropoda/animals"))["result"]["animals"]}
    assert animals[colony]["status"] == "active" and animals[colony]["diapause"] is None


async def test_rename_species_and_clean_up_duplicate(hass: HomeAssistant, hass_ws_client) -> None:
    """Hernoemen maakt geen kopie meer; een dubbele soort in gebruik kan opgeruimd worden."""
    entry, call, add = await _setup(hass, hass_ws_client)
    await call(type="arthropoda/species/save",
               yaml="species: {scientific_name: Pieris brasicae, group: lepidoptera}\n")
    species = {s["scientific_name"]: s for s in (await call(type="arthropoda/species/list"))["result"]["species"]}
    old_id = species["Pieris brasicae"]["id"]

    # Situatie van de gebruiker: een dier op de oude soort + een tweede, correcte soort
    rups = await add({"name": "Rupsen 2026", "species_id": old_id, "kind": "colony"})
    await call(type="arthropoda/journal/add", animal_ids=[rups], entry_type="feeding")
    await call(type="arthropoda/species/save",
               yaml="species: {scientific_name: Pieris brassicae, group: lepidoptera}\n")
    species = {s["scientific_name"]: s for s in (await call(type="arthropoda/species/list"))["result"]["species"]}
    new_id = species["Pieris brassicae"]["id"]

    # Zonder doel weigeren
    res = await call(type="arthropoda/species/delete", species_id=old_id)
    assert not res["success"] and res["error"]["code"] == "in_use"
    # Met doel: dieren verhuizen, oude soort weg, dagboek blijft
    res = await call(type="arthropoda/species/delete", species_id=old_id, reassign_to=new_id)
    assert res["success"], res
    assert res["result"]["moved"] == ["Rupsen 2026"]
    await hass.async_block_till_done()
    names = [s["scientific_name"] for s in (await call(type="arthropoda/species/list"))["result"]["species"]]
    assert "Pieris brasicae" not in names
    animals = {a["id"]: a for a in (await call(type="arthropoda/animals"))["result"]["animals"]}
    assert animals[rups]["species"]["scientific_name"] == "Pieris brassicae"
    assert entry.subentries[rups].data["species_id"] == str(new_id)
    journal = (await call(type="arthropoda/journal/list", animal_id=rups))["result"]["entries"]
    assert [e["type"] for e in journal] == ["feeding"]

    # Bewerken met species_id en een nieuwe naam → zelfde soort, geen kopie
    res = await call(type="arthropoda/species/save", species_id=new_id,
                     yaml="species: {scientific_name: Pieris brassicae L., group: lepidoptera}\n")
    assert res["success"], res
    listed = (await call(type="arthropoda/species/list"))["result"]["species"]
    pieris = [s for s in listed if s["scientific_name"].startswith("Pieris")]
    assert [(s["id"], s["scientific_name"]) for s in pieris] == [(new_id, "Pieris brassicae L.")]

    # Hernoemen naar de naam van een andere soort → nette fout
    res = await call(type="arthropoda/species/save", species_id=new_id,
                     yaml="species: {scientific_name: Sphodromantis lineola, group: mantis}\n")
    assert not res["success"] and res["error"]["code"] == "exists"
