"""Opvolging: onderhoudstaken en schattingen (pure functies, zonder Home Assistant).

Taken volgen uit de intervallen in het actieve verzorgingsprofiel:
- voederen        feeding_interval_days          (niet tijdens premolt/diapauze/voederpauze)
- schoonmaken     cleaning_interval_days
- substraat       substrate_change_interval_days
- waterwissel     water_change_interval_days

Een taak is verschuldigd op: laatste keer (of aanschafdatum) + interval.
Uitstellen ("snooze") schuift de vervaldatum op.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# soort taak -> (intervalsleutel in profiel, tellersleutel, dagboektype bij afvinken)
TASK_KINDS: dict[str, tuple[str, str, str]] = {
    "feeding": ("feeding_interval_days", "feeding", "feeding"),
    "cleaning": ("cleaning_interval_days", "cleaning", "spot_clean"),
    "substrate_change": ("substrate_change_interval_days", "substrate_change", "substrate_change"),
    "water_change": ("water_change_interval_days", "water_change", "water_change"),
    # Geen interval: eenmalige taak tijdens een diapauze.
    "diapause_end": ("", "", "diapause_end"),
}

EGG_TYPES = ("egg_sac", "ootheca", "egg_laying")

TEXTS = {
    "nl": {
        "feeding": "Voederen",
        "cleaning": "Schoonmaken",
        "substrate_change": "Substraat vervangen",
        "water_change": "Waterwissel",
        "diapause_end": "Uit diapauze halen",
        "equipment": "Onderhoud uitrusting",
        "plant_water": "Sproeien",
        "plant_fertilize": "Bemesten",
        "plant_sow": "Zaaien",
        "pot_replace": "Voerbakje vervangen",
        "diapause_window": "Diapauze kan eindigen: {name}",
        "overdue": "{days} dag(en) te laat",
        "due_today": "Vandaag",
        "molt_estimate": "Verwachte vervelling (schatting): {name}",
        "hatch_estimate": "Verwachte uitkomst {what}: {name}",
        "digest_title": "Arthropoda: onderhoud vandaag",
        "digest_problems": "Problemen",
        "digest_attention": "Aandacht (premolt, voer, kolonie, leeftijd)",
        "egg_sac": "eicocon",
        "ootheca": "ootheek",
        "egg_laying": "eieren",
        "document_expires": "Document vervalt: {title}",
        "digest_stock": "Voorraad laag",
        "digest_broods": "Uitkomst verwacht",
        "digest_documents": "Documenten die vervallen",
    },
    "en": {
        "feeding": "Feed",
        "cleaning": "Clean",
        "substrate_change": "Change substrate",
        "water_change": "Water change",
        "diapause_end": "End diapause",
        "equipment": "Equipment maintenance",
        "plant_water": "Water",
        "plant_fertilize": "Fertilize",
        "plant_sow": "Sow",
        "pot_replace": "Replace food pot",
        "diapause_window": "Diapause may end: {name}",
        "overdue": "{days} day(s) overdue",
        "due_today": "Today",
        "molt_estimate": "Expected molt (estimate): {name}",
        "hatch_estimate": "Expected hatch {what}: {name}",
        "digest_title": "Arthropoda: maintenance today",
        "digest_problems": "Problems",
        "digest_attention": "Attention (premolt, food, colony, age)",
        "egg_sac": "egg sac",
        "ootheca": "ootheca",
        "egg_laying": "eggs",
        "document_expires": "Document expires: {title}",
        "digest_stock": "Low stock",
        "digest_broods": "Hatching expected",
        "digest_documents": "Documents expiring",
    },
}


def texts(language: str | None) -> dict[str, str]:
    return TEXTS.get((language or "en")[:2], TEXTS["en"])


@dataclass(slots=True, frozen=True)
class Task:
    """Een (volgende) onderhoudstaak voor een dier of een kast."""

    animal_id: str
    kind: str
    due: datetime
    interval_days: float
    enclosure_id: int | None = None
    index: int | None = None  # welk toestel (bij kind == "equipment")
    label: str | None = None  # naam van het toestel of de plant
    plant: str | None = None  # plant.* (bij plant_water / plant_fertilize)

    @property
    def uid(self) -> str:
        if self.enclosure_id is not None:
            suffix = f":{self.index}" if self.index is not None else ""
            if self.plant is not None:
                suffix = f":{self.plant}" + (f":{self.index}" if self.index is not None else "")
            return f"enc{self.enclosure_id}:{self.kind}{suffix}"
        return f"{self.animal_id}:{self.kind}"

    @property
    def journal_type(self) -> str:
        return TASK_KINDS[self.kind][2] if self.kind in TASK_KINDS else ""


def compute_tasks(
    animal_id: str,
    values: dict[str, Any],
    last_ts: dict[str, datetime],
    baseline: datetime,
    feeding_paused: bool,
    snoozed: dict[str, datetime] | None = None,
    diapause: dict[str, Any] | None = None,
) -> list[Task]:
    """Volgende taak per soort onderhoud."""
    tasks: list[Task] = []
    for kind, (interval_key, counter, _journal) in TASK_KINDS.items():
        if not interval_key:
            continue
        interval = values.get(interval_key)
        if not interval:
            continue
        if kind == "feeding" and feeding_paused:
            continue
        due = (last_ts.get(counter) or baseline) + timedelta(days=interval)
        snooze = (snoozed or {}).get(kind)
        if snooze is not None and snooze > due:
            due = snooze
        tasks.append(Task(animal_id, kind, due, float(interval)))
    if diapause:
        end = diapause_end(diapause)
        if end is not None:
            snooze = (snoozed or {}).get("diapause_end")
            tasks.append(Task(animal_id, "diapause_end", max(end, snooze) if snooze else end, 0.0))
    return tasks


def diapause_end(diapause: dict[str, Any]) -> datetime | None:
    """Wanneer de diapauze mag eindigen: gepland einde, anders het vroegste einde."""
    if diapause.get("planned_end"):
        try:
            day = datetime.fromisoformat(diapause["planned_end"][:10])
        except ValueError:
            day = None
        if day is not None:
            start = datetime.fromisoformat(diapause["start"])
            return day.replace(hour=12, tzinfo=start.tzinfo)
    if diapause.get("earliest_end"):
        return datetime.fromisoformat(diapause["earliest_end"])
    return None


def project(task: Task, until: datetime, limit: int = 60) -> list[datetime]:
    """Vervaldatums van een terugkerende taak tot `until` (voor de kalender)."""
    result: list[datetime] = []
    due = task.due
    if task.interval_days <= 0:  # eenmalige taak
        return [due] if due <= until else []
    step = timedelta(days=task.interval_days)
    while due <= until and len(result) < limit:
        result.append(due)
        due += step
    return result


def estimate_next_molt(molt_times: list[datetime]) -> datetime | None:
    """Ruwe schatting: laatste vervelling + het laatste interval.

    Vervellingsintervallen worden met de leeftijd langer; het laatste interval
    is daarom een betere voorspeller dan het gemiddelde. Vanaf 2 vervellingen.
    """
    if len(molt_times) < 2:
        return None
    ordered = sorted(molt_times)
    return ordered[-1] + (ordered[-1] - ordered[-2])


def _incubation(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return float(value[0]), float(value[1])
    try:
        days = float(value)
    except (TypeError, ValueError):
        return None
    return days, days


def expected_hatches(
    entries: list[tuple[str, datetime, dict[str, Any]]],
    species_incubation: Any,
) -> list[tuple[str, datetime, datetime, datetime]]:
    """Verwachte uitkomstperiodes van eicocons/ootheken die nog niet uitkwamen.

    entries: (type, tijdstip, data), chronologisch, inclusief 'hatch'-regels.
    Een 'hatch' sluit alle eerder gelegde legsels af.
    Geeft (type, gelegd op, vroegste uitkomst, laatste uitkomst).
    """
    open_eggs: list[tuple[str, datetime, dict[str, Any]]] = []
    for entry_type, ts, data in sorted(entries, key=lambda e: e[1]):
        if entry_type == "hatch":
            open_eggs.clear()
        elif entry_type in EGG_TYPES:
            open_eggs.append((entry_type, ts, data))

    result = []
    for entry_type, ts, data in open_eggs:
        incubation = _incubation(data.get("incubation_days")) or _incubation(species_incubation)
        if incubation is None:
            continue
        lo, hi = incubation
        result.append((entry_type, ts, ts + timedelta(days=lo), ts + timedelta(days=hi)))
    return result
