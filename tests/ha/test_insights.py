"""Inzichten in HA: premolt-vermoeden pauzeert het voederen, leeftijd, kolonie-daling."""

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.arthropoda.const import DOMAIN

SHEET = """
species:
  scientific_name: Brachypelma hamorii
  group: tarantula
  development: molting_adult
  lifespan: {female_years: [20, 30], male_years: [5, 7]}
care_profiles: [{temp_day: [24, 28], feeding_interval_days: 7}]
"""


async def test_insights_flow(hass: HomeAssistant, hass_ws_client) -> None:
    await async_setup_component(hass, "websocket_api", {})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "C"})
    await hass.async_block_till_done()
    ws = await hass_ws_client(hass)

    async def call(**msg):
        await ws.send_json_auto_id(msg)
        while True:
            res = await ws.receive_json()
            if res.get("type") == "result":
                return res

    assert (await call(type="arthropoda/species/save", yaml=SHEET))["success"]
    (species,) = (await call(type="arthropoda/species/list"))["result"]["species"]
    born = (dt_util.now().date() - timedelta(days=3 * 365)).isoformat()
    res = await call(type="arthropoda/animal/add", data={
        "name": "Rosie", "species_id": species["id"], "kind": "individual",
        "sex": "female", "stage": "juvenile", "born_at": born})
    await hass.async_block_till_done()
    rosie = res["result"]["animal_id"]
    res = await call(type="arthropoda/animal/add", data={
        "name": "Dubia", "species_id": species["id"], "kind": "colony", "count": 500})
    await hass.async_block_till_done()
    colony = res["result"]["animal_id"]

    async def animal(aid):
        animals = (await call(type="arthropoda/animals"))["result"]["animals"]
        return next(a for a in animals if a["id"] == aid)

    a = await animal(rosie)
    assert [i["key"] for i in a["insights"]] == ["lifespan"]
    assert a["insights"][0]["age_estimated"] is False
    assert any(t["kind"] == "feeding" for t in a["tasks"])

    # Twee keer voer geweigerd → premolt vermoed, voederen gepauzeerd
    for days in (8, 1):
        ts = (dt_util.now() - timedelta(days=days)).isoformat()
        assert (await call(type="arthropoda/journal/add", animal_ids=[rosie],
                           entry_type="feeding_refused", timestamp=ts))["success"]
    a = await animal(rosie)
    keys = [i["key"] for i in a["insights"]]
    assert "premolt_suspected" in keys and a["feeding_paused"] is True
    assert not any(t["kind"] == "feeding" for t in a["tasks"])

    # Premolt bevestigen → geen 'vermoeden' meer, nog steeds gepauzeerd
    assert (await call(type="arthropoda/journal/add", animal_ids=[rosie], entry_type="premolt_observed"))["success"]
    a = await animal(rosie)
    assert "premolt_suspected" not in [i["key"] for i in a["insights"]] and a["feeding_paused"] is True

    # Kolonie: tellingen 500 → 300 in 20 dagen → daling
    for days, count in ((20, 500), (1, 300)):
        ts = (dt_util.now() - timedelta(days=days)).isoformat()
        assert (await call(type="arthropoda/journal/add", animal_ids=[colony], entry_type="count",
                           timestamp=ts, data={"count": count}))["success"]
    c = await animal(colony)
    (trend,) = [i for i in c["insights"] if i["key"].startswith("colony")]
    assert trend["key"] == "colony_declining" and trend["from"] == 500 and trend["to"] == 300
