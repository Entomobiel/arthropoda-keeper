"""Klimaatsturing end-to-end: gedeelde verwarming, veiligheid, verneveling, onderhoud."""

from datetime import timedelta

from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_mock_service,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from custom_components.arthropoda.const import DOMAIN

# Alleen temp_day: 's nachts geldt hetzelfde, dus de test hangt niet af van het uur.
SHEETS = """
species: {scientific_name: Species alpha, group: tarantula, development: molting_adult}
care_profiles: [{temp_day: [22, 26], humidity: [60, 80]}]
---
species: {scientific_name: Species beta, group: mantis, development: hemimetabolous}
care_profiles: [{temp_day: [24, 28], humidity: [60, 80]}]
---
species: {scientific_name: Species gamma, group: scorpion}
care_profiles: [{temp_day: [30, 34]}]
"""

TEMP = {"unit_of_measurement": "°C", "device_class": "temperature"}
HUM = {"unit_of_measurement": "%", "device_class": "humidity"}


async def _setup(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "C"})
    entry = result["result"]
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN, "import_caresheet", {"yaml": SHEETS}, blocking=True, return_response=True
    )
    species = {
        s.scientific_name: s.id
        for s in await hass.async_add_executor_job(entry.runtime_data.db.list_species)
    }
    return entry, species


async def _add(hass, entry, name, species_id, sensors, actuators, control=None, stage="adult"):
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, "animal"), context={"source": "user"})
    result = await flow.async_configure(
        result["flow_id"],
        {"name": name, "species_id": str(species_id), "kind": "individual",
         "sex": "unknown", "stage": stage},
    )
    result = await flow.async_configure(result["flow_id"], sensors)
    assert result["step_id"] == "actuators"
    result = await flow.async_configure(result["flow_id"], actuators)
    if result.get("step_id") == "control":
        result = await flow.async_configure(result["flow_id"], control or {})
    assert result["type"] == "create_entry", result
    await hass.async_block_till_done()


def _entity_calls(calls, entity_id):
    return [c for c in calls if entity_id in str(c.data.get("entity_id"))]


async def test_shared_heater_and_safety(hass: HomeAssistant) -> None:
    turn_on = async_mock_service(hass, "input_boolean", "turn_on")
    turn_off = async_mock_service(hass, "input_boolean", "turn_off")
    hass.states.async_set("sensor.t", "22", TEMP)
    hass.states.async_set("input_boolean.heater", "off")
    entry, species = await _setup(hass)

    sensors = {"temperature_sensors": ["sensor.t"]}
    await _add(hass, entry, "Alpha", species["Species alpha"], sensors, {"heater": "input_boolean.heater"})
    await _add(hass, entry, "Beta", species["Species beta"], sensors, {"heater": "input_boolean.heater"})

    # Gezamenlijk bereik 24–26 → 22 °C is te koud → verwarming aan
    assert _entity_calls(turn_on, "input_boolean.heater")
    attrs = hass.states.get("sensor.alpha_climate_control_status").attributes
    (heater,) = attrs["actuators"]
    assert heater["target"] == [24, 26]
    assert heater["setpoint"] == 25
    assert sorted(heater["members"]) == sorted(entry.subentries)

    # 32 °C ≥ 26 + 5 → kritiek: meteen uit, ook al werd net geschakeld
    hass.states.async_set("input_boolean.heater", "on")
    hass.states.async_set("sensor.t", "32", TEMP)
    await hass.async_block_till_done()
    assert _entity_calls(turn_off, "input_boolean.heater")
    assert "temperature_critical" in hass.states.get("sensor.alpha_status").attributes["problems"]

    # Sensor onbereikbaar → fail-safe uit
    turn_off.clear()
    hass.states.async_set("sensor.t", "unavailable")
    await hass.async_block_till_done()
    assert _entity_calls(turn_off, "input_boolean.heater")


async def test_starts_after_home_assistant_boot(hass: HomeAssistant) -> None:
    """Herstart van HA: integratie laadt tijdens het opstarten, regelt pas daarna."""
    turn_on = async_mock_service(hass, "input_boolean", "turn_on")
    async_mock_service(hass, "input_boolean", "turn_off")
    hass.states.async_set("sensor.t", "22", TEMP)
    hass.states.async_set("input_boolean.heater", "off")
    entry, species = await _setup(hass)
    await _add(hass, entry, "Alpha", species["Species alpha"],
               {"temperature_sensors": ["sensor.t"]}, {"heater": "input_boolean.heater"})
    turn_on.clear()

    hass.set_state(CoreState.starting)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert not turn_on  # nog niets gestuurd tijdens het opstarten

    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    assert _entity_calls(turn_on, "input_boolean.heater")


async def test_climate_switch_off_leaves_actuator_alone(hass: HomeAssistant) -> None:
    turn_on = async_mock_service(hass, "input_boolean", "turn_on")
    async_mock_service(hass, "input_boolean", "turn_off")
    hass.states.async_set("sensor.t", "22", TEMP)
    hass.states.async_set("input_boolean.heater", "off")
    entry, species = await _setup(hass)
    await _add(hass, entry, "Alpha", species["Species alpha"],
               {"temperature_sensors": ["sensor.t"]}, {"heater": "input_boolean.heater"})
    assert _entity_calls(turn_on, "input_boolean.heater")

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.alpha_climate_control"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("switch.alpha_climate_control").state == "off"
    assert hass.states.get("sensor.alpha_climate_control_status").state == "paused"


async def test_range_conflict_creates_issue(hass: HomeAssistant) -> None:
    async_mock_service(hass, "input_boolean", "turn_on")
    async_mock_service(hass, "input_boolean", "turn_off")
    hass.states.async_set("sensor.t", "28", TEMP)
    hass.states.async_set("input_boolean.heater", "off")
    entry, species = await _setup(hass)
    sensors = {"temperature_sensors": ["sensor.t"]}
    await _add(hass, entry, "Alpha", species["Species alpha"], sensors, {"heater": "input_boolean.heater"})
    await _add(hass, entry, "Gamma", species["Species gamma"], sensors, {"heater": "input_boolean.heater"})

    issue = ir.async_get(hass).async_get_issue(DOMAIN, "range_conflict_input_boolean.heater")
    assert issue is not None
    assert "Alpha" in issue.translation_placeholders["animals"]


async def test_mister_pulse_and_maintenance(hass: HomeAssistant) -> None:
    turn_on = async_mock_service(hass, "input_boolean", "turn_on")
    turn_off = async_mock_service(hass, "input_boolean", "turn_off")
    hass.states.async_set("sensor.h", "40", HUM)
    hass.states.async_set("input_boolean.mister", "off")
    hass.states.async_set("input_boolean.pump", "off")
    entry, species = await _setup(hass)
    await _add(
        hass, entry, "Alpha", species["Species alpha"],
        {"humidity_sensor": "sensor.h"},
        {"mister": "input_boolean.mister", "pumps": ["input_boolean.pump"]},
        {"mist_seconds": 5, "mist_pause_minutes": 30, "mist_max_per_day": 6},
    )
    # Te droog → puls; pomp altijd aan
    assert len(_entity_calls(turn_on, "input_boolean.mister")) == 1
    assert _entity_calls(turn_on, "input_boolean.pump")

    # Na 5 s gaat de vernevelaar weer uit
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()
    assert _entity_calls(turn_off, "input_boolean.mister")

    # Binnen de pauze geen nieuwe puls
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()
    assert len(_entity_calls(turn_on, "input_boolean.mister")) == 1

    # Onderhoudsmodus → pomp uit
    hass.states.async_set("input_boolean.pump", "on")
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.alpha_maintenance_mode"}, blocking=True
    )
    await hass.async_block_till_done()
    assert _entity_calls(turn_off, "input_boolean.pump")
    assert hass.states.get("sensor.alpha_climate_control_status").state == "maintenance"


async def test_critical_alarm_notifies(hass: HomeAssistant) -> None:
    notify = async_mock_service(hass, "notify", "test_phone")
    hass.states.async_set("sensor.t", "24", TEMP)
    entry, species = await _setup(hass)
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "notify_targets": ["notify.test_phone"]}
    )
    await hass.async_block_till_done()
    await _add(hass, entry, "Alpha", species["Species alpha"],
               {"temperature_sensors": ["sensor.t"]}, {})
    assert not notify

    hass.states.async_set("sensor.t", "35", TEMP)
    await hass.async_block_till_done()
    assert len(notify) == 1
    assert "Alpha" in notify[0].data["title"]

    hass.states.async_set("sensor.t", "24", TEMP)
    await hass.async_block_till_done()
    assert len(notify) == 2  # opgelost-bericht


async def test_adult_mantis_cannot_molt(hass: HomeAssistant) -> None:
    entry, species = await _setup(hass)
    await _add(hass, entry, "Beta", species["Species beta"], {}, {})
    assert hass.states.get("binary_sensor.beta_premolt") is None
    assert hass.states.get("sensor.beta_molt_count") is None
    device_id = hass.states.get("sensor.beta_status")
    assert device_id is not None


async def test_import_with_filename_in_yaml_field(hass: HomeAssistant, tmp_path) -> None:
    entry, _ = await _setup(hass)
    folder = tmp_path / "arthropoda" / "caresheets"
    folder.mkdir(parents=True)
    (folder / "extra.yaml").write_text(
        "species: {scientific_name: Porcellio laevis, group: isopod}\n", encoding="utf-8"
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "import_caresheet"}
    )
    # Alleen de bestandsnaam ingevuld in het YAML-veld (zoals in de echte test)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"yaml": "extra.yaml"}
    )
    assert result["type"] == "form"
    assert "arthropoda/caresheets/extra.yaml" in result["description_placeholders"]["error"]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"yaml": "arthropoda/caresheets/extra.yaml"}
    )
    assert result["reason"] == "caresheets_imported"
