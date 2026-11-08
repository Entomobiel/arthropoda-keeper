"""Constanten voor Arthropoda Keeper."""

from __future__ import annotations

DOMAIN = "arthropoda"
NAME = "Arthropoda Keeper"

DATA_DIR = "arthropoda"
DB_FILE = "arthropoda.db"

SUBENTRY_ANIMAL = "animal"

EVENT_JOURNAL_ENTRY = "arthropoda_journal_entry"
# Dispatcher-signaal: er is iets veranderd (voor paneel en kaarten).
SIGNAL_UPDATE = "arthropoda_update"

# Frontend
PANEL_URL_PATH = "arthropoda"
STATIC_URL = "/arthropoda_static"
FRONTEND_VERSION = "0.7.1"

# --- Soortkenmerken -------------------------------------------------------

GROUPS = [
    "tarantula",
    "true_spider",
    "scorpion",
    "whip_spider",
    "mantis",
    "phasmid",
    "orthoptera",
    "roach",
    "isopod",
    "myriapod",
    "beetle",
    "ant",
    "lepidoptera",
    "aquatic",
    "other",
]

DEVELOPMENT = ["hemimetabolous", "holometabolous", "ametabolous", "molting_adult"]

HABITATS = ["terrestrial", "arboreal", "fossorial", "semi_aquatic", "aquatic"]

STAGES = ["egg", "nymph", "larva", "pupa", "juvenile", "subadult", "adult"]

# Als er geen profiel is voor de exacte levensfase, probeer deze (in volgorde).
STAGE_FALLBACK: dict[str, list[str]] = {
    "nymph": ["juvenile"],
    "juvenile": ["nymph"],
    "subadult": ["juvenile", "nymph", "adult"],
    "larva": ["juvenile"],
    "pupa": ["larva"],
    "egg": [],
    "adult": [],
}

SEASONS = ["normal", "winter", "breeding"]
SEASON_MODES = ["auto", *SEASONS]

SUBSTRATE_MOISTURE = ["dry", "slightly_moist", "moist", "wet"]
VENTILATION = ["low", "medium", "high"]

# --- Dier / kolonie -------------------------------------------------------

KINDS = ["individual", "colony"]
SEXES = ["unknown", "female", "male", "probably_female", "probably_male", "mixed"]
ORIGINS = ["bred", "bought", "wild_caught", "gift", "unknown"]
ANIMAL_STATUSES = [
    "active",
    "diapause",
    "deceased",
    "sold",
    "released",
    "escaped",
    "archived",
]
# Statussen waarin de integratie nog bewaakt.
MONITORED_STATUSES = ("active", "diapause")

# --- Configuratiesleutels -------------------------------------------------

CONF_SPECIES_ID = "species_id"
CONF_KIND = "kind"
CONF_SEX = "sex"
CONF_STAGE = "stage"
CONF_INSTAR = "instar"
CONF_COUNT = "count"
CONF_ACQUIRED_AT = "acquired_at"
CONF_BORN_AT = "born_at"
CONF_ORIGIN = "origin"
CONF_TEMPERATURE_SENSORS = "temperature_sensors"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_WATER_TEMPERATURE_SENSOR = "water_temperature_sensor"
# Voedselplanten uit de plant monitor / plant-integratie (plant.*)
CONF_FOOD_PLANTS = "food_plants"

INITIAL_FIELDS_UI = (CONF_SEX, CONF_STAGE, CONF_INSTAR, CONF_COUNT)

SENSOR_KEYS = (
    CONF_TEMPERATURE_SENSORS,
    CONF_HUMIDITY_SENSOR,
    CONF_WATER_TEMPERATURE_SENSOR,
    CONF_FOOD_PLANTS,
)

# Actuatoren per dier (rol -> configuratiesleutel)
CONF_HEATER = "heater"
CONF_MISTER = "mister"
CONF_LIGHTS = "lights"
CONF_FAN = "fan"
CONF_WATER_HEATER = "water_heater"
CONF_PUMPS = "pumps"

ACTUATOR_KEYS = (CONF_HEATER, CONF_MISTER, CONF_LIGHTS, CONF_FAN, CONF_WATER_HEATER, CONF_PUMPS)
# Sleutels met een lijst van entiteiten
MULTI_ACTUATOR_KEYS = (CONF_LIGHTS, CONF_PUMPS)

# Afstelling (per dier; bij gedeelde actuatoren geldt die van het eerste dier)
CONF_HYSTERESIS = "hysteresis"
CONF_MIST_SECONDS = "mist_seconds"
CONF_MIST_PAUSE_MINUTES = "mist_pause_minutes"
CONF_MIST_MAX_PER_DAY = "mist_max_per_day"
CONF_MIST_TIMES = "mist_times"
CONF_LIGHT_RAMP_MINUTES = "light_ramp_minutes"

TUNING_KEYS = (
    CONF_HYSTERESIS,
    CONF_MIST_SECONDS,
    CONF_MIST_PAUSE_MINUTES,
    CONF_MIST_MAX_PER_DAY,
    CONF_MIST_TIMES,
    CONF_LIGHT_RAMP_MINUTES,
)
TUNING_DEFAULTS = {
    CONF_HYSTERESIS: 0.5,
    CONF_MIST_SECONDS: 10,
    CONF_MIST_PAUSE_MINUTES: 30,
    CONF_MIST_MAX_PER_DAY: 6,
    CONF_MIST_TIMES: "",
    CONF_LIGHT_RAMP_MINUTES: 0,
}

# Minimale tijd tussen twee schakelingen van een aan/uit-actuator (relais sparen).
MIN_SWITCH_INTERVAL_SECONDS = 60
# Hoe vaak de regelaar ook zonder sensorwijziging opnieuw beslist.
CONTROL_TICK_SECONDS = 30
# Onderhoudsmodus schakelt zichzelf na zoveel minuten weer uit.
MAINTENANCE_MINUTES = 60

# Opties van de hoofdentry
CONF_DAY_START = "day_start"
CONF_DAY_END = "day_end"
CONF_POST_MOLT_FAST_DAYS = "post_molt_fast_days"
CONF_LIGHT_MODE = "light_mode"
CONF_STALE_MINUTES = "stale_minutes"
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_ALARM_DELAY_MINUTES = "alarm_delay_minutes"

CONF_DIGEST_ENABLED = "digest_enabled"
CONF_DIGEST_TIME = "digest_time"
DEFAULT_DIGEST_TIME = "18:00:00"

LIGHT_MODES = ["fixed", "sun"]

DEFAULT_DAY_START = "08:00:00"
DEFAULT_DAY_END = "20:00:00"
DEFAULT_POST_MOLT_FAST_DAYS = 7
DEFAULT_LIGHT_MODE = "fixed"
DEFAULT_STALE_MINUTES = 30
DEFAULT_ALARM_DELAY_MINUTES = 15

# Soorten die ook als adult vervellen (en pissebedden e.d. levenslang).
ADULT_MOLTING_DEVELOPMENT = ("molting_adult", "ametabolous")

# --- Status ---------------------------------------------------------------

PROBLEMS = [
    "temperature_critical",
    "temperature_low",
    "temperature_high",
    "humidity_low",
    "humidity_high",
    "water_temperature_low",
    "water_temperature_high",
    "sensor_unavailable",
    "feeding_overdue",
    "cleaning_overdue",
    "water_change_overdue",
    "enclosure_too_small",
]
CLIMATE_PROBLEMS = {
    "temperature_critical",
    "temperature_low",
    "temperature_high",
    "humidity_low",
    "humidity_high",
    "water_temperature_low",
    "water_temperature_high",
}
# Problemen waarvoor een melding gestuurd wordt (na de alarmvertraging).
ALARM_PROBLEMS = CLIMATE_PROBLEMS | {"sensor_unavailable"}
# Problemen die meteen gemeld worden, zonder vertraging.
CRITICAL_PROBLEMS = {"temperature_critical"}
