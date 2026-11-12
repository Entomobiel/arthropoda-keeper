"""Voedselplanning: bakjes zaaien, voerklaar, in een dierenbak, vervangen, vaste planten."""

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from test_plants import _fake_plant
from test_enclosures import _setup


async def test_food_planning(hass: HomeAssistant, hass_ws_client) -> None:
    gras = _fake_plant(hass, "gras", "Gras", (15, 25), (40, 80))
    eik = _fake_plant(hass, "eik", "Eik", (10, 25), (40, 80))
    entry, call, _add, _ = await _setup(hass, hass_ws_client)
    pk = (await call(type="arthropoda/enclosure/save", item={
        "code": "PK-01", "type": "plant_cabinet", "config": {"plants": [gras, eik]}}))["result"]["id"]
    kb = (await call(type="arthropoda/enclosure/save", item={"code": "KB-01"}))["result"]["id"]
    db = entry.runtime_data.db

    # Profielen: gras = gewas, eik = vaste plant
    res = await call(type="arthropoda/food/profile/save", plant=gras, kind="crop",
                     days_to_ready=10, days_in_use=5, sow_every_days=7)
    assert res["success"], res
    res = await call(type="arthropoda/food/profile/save", plant=eik, kind="perennial",
                     days_in_use=3, days_to_recover=20)
    plants = {p["entity_id"]: p for p in res["result"]["plants"]}
    assert plants[gras]["profile"]["kind"] == "crop" and plants[gras]["home"] == "PK-01"
    assert plants[eik]["settings"]["days_to_recover"] == 20
    tasks = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    sow = next(t for e in tasks for t in e["tasks"] if t["kind"] == "plant_sow")
    assert sow["plant"] == gras  # nog nooit gezaaid → vandaag zaaien
    assert dt_util.parse_datetime(sow["due"]).date() == dt_util.now().date()

    # Zaaien: 2 bakjes, groeien 10 dagen; zaaitaak schuift 7 dagen op
    res = await call(type="arthropoda/food/sow", plant=gras, enclosure_id=pk, count=2, label="Gras")
    assert res["success"], res
    pot1, pot2 = res["result"]["result"]
    pots = {p["id"]: p for p in res["result"]["pots"]}
    assert pots[pot1]["status"] == "growing" and not pots[pot1]["ready"]
    assert pots[pot1]["name"] == "Gras 1" and pots[pot1]["location"] == "PK-01"
    fc = {p["entity_id"]: p for p in res["result"]["plants"]}[gras]["forecast"]
    assert fc["ready"] == 0 and fc["growing"] == 2 and fc["shortfall"] is None
    entries = (await call(type="arthropoda/plant/journal", plants=[gras]))["result"]["entries"]
    assert entries[0]["type"] == "sown"
    (pk_enc,) = [e for e in (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"] if e["id"] == pk]
    sow = next(t for t in pk_enc["tasks"] if t["kind"] == "plant_sow")
    assert dt_util.parse_datetime(sow["due"]).date() == dt_util.now().date() + timedelta(days=7)
    assert len(pk_enc["pots"]) == 2

    # 10 dagen later: voerklaar
    past = (dt_util.utcnow() - timedelta(hours=1)).isoformat()
    for pot in (pot1, pot2):
        await hass.async_add_executor_job(lambda p=pot: db.update_pot(p, ready_at=past))
    await entry.runtime_data.coordinator.async_refresh()

    # In de dierenbak → vervangtaak na 5 dagen
    res = await call(type="arthropoda/pot/move", pot_id=pot1, enclosure_id=kb)
    assert res["success"], res
    (kb_enc,) = [e for e in (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"] if e["id"] == kb]
    assert [p["id"] for p in kb_enc["pots"]] == [pot1] and kb_enc["pots"][0]["status"] == "in_use"
    (replace,) = [t for t in kb_enc["tasks"] if t["kind"] == "pot_replace"]
    assert replace["uid"] == f"enc{kb}:pot_replace:{gras}:{pot1}" and replace["label"] == "Gras 1"
    assert dt_util.parse_datetime(replace["due"]).date() == dt_util.now().date() + timedelta(days=5)

    # Vervangen (via de takenlijst): bakje 2 erin, bakje 1 op
    assert (await call(type="arthropoda/task/done", uid=replace["uid"]))["success"]
    food = (await call(type="arthropoda/food/overview"))["result"]
    pots = {p["id"]: p for p in food["pots"]}
    assert pot1 not in pots and pots[pot2]["status"] == "in_use" and pots[pot2]["location"] == "KB-01"
    fc = {p["entity_id"]: p for p in food["plants"]}[gras]["forecast"]
    # Niets meer in voorraad → tekort binnen 5 dagen → zaaien vandaag
    assert fc["ready"] == 0 and fc["in_use"] == 1 and fc["shortfall"] is not None
    (pk_enc,) = [e for e in (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"] if e["id"] == pk]
    sow = next(t for t in pk_enc["tasks"] if t["kind"] == "plant_sow")
    assert dt_util.parse_datetime(sow["due"]).date() == dt_util.now().date()

    # Opnieuw vervangen kan niet: geen voerklaar bakje
    res = await call(type="arthropoda/pot/replace", pot_id=pot2)
    assert not res["success"] and "Geen voerklaar bakje" in res["error"]["message"]

    # Zaaitaak afvinken = nieuw bakje in PK-01
    assert (await call(type="arthropoda/task/done", uid=sow["uid"]))["success"]
    food = (await call(type="arthropoda/food/overview"))["result"]
    assert sum(1 for p in food["pots"] if p["plant"] == gras and p["status"] == "growing") == 1

    # Vaste plant: toevoegen (meteen klaar) → afgrazen → terug om te herstellen
    res = await call(type="arthropoda/food/sow", plant=eik, enclosure_id=pk)
    (oak,) = res["result"]["result"]
    pots = {p["id"]: p for p in res["result"]["pots"]}
    assert pots[oak]["status"] == "recovering" and pots[oak]["ready"] is True
    assert (await call(type="arthropoda/pot/move", pot_id=oak, enclosure_id=kb))["success"]
    res = await call(type="arthropoda/pot/return", pot_id=oak)
    assert res["success"], res
    pots = {p["id"]: p for p in res["result"]["pots"]}
    assert pots[oak]["status"] == "recovering" and pots[oak]["location"] == "PK-01"
    assert pots[oak]["cycles"] == 1 and not pots[oak]["ready"]
    assert dt_util.parse_datetime(pots[oak]["ready_at"]).date() == dt_util.now().date() + timedelta(days=20)
    # Een gewas kan niet 'terug'
    res = await call(type="arthropoda/pot/return", pot_id=pot2)
    assert not res["success"]

    # Bakje mislukt → weg uit de planning
    grow = next(p["id"] for p in food["pots"] if p["plant"] == gras and p["status"] == "growing")
    assert (await call(type="arthropoda/pot/finish", pot_id=grow, status="failed"))["success"]
    food = (await call(type="arthropoda/food/overview"))["result"]
    assert grow not in {p["id"] for p in food["pots"]}
