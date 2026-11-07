"""End-to-end: collectie aanmaken, caresheet importeren, dier toevoegen, dagboek."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.arthropoda.const import DOMAIN

SHEET = """
species:
  scientific_name: Brachypelma hamorii
  common_names: {nl: Mexicaanse roodknievogelspin}
  group: tarantula
  development: molting_adult
care_profiles:
  - temp_day: [22, 26]
    temp_night: [18, 22]
    humidity: [55, 70]
    feeding_interval_days: 14
"""


async def _setup_collection(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Testcollectie"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    return result["result"]


async def _add_animal(hass: HomeAssistant, entry, name: str, species_id: int, **extra):
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "animal"), context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM, result
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": name, "species_id": str(species_id), "kind": "individual",
         "sex": "female", "stage": "adult", "instar": 9},
    )
    assert result["step_id"] == "sensors"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], extra)
    assert result["step_id"] == "actuators"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def test_no_species_aborts_animal_flow(hass: HomeAssistant) -> None:
    entry = await _setup_collection(hass)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "animal"), context={"source": "user"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_species"


async def test_options_add_species(hass: HomeAssistant) -> None:
    entry = await _setup_collection(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_species"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"scientific_name": "Porcellio scaber", "group": "isopod",
         "humidity_min": 60, "humidity_max": 85},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "species_added"
    species = await hass.async_add_executor_job(entry.runtime_data.db.list_species)
    assert [s.scientific_name for s in species] == ["Porcellio scaber"]


async def test_full_flow(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "sensor.terra_temp", "30", {"unit_of_measurement": "°C", "device_class": "temperature"}
    )
    hass.states.async_set(
        "sensor.terra_hum", "60", {"unit_of_measurement": "%", "device_class": "humidity"}
    )
    entry = await _setup_collection(hass)

    response = await hass.services.async_call(
        DOMAIN, "import_caresheet", {"yaml": SHEET}, blocking=True, return_response=True
    )
    assert response["imported"] == ["Brachypelma hamorii"]
    (species,) = await hass.async_add_executor_job(entry.runtime_data.db.list_species)

    await _add_animal(
        hass, entry, "Rosie", species.id,
        temperature_sensors=["sensor.terra_temp"], humidity_sensor="sensor.terra_hum",
    )

    status = hass.states.get("sensor.rosie_status")
    assert status is not None, sorted(hass.states.async_entity_ids())
    assert status.state == "problem"
    assert "temperature_high" in status.attributes["problems"]
    assert hass.states.get("binary_sensor.rosie_problem").state == "on"
    assert hass.states.get("sensor.rosie_temperature").state == "30.0"
    assert hass.states.get("sensor.rosie_instar").state == "9"

    # Temperatuur zakt binnen bereik (ook 's nachts geldig) → status ok
    hass.states.async_set(
        "sensor.terra_temp", "22", {"unit_of_measurement": "°C", "device_class": "temperature"}
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.rosie_status").state == "ok"

    # Snelknop
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.rosie_fed"}, blocking=True
    )
    assert hass.states.get("sensor.rosie_days_since_feeding").state == "0"

    # Vervelling via actie
    device_id = er.async_get(hass).async_get("sensor.rosie_status").device_id
    device = dr.async_get(hass).async_get(device_id)
    assert (DOMAIN, next(iter(entry.subentries))) in device.identifiers
    await hass.services.async_call(
        DOMAIN, "log_molt", {"animal": device.id, "legspan_mm": 55}, blocking=True
    )
    assert hass.states.get("sensor.rosie_instar").state == "10"
    assert hass.states.get("sensor.rosie_molt_count").state == "1"

    journal = await hass.services.async_call(
        DOMAIN, "get_journal", {"animal": device.id}, blocking=True, return_response=True
    )
    assert [e["type"] for e in journal["entries"]] == ["molt", "feeding"]

    # Wijzigen: stadium aanpassen en vochtigheidssensor loskoppelen
    subentry_id = next(iter(entry.subentries))
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "animal"),
        context={"source": "reconfigure", "subentry_id": subentry_id},
    )
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "Rosie", "species_id": str(species.id), "kind": "individual",
         "sex": "female", "stage": "adult", "instar": 12},
    )
    assert result["step_id"] == "reconfigure_sensors"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"temperature_sensors": ["sensor.terra_temp"]}
    )
    assert result["step_id"] == "reconfigure_actuators"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert hass.states.get("sensor.rosie_instar").state == "12"
    assert "humidity_sensor" not in entry.subentries[subentry_id].data
    assert hass.states.get("sensor.rosie_molt_count").state == "1"  # dagboek bleef bewaard

    # Dier verwijderen → archiveren in de database
    subentry_id = next(iter(entry.subentries))
    assert hass.config_entries.async_remove_subentry(entry, subentry_id)
    await hass.async_block_till_done()
    animal = await hass.async_add_executor_job(entry.runtime_data.db.get_animal, subentry_id)
    assert animal.status == "archived"
