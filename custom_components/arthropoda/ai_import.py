"""Caresheets inlezen met AI (HA 'AI Task', bv. Claude) en soortfoto's van iNaturalist.

AI-extractie
------------
- Bron: een webpagina (URL) of een geüpload bestand (PDF of foto van een caresheet).
- Webpagina's worden als tekst meegegeven; PDF's en foto's als bijlage
  (vereist een AI Task-entiteit die bijlagen ondersteunt).
- De AI moet YAML in ons caresheet-formaat teruggeven. Die wordt gevalideerd,
  maar NIET opgeslagen: de gebruiker kijkt het resultaat na en slaat zelf op.

iNaturalist
-----------
- Alleen foto's met een Creative Commons-licentie (of CC0); auteur, licentie
  en bronlink worden bewaard en getoond.
"""

from __future__ import annotations

from html.parser import HTMLParser
import logging
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote
import uuid

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .caresheet import CaresheetError, dump_documents, parse_caresheets, relax_caresheets
from .const import DEVELOPMENT, GROUPS, HABITATS, SEASONS, STAGES, SUBSTRATE_MOISTURE, VENTILATION

_LOGGER = logging.getLogger(__name__)

USER_AGENT = "ArthropodaKeeper/0.5 (Home Assistant integration)"
MAX_DOWNLOAD = 15 * 1024 * 1024
MAX_PAGE_CHARS = 60_000
AI_TASK_GENERATE_DATA = 1
AI_TASK_ATTACHMENTS = 2

ATTACHMENT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class ImportFailed(HomeAssistantError):
    """Inlezen mislukt (met een leesbare reden)."""


# --- AI-instructies ---------------------------------------------------------

INSTRUCTIONS = f"""\
You extract husbandry data for ONE arthropod species from the caresheet below (or attached)
and return it as YAML in the exact format shown. Return ONLY the YAML, no explanation,
no code fences.

Rules:
- Use ONLY information stated in the source. If a value is not in the source, leave the
  field out. Never guess or fill in typical values.
- Ranges are [min, max]. Temperatures in °C (convert from °F if needed), humidity in %.
- If the source gives different values per life stage (e.g. juveniles vs adults) or per
  season (e.g. winter rest / diapause / cooling), make a separate care profile for each.
  A profile only needs the fields that differ.
- Allowed values:
  group: {", ".join(GROUPS)}
  development: {", ".join(DEVELOPMENT)}
  habitat: {", ".join(HABITATS)}
  stage: {", ".join(STAGES)}
  season: {", ".join(SEASONS)}  (seasonal profiles also need months: list of 1-12)
  substrate_moisture: {", ".join(SUBSTRATE_MOISTURE)}
  ventilation: {", ".join(VENTILATION)}
- diapause: only if the source describes a winter rest / hibernation / diapause; give the
  duration in days (convert weeks/months), the months it usually starts and the life stage.
- feeder: true only if the source presents the species as a feeder insect.
- Common names: add the names you find, keyed by language code (nl, en, de, ...).
- Use ONLY the field names shown in the format. Do not invent new fields. Anything useful
  that has no field of its own goes into the free `extra:` block (species or profile),
  e.g. extra: {{time_to_adulthood_months: [12, 18], communal: false}}.
- Put remaining useful care info (substrate, enclosure size, prey, plants, special
  remarks) in the free-text fields shown (enclosure, diet, notes).

Format:
format: arthropoda-caresheet/1
species:
  scientific_name: Genus species
  common_names: {{nl: ..., en: ...}}
  group: tarantula
  development: molting_adult
  habitat: terrestrial
  taxonomy: {{order: ..., family: ...}}
  lifespan: {{female_years: [20, 30], male_years: [5, 7]}}
  adult_size: {{body_mm: [50, 60], legspan_mm: [130, 150]}}
  diet: {{prey: [cricket, roach], plants: [bramble]}}
  enclosure: {{substrate: ..., depth_cm: 10, min_size_cm: [30, 30, 30]}}
  legal: {{cites: II}}
  temperament: ...
  venom: ...
  urticating_hairs: true
  incubation_days: [40, 60]
  development_time: {{months_to_adult: [12, 18], instars_to_adult: 7}}
  diapause: {{min_days: 60, max_days: 120, start_months: [11, 12], stage: pupa, notes: ...}}
  feeder: false
  notes: ...
  extra: {{communal: false}}
care_profiles:
  - temp_day: [22, 26]
    temp_night: [18, 22]
    temp_max_safe: 32
    humidity: [55, 70]
    water_temp: [18, 24]
    light_hours: 12
    uv: false
    substrate_moisture: slightly_moist
    misting: "twice a week"
    ventilation: medium
    feeding_interval_days: 14
    cleaning_interval_days: 30
    substrate_change_interval_days: 365
    water_change_interval_days: 7
    post_molt_fast_days: 10
  - stage: juvenile
    feeding_interval_days: 5
  - season: winter
    months: [12, 1, 2]
    temp_day: [18, 22]
source: "<url or document name>"
"""


# --- hulpfuncties ------------------------------------------------------------


class _TextExtractor(HTMLParser):
    """Leesbare tekst uit HTML (zonder scripts, stijlen en navigatie)."""

    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()[:MAX_PAGE_CHARS]


def strip_fences(text: str) -> str:
    """Verwijder ```yaml ... ``` als de AI dat toch toevoegt."""
    match = re.search(r"```(?:ya?ml)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip() + "\n"


def media_dir(hass: HomeAssistant) -> Path | None:
    local = hass.config.media_dirs.get("local")
    return Path(local) / "arthropoda" if local else None


def save_attachment(hass: HomeAssistant, data: bytes, content_type: str, name: str) -> str:
    """Bewaar een bestand in de mediamap en geef de media-source-ID terug. (executor)"""
    folder = media_dir(hass)
    if folder is None:
        raise ImportFailed("Home Assistant heeft geen lokale mediamap (media_dirs: local).")
    ext = ATTACHMENT_TYPES.get(content_type)
    if ext is None:
        raise ImportFailed(f"Bestandstype {content_type} wordt niet ondersteund (PDF, JPG, PNG, WEBP).")
    folder.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(unquote(name)).stem)[:60] or "caresheet"
    filename = f"{stem}_{uuid.uuid4().hex[:6]}{ext}"
    (folder / filename).write_bytes(data)
    return f"media-source://media_source/local/arthropoda/{filename}"


def ai_entities(hass: HomeAssistant) -> list[dict[str, Any]]:
    """AI Task-entiteiten die gegevens kunnen genereren."""
    result = []
    for state in hass.states.async_all("ai_task"):
        features = state.attributes.get("supported_features", 0)
        if features & AI_TASK_GENERATE_DATA:
            result.append(
                {
                    "entity_id": state.entity_id,
                    "name": state.attributes.get("friendly_name", state.entity_id),
                    "attachments": bool(features & AI_TASK_ATTACHMENTS),
                }
            )
    return result


async def _download(hass: HomeAssistant, url: str) -> tuple[bytes, str]:
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                raise ImportFailed(f"De pagina gaf foutcode {resp.status}.")
            data = await resp.content.read(MAX_DOWNLOAD + 1)
            if len(data) > MAX_DOWNLOAD:
                raise ImportFailed("Het bestand is groter dan 15 MB.")
            return data, (resp.content_type or "").lower()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise ImportFailed(f"Kon {url} niet ophalen: {err}") from err


# --- AI-extractie -------------------------------------------------------------


async def async_extract(
    hass: HomeAssistant,
    *,
    entity_id: str | None,
    url: str | None = None,
    media_content_id: str | None = None,
    source_name: str | None = None,
    hint: str | None = None,
) -> dict[str, Any]:
    """Laat de AI een caresheet maken. Geeft {'yaml', 'error', 'species'} terug."""
    entities = {e["entity_id"]: e for e in ai_entities(hass)}
    if not entities:
        raise ImportFailed(
            "Er is geen AI-integratie met 'AI Task' ingesteld. Voeg bv. de Anthropic-integratie "
            "toe en maak een AI Task-entiteit aan."
        )
    entity_id = entity_id or next(iter(entities))
    if entity_id not in entities:
        raise ImportFailed(f"{entity_id} is geen bruikbare AI Task-entiteit.")

    instructions = INSTRUCTIONS
    attachments: list[dict[str, str]] = []
    source = source_name or url or "upload"

    if url:
        data, content_type = await _download(hass, url)
        if content_type in ATTACHMENT_TYPES:
            media_content_id = await hass.async_add_executor_job(
                save_attachment, hass, data, content_type, url.rsplit("/", 1)[-1]
            )
        else:
            text = html_to_text(data.decode("utf-8", errors="replace"))
            if len(text) < 200:
                raise ImportFailed("Op deze pagina staat te weinig tekst (misschien laadt ze via JavaScript).")
            instructions += f"\n\nSource URL: {url}\n\nCaresheet text:\n-----\n{text}\n-----\n"

    if media_content_id:
        if not entities[entity_id]["attachments"]:
            raise ImportFailed(
                f"{entities[entity_id]['name']} ondersteunt geen bijlagen (PDF/foto). "
                "Kies een andere AI-entiteit of gebruik een webpagina."
            )
        attachments.append({"media_content_id": media_content_id, "media_content_type": ""})
        instructions += f"\n\nThe caresheet is attached. Source: {source}\n"

    if hint:
        instructions += f"\n\nExtra instruction from the user: {hint}\n"

    try:
        response = await hass.services.async_call(
            "ai_task",
            "generate_data",
            {
                "task_name": "Arthropoda caresheet",
                "entity_id": entity_id,
                "instructions": instructions,
                **({"attachments": attachments} if attachments else {}),
            },
            blocking=True,
            return_response=True,
        )
    except HomeAssistantError as err:
        raise ImportFailed(f"De AI gaf een fout: {err}") from err

    raw = response.get("data") if isinstance(response, dict) else None
    if not isinstance(raw, str) or not raw.strip():
        raise ImportFailed("De AI gaf geen bruikbaar antwoord.")
    text = strip_fences(raw)
    # Onbekende/ongeldige velden niet weigeren maar naar 'extra' verplaatsen.
    text, moved = relax_caresheets(text)

    # Valideren; bij succes netjes herschrijven met bronvermelding.
    try:
        sheets = parse_caresheets(text)
    except CaresheetError as err:
        return {"yaml": text, "error": str(err), "species": [], "moved": moved}
    docs = []
    for sheet in sheets:
        doc = {
            "format": "arthropoda-caresheet/1",
            "species": sheet.species,
            "care_profiles": sheet.profiles,
            "source": f"{sheet.source or source} (AI-extractie – nakijken)",
        }
        docs.append(doc)
    return {
        "yaml": dump_documents(docs),
        "error": None,
        "species": [s.species["scientific_name"] for s in sheets],
        "moved": moved,
    }


# --- iNaturalist --------------------------------------------------------------

INAT_API = "https://api.inaturalist.org/v1"


async def async_inat_photos(hass: HomeAssistant, scientific_name: str, limit: int = 12) -> list[dict]:
    """Foto's met open licentie voor een soort (of geslacht) op iNaturalist."""
    session = async_get_clientsession(hass)
    headers = {"User-Agent": USER_AGENT}
    timeout = aiohttp.ClientTimeout(total=20)
    try:
        async with session.get(
            f"{INAT_API}/taxa", params={"q": scientific_name, "per_page": 1},
            headers=headers, timeout=timeout,
        ) as resp:
            results = (await resp.json()).get("results", [])
        if not results:
            return []
        async with session.get(
            f"{INAT_API}/taxa/{results[0]['id']}", headers=headers, timeout=timeout
        ) as resp:
            taxon = (await resp.json())["results"][0]
    except (aiohttp.ClientError, TimeoutError, KeyError, ValueError) as err:
        raise ImportFailed(f"iNaturalist is niet bereikbaar: {err}") from err

    photos = [tp["photo"] for tp in taxon.get("taxon_photos", [])]
    if not photos and taxon.get("default_photo"):
        photos = [taxon["default_photo"]]
    result = []
    for photo in photos:
        if not photo.get("license_code"):  # alle rechten voorbehouden → niet gebruiken
            continue
        medium = photo.get("medium_url") or photo.get("url")
        if not medium:
            continue
        result.append(
            {
                "url": medium.replace("/square.", "/medium."),
                "large_url": medium.replace("/medium.", "/large."),
                "attribution": photo.get("attribution", ""),
                "license": photo["license_code"].upper(),
                "source_url": f"https://www.inaturalist.org/photos/{photo['id']}" if photo.get("id") else
                              f"https://www.inaturalist.org/taxa/{taxon['id']}",
                "taxon": taxon.get("name"),
            }
        )
        if len(result) >= limit:
            break
    return result
