"""Opvolging: takenlijst, kalender, samenvatting, collectie-sensoren."""

from datetime import timedelta

from pytest_homeassistant_custom_component.common import async_mock_service

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.arthropoda.const import DOMAIN

SHEET = """
species:
  scientific_name: Sphodromantis lineola
  group: mantis
  development: hemimetabolous
  incubation_days: [28, 42]
care_profiles:
  - {feeding_interval_days: 3, cleaning_interval_days: 14}
"""


async def _setup(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "C"})
    entry = result["result"]
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN, "import_caresheet", {"yaml": SHEET}, blocking=True, return_response=True
    )
    (species,) = await hass.async_add_executor_job(entry.runtime_data.db.list_species)
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, "animal"), context={"source": "user"})
    acquired = (dt_util.now().date() - timedelta(days=5)).isoformat()
    result = await flow.async_configure(
        result["flow_id"],
        {"name": "Mantis", "species_id": str(species.id), "kind": "individual",
         "sex": "female", "stage": "nymph", "instar": 4, "acquired_at": acquired},
    )
    result = await flow.async_configure(result["flow_id"], {})
    result = await flow.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    device_id = er.async_get(hass).async_get("sensor.mantis_status").device_id
    return entry, device_id


async def _todo_items(hass: HomeAssistant) -> list[dict]:
    result = await hass.services.async_call(
        "todo", "get_items", {"entity_id": "todo.c_maintenance"},
        blocking=True, return_response=True,
    )
    return result["todo.c_maintenance"]["items"]


async def test_todo_complete_and_snooze(hass: HomeAssistant) -> None:
    entry, device_id = await _setup(hass)

    # Aangeschaft 5 dagen geleden, voederen elke 3 dagen → 2 dagen te laat
    items = await _todo_items(hass)
    assert [i["uid"].split(":")[1] for i in items] == ["feeding"]
    assert hass.states.get("todo.c_maintenance").state == "1"
    assert hass.states.get("sensor.c_open_tasks").state == "1"

    # Afvinken → dagboekregel 'feeding' → taak verdwijnt
    await hass.services.async_call(
        "todo", "update_item",
        {"entity_id": "todo.c_maintenance", "item": items[0]["uid"], "status": "completed"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert await _todo_items(hass) == []
    journal = await hass.services.async_call(
        DOMAIN, "get_journal", {"animal": device_id}, blocking=True, return_response=True
    )
    assert journal["entries"][0]["type"] == "feeding"
    assert journal["entries"][0]["data"] == {"source": "todo"}

    # Uitstellen via de actie
    await hass.services.async_call(
        DOMAIN, "snooze_task", {"animal": device_id, "task": "cleaning", "days": 30},
        blocking=True, return_response=True,
    )
    tasks = {t.kind: t for t in entry.runtime_data.coordinator.all_tasks()}
    assert dt_util.as_local(tasks["cleaning"].due).date() == dt_util.now().date() + timedelta(days=30)


async def test_todo_delete_snoozes_until_tomorrow(hass: HomeAssistant) -> None:
    entry, _ = await _setup(hass)
    (item,) = await _todo_items(hass)
    await hass.services.async_call(
        "todo", "remove_item", {"entity_id": "todo.c_maintenance", "item": item["uid"]},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert await _todo_items(hass) == []
    (feeding,) = [t for t in entry.runtime_data.coordinator.all_tasks() if t.kind == "feeding"]
    assert dt_util.as_local(feeding.due).date() == dt_util.now().date() + timedelta(days=1)


async def test_calendar(hass: HomeAssistant) -> None:
    _, device_id = await _setup(hass)
    now = dt_util.now()
    for days_ago in (100, 40):
        await hass.services.async_call(
            DOMAIN, "log_molt", {"animal": device_id, "timestamp": now - timedelta(days=days_ago)},
            blocking=True,
        )
    await hass.services.async_call(
        DOMAIN, "log_entry",
        {"animal": device_id, "type": "ootheca", "timestamp": now - timedelta(days=10)},
        blocking=True,
    )
    await hass.async_block_till_done()

    result = await hass.services.async_call(
        "calendar", "get_events",
        {"entity_id": "calendar.c_calendar", "start_date_time": now - timedelta(days=120),
         "end_date_time": now + timedelta(days=60)},
        blocking=True, return_response=True,
    )
    summaries = [e["summary"] for e in result["calendar.c_calendar"]["events"]]
    assert sum(s.startswith("Molt: Mantis") for s in summaries) == 2  # dagboek
    assert any(s.startswith("Ootheca: Mantis") for s in summaries)
    assert any(s.startswith("Feed: Mantis") for s in summaries)  # gepland
    assert any(s.startswith("Expected molt") for s in summaries)  # 40 + 60 dagen → over 20 dagen
    assert any(s.startswith("Expected hatch ootheca") for s in summaries)
    assert hass.states.get("calendar.c_calendar") is not None


async def test_digest_and_problem_sensor(hass: HomeAssistant) -> None:
    notify = async_mock_service(hass, "notify", "phone")
    entry, _ = await _setup(hass)
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "notify_targets": ["notify.phone"]}
    )
    await hass.async_block_till_done()

    result = await hass.services.async_call(
        DOMAIN, "send_digest", {}, blocking=True, return_response=True
    )
    assert result == {"sent": True}
    assert "Feed: Mantis" in notify[0].data["message"]
    problems = hass.states.get("sensor.c_animals_with_a_problem")
    assert problems.state == "1"  # voederen te laat
    assert problems.attributes["animals"] == {"Mantis": ["feeding_overdue"]}


async def test_animal_device_has_settings_link(hass: HomeAssistant) -> None:
    _, device_id = await _setup(hass)
    device = dr.async_get(hass).async_get(device_id)
    assert device.configuration_url == "homeassistant://config/integrations/integration/arthropoda"
