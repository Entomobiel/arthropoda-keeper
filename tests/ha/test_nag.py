"""Fase 9: aandringen bij taken over tijd, uitstellen en scanbewijs."""

from datetime import timedelta

from pytest_homeassistant_custom_component.common import async_mock_service

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.arthropoda.const import DOMAIN
from custom_components.arthropoda.nag import ACTION_LATER, NOTIFY_TAG

SHEET = """
species:
  scientific_name: Extatosoma tiaratum
  group: phasmid
care_profiles: [{temp_day: [22, 26], feeding_interval_days: 3}]
"""


def _days_ago(n: int) -> str:
    return (dt_util.now().date() - timedelta(days=n)).isoformat()


async def test_nag_escalation_snooze_and_scan(hass: HomeAssistant, hass_ws_client) -> None:
    notify = async_mock_service(hass, "notify", "mobile_app_pixel")
    speak = async_mock_service(hass, "tts", "speak")
    flash = async_mock_service(hass, "light", "turn_on")
    await async_setup_component(hass, "websocket_api", {})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "C"})
    await hass.async_block_till_done()
    entry = result["result"]

    # Opties via de echte optiestap 'reminders'
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "reminders"})
    assert flow["step_id"] == "reminders"
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {
        "nag_enabled": True, "nag_interval_hours": 3, "quiet_start": "00:00:00", "quiet_end": "00:00:00",
        "nag_max_snoozes": 1, "nag_urgent_days": 2, "nag_loud_days": 3,
        "nag_tts": "tts.google", "nag_media_player": "media_player.keuken", "nag_light": "light.bureau",
        "require_scan": True, "scan_minutes": 15,
    })
    hass.config_entries.async_update_entry(entry, options={**entry.options, "notify_targets": ["notify.mobile_app_pixel"]})
    await hass.async_block_till_done()
    assert entry.options["nag_enabled"] is True

    ws = await hass_ws_client(hass)

    async def call(**msg):
        await ws.send_json_auto_id(msg)
        while True:
            res = await ws.receive_json()
            if res.get("type") == "result":
                return res

    await call(type="arthropoda/species/save", yaml=SHEET)
    (species,) = (await call(type="arthropoda/species/list"))["result"]["species"]

    async def add(name, acquired_days_ago):
        res = await call(type="arthropoda/animal/add", data={
            "name": name, "species_id": species["id"], "kind": "individual",
            "acquired_at": _days_ago(acquired_days_ago)})
        assert res["success"], res
        await hass.async_block_till_done()
        return res["result"]["animal_id"]

    # Voederen elke 3 dagen; 4 dagen geleden aangekocht = 1 dag te laat
    rosie = await add("Rosie", 4)
    nag = lambda: entry.runtime_data.nag  # noqa: E731 (nieuw object na herladen)
    tasks = nag().overdue_tasks()
    assert [(t.animal_id, t.kind) for t in tasks] == [(rosie, "feeding")]

    # Niveau 1: melding met knoppen, zonder 'Gedaan'; tikken telt niet als scan
    notify.clear()
    await nag().async_check(force=True)
    (call1,) = notify
    data = call1.data["data"]
    assert data["tag"] == NOTIFY_TAG and "persistent" not in data
    assert [a["action"] for a in data["actions"]] == [ACTION_LATER, "ARTHROPODA_NAG_TOMORROW"]
    assert "Rosie" in call1.data["message"]
    # Binnen het interval geen nieuwe melding
    notify.clear()
    await nag().async_check()
    assert not notify

    # 'Over 1 uur' → taak stil, melding weggehaald; maximum (1) bereikt
    hass.bus.async_fire("mobile_app_notification_action", {"action": ACTION_LATER})
    await hass.async_block_till_done()
    assert nag().overdue_tasks() == []
    assert any(c.data.get("message") == "clear_notification" for c in notify)
    key = nag()._key(tasks[0])
    assert nag().state.snoozes[key] == 1
    # Na het uitstel: nieuwe melding zonder knoppen (maximum bereikt)
    nag().state.silenced_until[key] = (dt_util.utcnow() - timedelta(minutes=1)).isoformat()
    notify.clear()
    await nag().async_check(force=True)
    assert "actions" not in notify[-1].data["data"]

    # Niveau 3: een dier dat 4 dagen te laat is → dringend + speaker + lamp
    await add("Grote Bertha", 7)
    notify.clear()
    await nag().async_check(force=True)
    data = notify[-1].data["data"]
    assert data["persistent"] is True and data["priority"] == "high" and "actions" not in data
    assert data["channel"] == "Arthropoda urgent"  # testomgeving is Engelstalig
    assert speak and speak[-1].data["media_player_entity_id"] == "media_player.keuken"
    assert "Grote Bertha" in speak[-1].data["message"]
    assert flash and flash[-1].data["flash"] == "long"

    # Scanbewijs: kast met NFC-tag; voederen zonder scan wordt geweigerd
    res = await call(type="arthropoda/enclosure/save", item={"code": "KB-01", "nfc_tag": "TAG-1"})
    enc_id = res["result"]["id"]
    for animal in (rosie,):
        assert (await call(type="arthropoda/enclosure/assign", animal_id=animal, enclosure_id=enc_id))["success"]
    res = await call(type="arthropoda/journal/add", animal_ids=[rosie], entry_type="feeding")
    assert not res["success"] and "KB-01" in res["error"]["message"]
    # Ook afvinken in de takenlijst wordt geweigerd
    res = await call(type="arthropoda/task/done", uid=f"{rosie}:feeding")
    assert not res["success"]
    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    assert enc["scan"] == {"required": True, "recent": False}

    # Andere handelingen (niet het voederen) mogen gewoon
    res = await call(type="arthropoda/journal/add", animal_ids=[rosie], entry_type="observation", notes="ok")
    assert res["success"], res

    # NFC-tag scannen → nu mag het; taak weg
    hass.bus.async_fire("tag_scanned", {"tag_id": "TAG-1", "device_id": None})
    await hass.async_block_till_done()
    (enc,) = (await call(type="arthropoda/enclosures/list"))["result"]["enclosures"]
    assert enc["scan"]["recent"] is True
    res = await call(type="arthropoda/journal/add", animal_ids=[rosie], entry_type="feeding")
    assert res["success"], res
    assert [t.animal_id for t in nag().overdue_tasks()] != [rosie]

    # Bertha zit in geen kast → geen bewijs mogelijk, afvinken mag
    bertha_task = next(t for t in nag().overdue_tasks() if t.kind == "feeding")
    res = await call(type="arthropoda/task/done", uid=bertha_task.uid)
    assert res["success"], res
    await hass.async_block_till_done()
    assert nag().overdue_tasks() == []
    # Alles gedaan → melding van de gsm gehaald
    assert notify[-1].data["message"] == "clear_notification"

    # QR-scan via het werkscherm telt ook als scan
    res = await call(type="arthropoda/enclosure/scanned", code="kb-01")
    assert res["success"] and res["result"]["enclosure_id"] == enc_id
