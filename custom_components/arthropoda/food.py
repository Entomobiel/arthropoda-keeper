"""Voedselplanning: bakjes met voedselplanten volgen van zaaien tot opeten.

Twee soorten planten (profiel per plant.* van Plant Monitor):

- **Gewas** (`crop`; gras, erwten, bonen, kool, koolzaad ...):
  gezaaid → groeit (`growing`) → voerklaar na `days_to_ready` → in een dierenbak
  (`in_use`) → na `days_in_use` vervangen door een nieuw voerklaar bakje → op (`done`).
- **Vaste plant** (`perennial`; eik, liguster, braam ...):
  herstelt in de plantenkast (`recovering`) → klaar → in een dierenbak om
  af te grazen (`in_use`) → na `days_in_use` terug naar huis → herstelt
  `days_to_recover` dagen → weer klaar.

Taken (in de takenlijst, met aandringen/scanbewijs):
- `plant_sow`: elke `sow_every_days` zaaien (en meteen als er een tekort dreigt);
- `pot_replace`: een bakje in een dierenbak vervangen.

De prognose zoekt het eerste moment waarop een bakje vervangen moet worden
zonder dat er een voerklaar bakje van dezelfde plant klaarstaat (tekort).
"""

from __future__ import annotations

import heapq
from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

TASK_SOW = "plant_sow"
TASK_REPLACE = "pot_replace"

DEFAULTS: dict[str, dict[str, float]] = {
    "crop": {"days_to_ready": 14, "days_in_use": 7},
    "perennial": {"days_in_use": 7, "days_to_recover": 28},
}
ACTIVE_STATUSES = ("growing", "recovering", "in_use")


def setting(profile: dict[str, Any] | None, key: str) -> float | None:
    """Waarde uit het profiel, anders de standaardwaarde voor die soort plant."""
    profile = profile or {}
    kind = profile.get("kind") or "crop"
    value = profile.get(key)
    if value not in (None, "", 0):
        return float(value)
    default = DEFAULTS.get(kind, {}).get(key)
    return float(default) if default is not None else None


def _parse(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


def ready_time(pot: dict[str, Any], now: datetime) -> datetime | None:
    """Wanneer een bakje in de kast voerklaar is (None als het in gebruik/op is)."""
    if pot["status"] not in ("growing", "recovering"):
        return None
    ready = _parse(pot.get("ready_at"))
    return ready if ready is not None else now


def is_ready(pot: dict[str, Any], now: datetime) -> bool:
    ready = ready_time(pot, now)
    return ready is not None and ready <= now


def replace_due(pot: dict[str, Any], profile: dict[str, Any] | None) -> datetime | None:
    """Wanneer een bakje in een dierenbak vervangen moet worden."""
    if pot["status"] != "in_use":
        return None
    days = setting(profile, "days_in_use")
    since = _parse(pot.get("status_since"))
    if not days or since is None:
        return None
    return since + timedelta(days=days)


def forecast(
    pots: list[dict[str, Any]], profile: dict[str, Any] | None, now: datetime
) -> dict[str, Any]:
    """Voorraad van één plant: klaar, groeiend, in gebruik, eerste tekort."""
    supply = sorted(t for p in pots if (t := ready_time(p, now)) is not None)
    supply = [max(t, now) for t in supply]
    demand = sorted(d for p in pots if (d := replace_due(p, profile)) is not None)
    perennial = (profile or {}).get("kind") == "perennial"
    recover = setting(profile, "days_to_recover") or 0
    heap = list(supply)
    heapq.heapify(heap)
    shortfall = None
    for due in demand:
        if heap and heap[0] <= max(due, now):
            heapq.heappop(heap)
            if perennial:  # het afgegraasde bakje gaat terug en herstelt
                heapq.heappush(heap, max(due, now) + timedelta(days=recover))
        else:
            shortfall = due
            break
    upcoming = [t for t in supply if t > now]
    return {
        "ready": sum(1 for t in supply if t <= now),
        "growing": len(upcoming),
        "in_use": sum(1 for p in pots if p["status"] == "in_use"),
        "next_ready": min(upcoming).isoformat() if upcoming else None,
        "shortfall": shortfall.isoformat() if shortfall else None,
    }


STAGES = ("sown", "germinated", "ready", "recovering", "fed", "done", "failed")
LATE_GERMINATION = timedelta(days=2)


def stage(pot: dict[str, Any], profile: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    """Groeifase van een bakje, verwachte kiemdatum en of het kiemen laat is."""
    stages = pot.get("stages") or {}
    if pot["status"] in ("done", "failed"):
        current = pot["status"]
    elif pot["status"] == "in_use":
        current = "fed"
    elif is_ready(pot, now):
        current = "ready"
    elif pot["kind"] == "perennial":
        current = "recovering"
    else:
        current = "germinated" if stages.get("germinated") else "sown"
    germinate_at = None
    days = (profile or {}).get("days_to_germinate")
    sown = _parse(pot.get("sown_at"))
    if pot["kind"] == "crop" and days and sown is not None:
        germinate_at = sown + timedelta(days=float(days))
    late = current == "sown" and germinate_at is not None and now > germinate_at + LATE_GERMINATION
    return {
        "stage": current,
        "germinate_at": germinate_at.isoformat() if germinate_at else None,
        "late_germination": late,
    }


def sow_due(
    profile: dict[str, Any] | None,
    last_sown: datetime | None,
    shortfall: datetime | None,
    now: datetime,
) -> datetime | None:
    """Volgende zaaidag van een gewas (None: geen zaaitaak)."""
    if (profile or {}).get("kind", "crop") != "crop":
        return None
    every = (profile or {}).get("sow_every_days")
    today = dt_util.start_of_local_day(now)
    due = None
    if every:
        due = (last_sown + timedelta(days=float(every))) if last_sown else today
    if shortfall is not None:
        # Op tijd zaaien zodat het bakje klaar is vóór het tekort (ten vroegste vandaag).
        latest = shortfall - timedelta(days=setting(profile, "days_to_ready") or 0)
        pulled = max(latest, today)
        due = pulled if due is None else min(due, pulled)
    return due
