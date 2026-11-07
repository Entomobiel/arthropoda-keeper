"""Genereer translations/nl.json en en.json vanuit één bron.

Gebruik: python scripts/gen_translations.py
Elke tekst is een tuple (nl, en), zodat beide talen altijd dezelfde sleutels hebben.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "custom_components" / "arthropoda" / "translations"

T = tuple[str, str]

OPTIONS: dict[str, dict[str, T]] = {
    "group": {
        "tarantula": ("Vogelspin", "Tarantula"),
        "true_spider": ("Spin (overig)", "True spider"),
        "scorpion": ("Schorpioen", "Scorpion"),
        "whip_spider": ("Zweepspin / zweepstaartschorpioen", "Whip spider / vinegaroon"),
        "mantis": ("Bidsprinkhaan", "Mantis"),
        "phasmid": ("Wandelende tak / blad", "Stick or leaf insect"),
        "orthoptera": ("Sprinkhaan / krekel", "Grasshopper / cricket"),
        "roach": ("Kakkerlak", "Cockroach"),
        "isopod": ("Pissebed", "Isopod"),
        "myriapod": ("Duizend- / miljoenpoot", "Centipede / millipede"),
        "beetle": ("Kever", "Beetle"),
        "ant": ("Mier", "Ant"),
        "lepidoptera": ("Vlinder / mot", "Butterfly / moth"),
        "aquatic": ("Waterinsect", "Aquatic insect"),
        "other": ("Overig", "Other"),
    },
    "development": {
        "hemimetabolous": ("Onvolledige gedaanteverwisseling (nimfen)", "Hemimetabolous (nymphs)"),
        "holometabolous": ("Volledige gedaanteverwisseling (larve, pop)", "Holometabolous (larva, pupa)"),
        "ametabolous": ("Geen gedaanteverwisseling", "Ametabolous"),
        "molting_adult": ("Vervelt ook als adult", "Molts as adult"),
    },
    "habitat": {
        "terrestrial": ("Bodembewoner", "Terrestrial"),
        "arboreal": ("Boombewoner", "Arboreal"),
        "fossorial": ("Graver", "Fossorial"),
        "semi_aquatic": ("Half-aquatisch", "Semi-aquatic"),
        "aquatic": ("Aquatisch", "Aquatic"),
    },
    "kind": {
        "individual": ("Individu", "Individual"),
        "colony": ("Kolonie / groep", "Colony / group"),
    },
    "sex": {
        "unknown": ("Onbekend", "Unknown"),
        "female": ("Vrouwtje", "Female"),
        "male": ("Mannetje", "Male"),
        "probably_female": ("Waarschijnlijk vrouwtje", "Probably female"),
        "probably_male": ("Waarschijnlijk mannetje", "Probably male"),
        "mixed": ("Gemengd", "Mixed"),
    },
    "stage": {
        "egg": ("Ei", "Egg"),
        "nymph": ("Nimf", "Nymph"),
        "larva": ("Larve", "Larva"),
        "pupa": ("Pop", "Pupa"),
        "juvenile": ("Juveniel", "Juvenile"),
        "subadult": ("Subadult", "Subadult"),
        "adult": ("Adult", "Adult"),
    },
    "origin": {
        "bred": ("Eigen kweek", "Own breeding"),
        "bought": ("Gekocht", "Bought"),
        "wild_caught": ("Wildvang", "Wild caught"),
        "gift": ("Gekregen", "Gift"),
        "unknown": ("Onbekend", "Unknown"),
    },
    "feeding_result": {
        "accepted": ("Gegeten", "Accepted"),
        "partial": ("Deels gegeten", "Partially eaten"),
        "refused": ("Geweigerd", "Refused"),
    },
    "task_kind": {
        "feeding": ("Voederen", "Feeding"),
        "cleaning": ("Schoonmaken", "Cleaning"),
        "substrate_change": ("Substraat vervangen", "Substrate change"),
        "water_change": ("Waterwissel", "Water change"),
    },
    "light_mode": {
        "fixed": ("Vaste uren (daglengte uit de caresheet)", "Fixed hours (day length from caresheet)"),
        "sun": ("Volgens de zon (zonsopgang tot -ondergang)", "Follow the sun (sunrise to sunset)"),
    },
    "season_mode": {
        "auto": ("Automatisch (volgens maanden)", "Automatic (by month)"),
        "normal": ("Normaal", "Normal"),
        "winter": ("Winter / diapauze", "Winter / diapause"),
        "breeding": ("Kweek", "Breeding"),
    },
    "entry_type": {
        "feeding": ("Gevoederd", "Fed"),
        "feeding_refused": ("Voer geweigerd", "Food refused"),
        "water_refill": ("Water bijgevuld", "Water refilled"),
        "remove_leftovers": ("Voedselresten verwijderd", "Leftovers removed"),
        "plant_food": ("Voedselplanten vervangen", "Food plants replaced"),
        "supplement": ("Supplement gegeven", "Supplement given"),
        "spot_clean": ("Plaatselijk schoongemaakt", "Spot clean"),
        "full_clean": ("Volledig schoongemaakt", "Full clean"),
        "substrate_change": ("Substraat vervangen", "Substrate changed"),
        "substrate_moisten": ("Substraat bevochtigd", "Substrate moistened"),
        "pest_check": ("Controle schimmel/mijten/plagen", "Mold/mite/pest check"),
        "misting_manual": ("Gesproeid", "Misted"),
        "climate_adjust": ("Klimaat aangepast", "Climate adjusted"),
        "water_change": ("Waterwissel", "Water change"),
        "water_test": ("Watertest", "Water test"),
        "filter_clean": ("Filter gereinigd", "Filter cleaned"),
        "premolt_observed": ("Premolt waargenomen", "Premolt observed"),
        "molt": ("Vervelling", "Molt"),
        "molt_problem": ("Vervelingsprobleem", "Molt problem"),
        "pupation": ("Verpopping", "Pupation"),
        "eclosion": ("Uit de pop gekomen", "Eclosion"),
        "stage_change": ("Levensfase gewijzigd", "Stage changed"),
        "diapause_start": ("Diapauze gestart", "Diapause started"),
        "diapause_end": ("Diapauze beëindigd", "Diapause ended"),
        "pairing": ("Koppeling", "Pairing"),
        "egg_sac": ("Eicocon", "Egg sac"),
        "ootheca": ("Ootheek", "Ootheca"),
        "egg_laying": ("Eieren gelegd", "Eggs laid"),
        "brood_pulled": ("Eicocon/ootheek apart gezet", "Brood pulled"),
        "hatch": ("Uitgekomen", "Hatched"),
        "split_colony": ("Kolonie gesplitst", "Colony split"),
        "measurement": ("Meting", "Measurement"),
        "count": ("Telling", "Count"),
        "observation": ("Observatie", "Observation"),
        "health_issue": ("Gezondheidsprobleem", "Health issue"),
        "treatment": ("Behandeling", "Treatment"),
        "death": ("Overleden", "Death"),
        "rehouse": ("Verhuisd", "Rehoused"),
        "escape": ("Ontsnapt", "Escaped"),
        "recaptured": ("Teruggevonden", "Recaptured"),
        "acquired": ("Aangeschaft", "Acquired"),
        "sold": ("Verkocht", "Sold"),
        "given_away": ("Weggegeven", "Given away"),
        "released": ("Vrijgelaten", "Released"),
        "document_added": ("Document toegevoegd", "Document added"),
        "note": ("Notitie", "Note"),
    },
}


def opts(key: str, lang: int) -> dict[str, str]:
    return {k: v[lang] for k, v in OPTIONS[key].items()}


ANIMAL_FIELDS: dict[str, tuple[T, T | None]] = {
    "name": (("Naam", "Name"), None),
    "species_id": (("Soort", "Species"), (
        "Voeg eerst soorten toe via de opties van de integratie (Configureren).",
        "Add species first via the integration options (Configure).",
    )),
    "kind": (("Type", "Type"), (
        "Een kolonie is een groep (bv. pissebedden, voederdieren) met een geschat aantal.",
        "A colony is a group (e.g. isopods, feeders) with an estimated count.",
    )),
    "sex": (("Geslacht", "Sex"), None),
    "stage": (("Levensfase", "Life stage"), None),
    "instar": (("Stadium (L-nummer / vervelling)", "Instar"), (
        "Bv. 4 voor L4. Wordt automatisch verhoogd bij elke vervelling in het dagboek.",
        "E.g. 4 for L4. Increases automatically with each logged molt.",
    )),
    "count": (("Aantal (kolonie)", "Count (colony)"), None),
    "born_at": (("Geboren / uitgekomen", "Born / hatched"), None),
    "acquired_at": (("Aangeschaft op", "Acquired on"), None),
    "origin": (("Herkomst", "Origin"), None),
}

SENSOR_FIELDS: dict[str, tuple[T, T | None]] = {
    "temperature_sensors": (("Temperatuursensor(en)", "Temperature sensor(s)"), (
        "Meerdere mag (warme en koele zijde): alle sensoren moeten binnen het bereik liggen.",
        "Multiple allowed (warm and cool side): all must be within range.",
    )),
    "humidity_sensor": (("Luchtvochtigheidssensor", "Humidity sensor"), None),
    "water_temperature_sensor": (("Watertemperatuursensor", "Water temperature sensor"), (
        "Voor waterinsecten.", "For aquatic species.",
    )),
    "food_plants": (("Voedselplanten", "Food plants"), (
        "Planten uit de plant monitor die je voor dit dier kweekt. Ze staan voorgeselecteerd bij "
        "het noteren van een voedering.",
        "Plants from the plant monitor that you grow for this animal. They are preselected when "
        "logging a feeding.",
    )),
}


ACTUATOR_FIELDS: dict[str, tuple[T, T | None]] = {
    "heater": (("Verwarming", "Heater"), (
        "Schakelaar (warmtemat, -kabel, -lamp), dimbare lamp (wordt proportioneel geregeld) "
        "of een bestaande thermostaat (climate).",
        "Switch (heat mat, cable, lamp), dimmable light (proportional control) "
        "or an existing thermostat (climate).",
    )),
    "mister": (("Vernevelaar / beregening", "Mister / rain system"), (
        "Schakelaar (geeft pulsen) of een script.", "Switch (pulsed) or a script.",
    )),
    "lights": (("Verlichting", "Lighting"), (
        "Volgt het dag/nachtritme.", "Follows the day/night rhythm.",
    )),
    "fan": (("Ventilator", "Fan"), (
        "Aan bij te hoge vochtigheid of temperatuur.", "On when humidity or temperature is too high.",
    )),
    "water_heater": (("Waterverwarming", "Water heater"), (
        "Voor waterinsecten; volgt de watertemperatuur.", "For aquatic species; follows water temperature.",
    )),
    "pumps": (("Pompen, filter, luchtpomp", "Pumps, filter, air pump"), (
        "Altijd aan, behalve in onderhoudsmodus.", "Always on, except in maintenance mode.",
    )),
}

CONTROL_FIELDS: dict[str, tuple[T, T | None]] = {
    "hysteresis": (("Hysterese verwarming", "Heater hysteresis"), (
        "Schakelmarge rond het midden van het doelbereik. Groter = minder vaak schakelen.",
        "Switching margin around the middle of the target range. Larger = fewer switches.",
    )),
    "mist_seconds": (("Duur van een vernevelpuls", "Mist pulse duration"), None),
    "mist_pause_minutes": (("Minimale pauze tussen pulsen", "Minimum pause between pulses"), None),
    "mist_max_per_day": (("Maximum pulsen per dag (op vochtigheid)", "Maximum pulses per day (humidity)"), (
        "0 = geen maximum. Vaste tijdstippen tellen niet mee.",
        "0 = no limit. Scheduled times are not limited.",
    )),
    "mist_times": (("Vaste vernevelmomenten", "Scheduled misting times"), (
        "Bv. 08:00, 20:00. Leeg = alleen op vochtigheid.",
        "E.g. 08:00, 20:00. Empty = humidity only.",
    )),
    "light_ramp_minutes": (("Op- en afdimmen (minuten)", "Dim up/down (minutes)"), (
        "Alleen voor dimbare lampen en vaste uren. 0 = meteen aan/uit.",
        "Only for dimmable lights and fixed hours. 0 = switch instantly.",
    )),
}


def fields(spec: dict[str, tuple[T, T | None]], lang: int) -> tuple[dict, dict]:
    data = {k: v[0][lang] for k, v in spec.items()}
    desc = {k: v[1][lang] for k, v in spec.items() if v[1]}
    return data, desc


def build(lang: int) -> dict:
    def t(nl: str, en: str) -> str:
        return (nl, en)[lang]

    animal_data, animal_desc = fields(ANIMAL_FIELDS, lang)
    sensor_data, sensor_desc = fields(SENSOR_FIELDS, lang)
    act_data, act_desc = fields(ACTUATOR_FIELDS, lang)
    ctl_data, ctl_desc = fields(CONTROL_FIELDS, lang)
    act_step = {
        "title": t("Klimaatsturing", "Climate control"),
        "description": t(
            "Kies wat de integratie mag aansturen. Alles is optioneel; zonder actuatoren wordt "
            "alleen bewaakt. Dieren die dezelfde actuator gebruiken, worden samen geregeld op "
            "het bereik waarin hun caresheets overlappen.",
            "Choose what the integration may control. Everything is optional; without actuators "
            "it only monitors. Animals sharing an actuator are controlled together using the "
            "range where their caresheets overlap."),
        "data": act_data,
        "data_description": act_desc,
    }
    ctl_step = {
        "title": t("Afstelling", "Tuning"),
        "description": t(
            "Bij gedeelde actuatoren geldt de afstelling van het eerst toegevoegde dier.",
            "For shared actuators, the tuning of the first added animal applies."),
        "data": ctl_data,
        "data_description": ctl_desc,
    }

    species_form = {
        "scientific_name": t("Wetenschappelijke naam", "Scientific name"),
        "common_name_nl": t("Nederlandse naam", "Dutch name"),
        "common_name_en": t("Engelse naam", "English name"),
        "group": t("Groep", "Group"),
        "development": t("Ontwikkeling", "Development"),
        "habitat": t("Leefwijze", "Habitat"),
        "feeder": t("Voederdier", "Feeder insect"),
        "temp_day_min": t("Temperatuur overdag min", "Day temperature min"),
        "temp_day_max": t("Temperatuur overdag max", "Day temperature max"),
        "temp_night_min": t("Temperatuur 's nachts min", "Night temperature min"),
        "temp_night_max": t("Temperatuur 's nachts max", "Night temperature max"),
        "humidity_min": t("Luchtvochtigheid min", "Humidity min"),
        "humidity_max": t("Luchtvochtigheid max", "Humidity max"),
        "water_temp_min": t("Watertemperatuur min", "Water temperature min"),
        "water_temp_max": t("Watertemperatuur max", "Water temperature max"),
        "feeding_interval_days": t("Voederen elke … dagen", "Feed every … days"),
        "cleaning_interval_days": t("Schoonmaken elke … dagen", "Clean every … days"),
        "water_change_interval_days": t("Waterwissel elke … dagen", "Water change every … days"),
        "notes": t("Notities", "Notes"),
    }

    entity = {
        "sensor": {
            "status": {
                "name": t("Status", "Status"),
                "state": {
                    "ok": t("OK", "OK"),
                    "problem": t("Probleem", "Problem"),
                    "inactive": t("Niet actief", "Inactive"),
                },
                "state_attributes": {"problems": {"name": t("Problemen", "Problems")}},
            },
            "temperature": {"name": t("Temperatuur", "Temperature")},
            "humidity": {"name": t("Luchtvochtigheid", "Humidity")},
            "water_temperature": {"name": t("Watertemperatuur", "Water temperature")},
            "stage": {"name": t("Levensfase", "Life stage"), "state": opts("stage", lang)},
            "instar": {"name": t("Stadium", "Instar")},
            "molt_count": {"name": t("Aantal vervellingen", "Molt count")},
            "colony_count": {"name": t("Koloniegrootte", "Colony size")},
            "days_since_feeding": {"name": t("Dagen sinds voedering", "Days since feeding")},
            "days_since_molt": {"name": t("Dagen sinds vervelling", "Days since molt")},
            "days_since_cleaning": {"name": t("Dagen sinds schoonmaak", "Days since cleaning")},
            "days_since_substrate_change": {
                "name": t("Dagen sinds substraatwissel", "Days since substrate change")
            },
            "days_since_water_change": {
                "name": t("Dagen sinds waterwissel", "Days since water change")
            },
            "next_feeding": {"name": t("Volgende voedering", "Next feeding")},
            "length": {"name": t("Lichaamslengte", "Body length")},
            "legspan": {"name": t("Spanwijdte", "Leg span")},
            "weight": {"name": t("Gewicht", "Weight")},
            "target_temperature_min": {"name": t("Doeltemperatuur min", "Target temperature min")},
            "target_temperature_max": {"name": t("Doeltemperatuur max", "Target temperature max")},
            "target_humidity_min": {"name": t("Doelvochtigheid min", "Target humidity min")},
            "target_humidity_max": {"name": t("Doelvochtigheid max", "Target humidity max")},
            "open_tasks": {"name": t("Openstaande taken", "Open tasks")},
            "low_stock": {"name": t("Voorraad laag", "Low stock")},
            "animals_with_problems": {"name": t("Dieren met een probleem", "Animals with a problem")},
            "climate_control_status": {
                "name": t("Status klimaatregeling", "Climate control status"),
                "state": {
                    "active": t("Actief", "Active"),
                    "paused": t("Gepauzeerd", "Paused"),
                    "monitoring": t("Alleen bewaken", "Monitoring only"),
                    "maintenance": t("Onderhoud", "Maintenance"),
                },
            },
        },
        "todo": {"maintenance": {"name": t("Onderhoud", "Maintenance")}},
        "calendar": {"calendar": {"name": t("Kalender", "Calendar")}},
        "image": {"photo": {"name": t("Foto", "Photo")}},
        "switch": {
            "climate_control": {"name": t("Klimaatsturing", "Climate control")},
            "maintenance": {"name": t("Onderhoudsmodus", "Maintenance mode")},
        },
        "binary_sensor": {
            "problem": {"name": t("Probleem", "Problem")},
            "climate_out_of_range": {"name": t("Klimaat buiten bereik", "Climate out of range")},
            "feeding_overdue": {"name": t("Voederen achterstallig", "Feeding overdue")},
            "premolt": {"name": t("Premolt", "Premolt")},
        },
        "select": {
            "season_mode": {"name": t("Seizoensprofiel", "Season profile"),
                            "state": opts("season_mode", lang)},
            "stage_select": {"name": t("Levensfase instellen", "Set life stage"),
                             "state": opts("stage", lang)},
        },
        "button": {
            "log_feeding": {"name": t("Gevoederd", "Fed")},
            "log_misting": {"name": t("Gesproeid", "Misted")},
            "log_spot_clean": {"name": t("Plaatselijk schoongemaakt", "Spot cleaned")},
            "log_water_refill": {"name": t("Water bijgevuld", "Water refilled")},
        },
    }

    f_animal = {"name": t("Dier(en)", "Animal(s)"), "description": t(
        "Een of meer dieren of kolonieën.", "One or more animals or colonies.")}
    f_ts = {"name": t("Tijdstip", "Timestamp"), "description": t(
        "Standaard: nu.", "Default: now.")}
    f_notes = {"name": t("Notities", "Notes"), "description": t(
        "Vrije tekst.", "Free text.")}
    common = {"animal": f_animal, "timestamp": f_ts, "notes": f_notes}

    def mm(nl: str, en: str) -> dict:
        return {"name": t(nl, en), "description": t(f"{nl} in mm.", f"{en} in mm.")}

    services = {
        "log_entry": {
            "name": t("Dagboekregel toevoegen", "Add journal entry"),
            "description": t("Voeg een handeling toe aan het dagboek.", "Add an action to the journal."),
            "fields": {
                **common,
                "type": {"name": t("Handeling", "Action"), "description": t(
                    "Soort handeling.", "Type of action.")},
                "data": {"name": t("Extra gegevens", "Extra data"), "description": t(
                    "Optionele velden, bv. {stage: adult} of {length_mm: 30}.",
                    "Optional fields, e.g. {stage: adult} or {length_mm: 30}.")},
            },
        },
        "log_feeding": {
            "name": t("Voedering noteren", "Log feeding"),
            "description": t("Noteer een voedering.", "Log a feeding."),
            "fields": {
                **common,
                "prey": {"name": t("Prooi/voedsel", "Prey/food"), "description": t(
                    "Bv. krekel, Dubia, fruitvlieg.", "E.g. cricket, Dubia, fruit fly.")},
                "quantity": {"name": t("Aantal", "Quantity"), "description": t(
                    "Aantal prooidieren.", "Number of prey items.")},
                "prey_size": {"name": t("Prooigrootte", "Prey size"), "description": t(
                    "Bv. L3, subadult, 1 cm.", "E.g. L3, subadult, 1 cm.")},
                "plants": {"name": t("Voedselplanten", "Food plants"), "description": t(
                    "Planten uit de plant monitor die je gevoerd hebt.",
                    "Plants from the plant monitor that you fed.")},
                "result": {"name": t("Resultaat", "Result"), "description": t(
                    "Een geweigerde voedering zet de teller niet op nul.",
                    "A refused feeding does not reset the counter.")},
            },
        },
        "log_molt": {
            "name": t("Vervelling noteren", "Log molt"),
            "description": t(
                "Noteer een vervelling: stadium +1, premolt uit, voederpauze start.",
                "Log a molt: instar +1, premolt off, feeding pause starts."),
            "fields": {
                **common,
                "complete": {"name": t("Geslaagd", "Successful"), "description": t(
                    "Uit = vervelingsprobleem (stadium wijzigt niet).",
                    "Off = molt problem (instar not changed).")},
                "instar_after": {"name": t("Stadium na vervelling", "Instar after molt"),
                                 "description": t("Leeg = huidig +1.", "Empty = current +1.")},
                "sex": {"name": t("Geslacht (exuvia)", "Sex (exuvia)"), "description": t(
                    "Geslacht bepaald op de vervellingshuid.", "Sex determined from the exuvia.")},
                "exuvia_kept": {"name": t("Exuvia bewaard", "Exuvia kept"), "description": t(
                    "Vervellingshuid bewaard.", "Molt skin kept.")},
                "legspan_mm": mm("Spanwijdte", "Leg span"),
                "length_mm": mm("Lichaamslengte", "Body length"),
            },
        },
        "add_measurement": {
            "name": t("Meting toevoegen", "Add measurement"),
            "description": t("Noteer lengte, spanwijdte, gewicht of aantal.",
                             "Log length, leg span, weight or count."),
            "fields": {
                **common,
                "length_mm": mm("Lichaamslengte", "Body length"),
                "legspan_mm": mm("Spanwijdte", "Leg span"),
                "weight_g": {"name": t("Gewicht", "Weight"), "description": t(
                    "Gewicht in gram.", "Weight in grams.")},
                "count": {"name": t("Aantal", "Count"), "description": t(
                    "Geteld aantal dieren (kolonie).", "Counted number of animals (colony).")},
            },
        },
        "set_stage": {
            "name": t("Levensfase instellen", "Set life stage"),
            "description": t("Wijzig levensfase en stadium (wordt in het dagboek genoteerd).",
                             "Change life stage and instar (logged in the journal)."),
            "fields": {
                **common,
                "stage": {"name": t("Levensfase", "Life stage"), "description": t(
                    "Nieuwe levensfase.", "New life stage.")},
                "instar": {"name": t("Stadium", "Instar"), "description": t(
                    "Optioneel L-nummer.", "Optional instar number.")},
            },
        },
        "get_journal": {
            "name": t("Dagboek opvragen", "Get journal"),
            "description": t("Geeft de recentste dagboekregels terug.",
                             "Returns the most recent journal entries."),
            "fields": {
                "animal": {"name": t("Dier", "Animal"), "description": t(
                    "Leeg = alle dieren.", "Empty = all animals.")},
                "type": {"name": t("Handeling", "Action"), "description": t(
                    "Alleen dit type (bv. molt).", "Only this type (e.g. molt).")},
                "limit": {"name": t("Maximum", "Limit"), "description": t(
                    "Maximaal aantal regels.", "Maximum number of entries.")},
            },
        },
        "import_caresheet": {
            "name": t("Caresheet importeren", "Import caresheet"),
            "description": t("Importeer soorten uit YAML (tekst of bestand in /config).",
                             "Import species from YAML (text or file in /config)."),
            "fields": {
                "yaml": {"name": "YAML", "description": t(
                    "Caresheet-tekst in het arthropoda-formaat.",
                    "Caresheet text in the arthropoda format.")},
                "path": {"name": t("Bestand", "File"), "description": t(
                    "Pad relatief aan de configuratiemap.", "Path relative to the config folder.")},
                "overwrite": {"name": t("Overschrijven", "Overwrite"), "description": t(
                    "Bestaande soorten vervangen.", "Replace existing species.")},
            },
        },
        "export_species": {
            "name": t("Soorten exporteren", "Export species"),
            "description": t("Exporteer soorten als caresheet-YAML.",
                             "Export species as caresheet YAML."),
            "fields": {
                "species": {"name": t("Soorten", "Species"), "description": t(
                    "Wetenschappelijke namen; leeg = alle.", "Scientific names; empty = all.")},
                "path": {"name": t("Bestand", "File"), "description": t(
                    "Optioneel: ook wegschrijven naar dit bestand in /config.",
                    "Optional: also write to this file in /config.")},
            },
        },
        "send_digest": {
            "name": t("Samenvatting nu versturen", "Send summary now"),
            "description": t("Stuurt meteen de dagelijkse samenvatting (handig om te testen).",
                             "Sends the daily summary right away (useful for testing)."),
        },
        "snooze_task": {
            "name": t("Taak uitstellen", "Snooze task"),
            "description": t("Stel een onderhoudstaak een aantal dagen uit.",
                             "Postpone a maintenance task by a number of days."),
            "fields": {
                "animal": {"name": t("Dier", "Animal"), "description": t("Het dier.", "The animal.")},
                "task": {"name": t("Taak", "Task"), "description": t("Welke taak.", "Which task.")},
                "days": {"name": t("Dagen", "Days"), "description": t(
                    "Uitstellen tot het begin van over zoveel dagen.",
                    "Postpone until the start of the day in this many days.")},
            },
        },
        "list_species": {
            "name": t("Soorten oplijsten", "List species"),
            "description": t("Geeft alle soorten in de database terug.",
                             "Returns all species in the database."),
        },
    }

    return {
        "config": {
            "step": {
                "user": {
                    "title": "Arthropoda Keeper",
                    "description": t(
                        "Maak je collectie aan. Daarna voeg je soorten toe via **Configureren** "
                        "en dieren via **Dier toevoegen**.",
                        "Create your collection. Then add species via **Configure** "
                        "and animals via **Add animal**."),
                    "data": {"name": t("Naam van de collectie", "Collection name")},
                }
            },
            "abort": {
                "already_configured": t("Er is al een collectie.", "A collection already exists."),
                "single_instance_allowed": t("Er is al een collectie.", "A collection already exists."),
            },
        },
        "config_subentries": {
            "animal": {
                "entry_type": t("Dier of kolonie", "Animal or colony"),
                "initiate_flow": {
                    "user": t("Dier toevoegen", "Add animal"),
                    "reconfigure": t("Dier wijzigen", "Edit animal"),
                },
                "step": {
                    "user": {
                        "title": t("Dier of kolonie toevoegen", "Add animal or colony"),
                        "data": animal_data,
                        "data_description": animal_desc,
                    },
                    "sensors": {
                        "title": t("Sensoren koppelen", "Link sensors"),
                        "description": t(
                            "Alles is optioneel. Dieren in hetzelfde terrarium mogen dezelfde sensoren gebruiken.",
                            "Everything is optional. Animals in the same enclosure may share sensors."),
                        "data": sensor_data,
                        "data_description": sensor_desc,
                    },
                    "reconfigure": {
                        "title": t("Dier wijzigen", "Edit animal"),
                        "data": animal_data,
                        "data_description": animal_desc,
                    },
                    "reconfigure_sensors": {
                        "title": t("Sensoren koppelen", "Link sensors"),
                        "data": sensor_data,
                        "data_description": sensor_desc,
                    },
                    "actuators": act_step,
                    "control": ctl_step,
                    "reconfigure_actuators": act_step,
                    "reconfigure_control": ctl_step,
                },
                "abort": {
                    "not_loaded": t("De integratie is niet geladen.", "The integration is not loaded."),
                    "no_species": t(
                        "Er zijn nog geen soorten. Voeg eerst een soort toe of importeer een caresheet "
                        "via Configureren.",
                        "There are no species yet. Add a species or import a caresheet via Configure first."),
                    "reconfigure_successful": t("Dier bijgewerkt.", "Animal updated."),
                },
            }
        },
        "options": {
            "step": {
                "init": {
                    "title": "Arthropoda Keeper",
                    "menu_options": {
                        "add_species": t("Soort toevoegen", "Add species"),
                        "import_caresheet": t("Caresheet importeren (YAML)", "Import caresheet (YAML)"),
                        "settings": t("Instellingen", "Settings"),
                    },
                },
                "settings": {
                    "title": t("Instellingen", "Settings"),
                    "data": {
                        "day_start": t("Dag begint om", "Day starts at"),
                        "day_end": t("Nacht begint om", "Night starts at"),
                        "light_mode": t("Dagritme", "Day rhythm"),
                        "post_molt_fast_days": t("Voederpauze na vervelling (dagen)",
                                                 "Feeding pause after molt (days)"),
                        "stale_minutes": t("Sensor verouderd na (minuten)",
                                           "Sensor stale after (minutes)"),
                        "alarm_delay_minutes": t("Alarmvertraging (minuten)",
                                                 "Alarm delay (minutes)"),
                        "notify_targets": t("Meldingen sturen naar", "Send notifications to"),
                        "digest_enabled": t("Dagelijkse samenvatting", "Daily summary"),
                        "digest_time": t("Samenvatting versturen om", "Send summary at"),
                    },
                    "data_description": {
                        "day_end": t(
                            "Wordt genegeerd als de caresheet een daglengte (light_hours) opgeeft.",
                            "Ignored when the caresheet sets a day length (light_hours)."),
                        "post_molt_fast_days": t(
                            "Standaard; een caresheet kan per soort een andere waarde opgeven.",
                            "Default; a caresheet can set a different value per species."),
                        "stale_minutes": t(
                            "Een sensor die zolang niets doorgeeft, telt als onbereikbaar: de "
                            "verwarming gaat dan uit. 0 = uitgeschakeld.",
                            "A sensor that reports nothing for this long counts as unavailable: "
                            "heating is switched off. 0 = disabled."),
                        "alarm_delay_minutes": t(
                            "Hoelang een probleem moet duren voor er gemeld wordt. Gevaarlijk "
                            "warm wordt altijd meteen gemeld.",
                            "How long a problem must last before notifying. Dangerously hot is "
                            "always notified immediately."),
                        "notify_targets": t(
                            "Bv. notify.mobile_app_mijn_gsm. Er komt altijd ook een melding in HA zelf.",
                            "E.g. notify.mobile_app_my_phone. A notification in HA itself is always created."),
                        "digest_enabled": t(
                            "Eén bericht per dag met de taken van vandaag en dieren met een probleem. "
                            "Zonder meldingsdoelen verschijnt het als melding in HA.",
                            "One message a day with today's tasks and animals with a problem. "
                            "Without notification targets it appears as a notification in HA."),
                    },
                },
                "add_species": {
                    "title": t("Soort toevoegen", "Add species"),
                    "description": t(
                        "Basisgegevens met één klimaatprofiel. Profielen per levensfase of seizoen "
                        "voeg je toe via een caresheet (YAML).",
                        "Basic data with one climate profile. Per-stage or seasonal profiles "
                        "can be added via a caresheet (YAML)."),
                    "data": species_form,
                },
                "import_caresheet": {
                    "title": t("Caresheet importeren", "Import caresheet"),
                    "description": t(
                        "Plak YAML of geef een bestand op (relatief aan /config). {error}",
                        "Paste YAML or give a file (relative to /config). {error}"),
                    "data": {
                        "yaml": "YAML",
                        "path": t("Bestand", "File"),
                        "overwrite": t("Bestaande soorten overschrijven", "Overwrite existing species"),
                    },
                },
            },
            "error": {
                "invalid_range": t("Bij elk bereik moeten min én max ingevuld zijn, met min ≤ max.",
                                   "Each range needs both min and max, with min ≤ max."),
                "species_exists": t("Deze soort bestaat al.", "This species already exists."),
                "invalid_caresheet": t("Caresheet ongeldig.", "Invalid caresheet."),
            },
            "abort": {
                "not_loaded": t("De integratie is niet geladen.", "The integration is not loaded."),
                "species_added": t("Soort toegevoegd: {names}", "Species added: {names}"),
                "caresheets_imported": t(
                    "Geïmporteerd: {saved}\nOvergeslagen (bestond al): {skipped}",
                    "Imported: {saved}\nSkipped (already existed): {skipped}"),
            },
        },
        "selector": {key: {"options": opts(key, lang)} for key in OPTIONS},
        "issues": {
            "range_conflict": {
                "title": t("Klimaatconflict bij {actuator}", "Climate conflict at {actuator}"),
                "description": t(
                    "De dieren {animals} delen {actuator}, maar hun doelbereiken overlappen niet. "
                    "De regelaar gebruikt nu het gemiddelde. Zet deze dieren in aparte "
                    "behuizingen, koppel een andere actuator of pas de caresheets aan.",
                    "The animals {animals} share {actuator}, but their target ranges do not "
                    "overlap. The controller now uses the average. Move them to separate "
                    "enclosures, link a different actuator or adjust the caresheets."),
            }
        },
        "entity": entity,
        "exceptions": {
            "not_loaded": {"message": t("Arthropoda Keeper is niet geladen.",
                                        "Arthropoda Keeper is not loaded.")},
            "unknown_animal": {"message": t("{device} is geen Arthropoda-dier.",
                                            "{device} is not an Arthropoda animal.")},
            "invalid_entry": {"message": t("Ongeldige dagboekregel: {error}",
                                           "Invalid journal entry: {error}")},
            "path_outside_config": {"message": t(
                "Het bestand moet in de configuratiemap staan.",
                "The file must be inside the config folder.")},
            "no_caresheet": {"message": t("Geef YAML-tekst of een bestand op.",
                                          "Provide YAML text or a file.")},
            "invalid_caresheet": {"message": t("Caresheet ongeldig: {error}",
                                               "Invalid caresheet: {error}")},
            "unknown_task": {"message": t("Deze taak bestaat niet (meer).",
                                          "This task does not exist (anymore).")},
            "no_values": {"message": t("Geef minstens één meetwaarde op.",
                                       "Provide at least one value.")},
        },
        "services": services,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for lang, code in ((0, "nl"), (1, "en")):
        (OUT / f"{code}.json").write_text(
            json.dumps(build(lang), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"Vertalingen geschreven naar {OUT}")


if __name__ == "__main__":
    main()
