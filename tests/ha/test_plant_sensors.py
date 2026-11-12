"""Sproeien op bodemvocht (taak + pompje), groeilampen op DLI, groeifasen en foto's."""

from datetime import timedelta

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed, async_mock_service

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from test_enclosures import TEMP, _setup


def _plant_with_sensors(hass: HomeAssistant, slug: str, name: str, moisture: float, dli: float,
                        moisture_range=(30, 60), dli_range=(8, 20)) -> tuple[str, str, str]:
    """Plant Monitor-plant met bodemvocht- en DLI-sensor (en grenzen)."""
    entry = MockConfigEntry(domain="plant", title=name)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    plant = registry.async_get_or_create("plant", "plant", entry.entry_id, config_entry=entry,
                                         suggested_object_id=slug).entity_id
    hass.states.async_set(plant, "ok", {"friendly_name": name})
    for quantity, (lo, hi) in (("temperature", (15, 25)), ("moisture", moisture_range), ("dli", dli_range)):
        for side, value in (("min", lo), ("max", hi)):
            number = registry.async_get_or_create(
                "number", "plant", f"{entry.entry_id}-{side}-{quantity}", config_entry=entry,
                suggested_object_id=f"{slug}_{side}_{quantity}").entity_id
            hass.states.async_set(number, str(value), TEMP if quantity == "temperature" else {})
    moist = registry.async_get_or_create("sensor", "plant", f"{entry.entry_id}-current-moisture",
                                         config_entry=entry, suggested_object_id=f"{slug}_moisture").entity_id
    hass.states.async_set(moist, str(moisture), {"unit_of_measurement": "%"})
    light = registry.async_get_or_create("sensor", "plant", f"{entry.entry_id}-dli",
                                         config_entry=entry, suggested_object_id=f"{slug}_dli").entity_id
    hass.states.async_set(light, str(dli), {"unit_of_measurement": "mol/d⋅m²"})
    return plant, moist, light


async def _enc(call, code):
    encs = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    return next(e for e in encs if e["code"] == code)


async def test_moisture_task_and_pump(hass: HomeAssistant, hass_ws_client) -> None:
    pump_on = async_mock_service(hass, "input_boolean", "turn_on")
    pump_off = async_mock_service(hass, "input_boolean", "turn_off")
    gras, gras_moist, _ = _plant_with_sensors(hass, "gras", "Gras", moisture=50, dli=5)
    kool, kool_moist, _ = _plant_with_sensors(hass, "kool", "Kool", moisture=50, dli=5)
    entry, call, _add, _ = await _setup(hass, hass_ws_client)
    res = await call(type="arthropoda/enclosure/save", item={
        "code": "PK-01", "type": "plant_cabinet", "config": {"plants": [gras, kool], "plant_care": {
            gras: {"water_on_moisture": True, "plant_water": 2},
            kool: {"water_on_moisture": True, "pump": "input_boolean.pomp_kool", "pump_seconds": 4,
                   "pump_max_per_day": 2, "pump_pause_minutes": 30},
        }}})
    assert res["success"], res
    enc = await _enc(call, "PK-01")
    assert enc["config"]["plant_care"][kool]["pump"] == "input_boolean.pomp_kool"
    plants = {p["entity_id"]: p for p in enc["plants"]}
    assert plants[gras]["moisture"] == 50 and plants[gras]["dli"] == 5
    # Vochtig genoeg → geen sproeitaak (ook al is er een interval)
    assert not [t for t in enc["tasks"] if t["kind"] == "plant_water"]

    # Gras droogt uit → taak; kool droogt uit → pompje (nog geen taak)
    hass.states.async_set(gras_moist, "20", {"unit_of_measurement": "%"})
    hass.states.async_set(kool_moist, "20", {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    await entry.runtime_data.watering.async_check()
    await hass.async_block_till_done()
    enc = await _enc(call, "PK-01")
    (task,) = [t for t in enc["tasks"] if t["kind"] == "plant_water"]
    assert task["plant"] == gras
    assert [c.data["entity_id"] for c in pump_on] == ["input_boolean.pomp_kool"]
    entries = (await call(type="arthropoda/plant/journal", plants=[kool]))["result"]["entries"]
    assert entries[0]["type"] == "watered" and entries[0]["data"]["auto"] is True
    # Na de looptijd weer uit
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()
    assert [c.data["entity_id"] for c in pump_off] == ["input_boolean.pomp_kool"]
    # Pauze: niet meteen opnieuw
    await entry.runtime_data.watering.async_check()
    assert len(pump_on) == 1

    # Sproeien noteren → taak weg (sensor krijgt even tijd)
    assert (await call(type="arthropoda/plant/log", plants=[gras], entry_type="watered"))["success"]
    enc = await _enc(call, "PK-01")
    assert not [t for t in enc["tasks"] if t["kind"] == "plant_water"]

    # Geen meting → terugvallen op het interval (2 dagen na de laatste beurt)
    hass.states.async_set(gras_moist, "unavailable")
    await hass.async_block_till_done()
    await entry.runtime_data.coordinator.async_refresh()
    enc = await _enc(call, "PK-01")
    (task,) = [t for t in enc["tasks"] if t["kind"] == "plant_water"]
    assert dt_util.parse_datetime(task["due"]).date() == dt_util.now().date() + timedelta(days=2)

    # Onderhoud: pompje blijft af
    runtime = entry.runtime_data
    runtime.watering.runs.clear()
    await call(type="arthropoda/enclosure/save", item={**{k: enc[k] for k in ("id", "code", "type")},
               "status": "maintenance", "config": enc["config"]})
    await runtime.watering.async_check()
    assert len(pump_on) == 1


async def test_dli_light_and_growth_stages(hass: HomeAssistant, hass_ws_client) -> None:
    light_on = async_mock_service(hass, "input_boolean", "turn_on")
    light_off = async_mock_service(hass, "input_boolean", "turn_off")
    hass.states.async_set("sensor.pk_temp", "20", TEMP)
    hass.states.async_set("input_boolean.groeilamp", "off")
    gras, _, gras_dli = _plant_with_sensors(hass, "gras", "Gras", moisture=50, dli=4, dli_range=(8, 20))
    erwt, _, erwt_dli = _plant_with_sensors(hass, "erwt", "Erwt", moisture=50, dli=4, dli_range=(10, 25))
    entry, call, _add, _ = await _setup(hass, hass_ws_client)
    # Dag van 00:00 tot 23:59, zodat het in de test altijd 'dag' is
    hass.config_entries.async_update_entry(entry, options={**entry.options, "day_start": "00:00:00", "day_end": "23:59:00"})
    await hass.async_block_till_done()
    res = await call(type="arthropoda/enclosure/save", item={
        "code": "PK-02", "type": "plant_cabinet", "config": {
            "plants": [gras, erwt], "temperature_sensors": ["sensor.pk_temp"], "lights": ["input_boolean.groeilamp"],
            "light_hours": 24, "light_dli": True}})
    assert res["success"], res
    controller = entry.runtime_data.controller
    await controller.async_evaluate()
    enc = await _enc(call, "PK-02")
    assert enc["config"]["light_dli"] is True
    assert enc["dli"] == {"target": 10, "current": 4, "reached": False}
    assert any(c.data["entity_id"] == "input_boolean.groeilamp" for c in light_on)

    # Erwt bereikt 10, gras 9: laagste meting telt nog niet → lamp blijft aan
    hass.states.async_set(gras_dli, "9")
    hass.states.async_set(erwt_dli, "12")
    await hass.async_block_till_done()
    enc = await _enc(call, "PK-02")
    assert enc["dli"]["reached"] is False
    hass.states.async_set(gras_dli, "10.5")
    await hass.async_block_till_done()
    hass.states.async_set("input_boolean.groeilamp", "on")
    controller._states.clear()  # minimale schakeltijd overslaan in de test
    await controller.async_evaluate()
    enc = await _enc(call, "PK-02")
    assert enc["dli"]["reached"] is True
    assert any(c.data["entity_id"] == "input_boolean.groeilamp" for c in light_off)
    (lamp,) = [a for a in enc["actuators"] if a["entity_id"] == "input_boolean.groeilamp"]
    assert lamp["reason"] == "dli_reached"

    # Groeifasen: gezaaid → gekiemd → voerklaar
    res = await call(type="arthropoda/food/profile/save", plant=gras, kind="crop",
                     days_to_ready=14, days_to_germinate=3)
    assert res["success"], res
    res = await call(type="arthropoda/food/sow", plant=gras, enclosure_id=enc["id"])
    (pot,) = res["result"]["result"]
    p = next(x for x in res["result"]["pots"] if x["id"] == pot)
    assert p["stage"] == "sown" and p["late_germination"] is False
    assert dt_util.parse_datetime(p["germinate_at"]).date() == dt_util.now().date() + timedelta(days=3)
    assert "sown" in p["stages"]
    # 6 dagen geleden gezaaid en nog niet gekiemd → laat
    db = entry.runtime_data.db
    old = (dt_util.utcnow() - timedelta(days=6)).isoformat()
    await hass.async_add_executor_job(lambda: db.update_pot(pot, sown_at=old))
    await entry.runtime_data.coordinator.async_refresh()
    p = next(x for x in (await call(type="arthropoda/food/overview"))["result"]["pots"] if x["id"] == pot)
    assert p["late_germination"] is True
    res = await call(type="arthropoda/pot/stage", pot_id=pot, stage="germinated")
    p = next(x for x in res["result"]["pots"] if x["id"] == pot)
    assert p["stage"] == "germinated" and p["late_germination"] is False
    res = await call(type="arthropoda/pot/stage", pot_id=pot, stage="ready")
    p = next(x for x in res["result"]["pots"] if x["id"] == pot)
    assert p["stage"] == "ready" and p["ready"] is True

    # Foto aan de tijdlijn (met de fase van dat moment)
    await entry.runtime_data.coordinator.async_pot_add_photo(pot, "1_test.jpg")
    p = next(x for x in (await call(type="arthropoda/food/overview"))["result"]["pots"] if x["id"] == pot)
    assert p["photos"][0]["file"] == "1_test.jpg" and p["photos"][0]["stage"] == "ready"
