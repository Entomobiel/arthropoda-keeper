"""Fase 5: caresheets via AI, soortfoto's (iNaturalist) en eigen foto's."""

from http import HTTPStatus

import aiohttp

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.setup import async_setup_component

from custom_components.arthropoda.const import DOMAIN

AI_YAML = """```yaml
format: arthropoda-caresheet/1
species:
  scientific_name: Phyllium philippinicum
  common_names: {nl: Wandelend blad}
  group: phasmid
  development: hemimetabolous
care_profiles:
  - temp_day: [22, 28]
    humidity: [60, 80]
    feeding_interval_days: 3
source: https://example.org/phyllium
```"""

PAGE = "<html><body><nav>menu</nav><h1>Phyllium philippinicum</h1>" + (
    "<p>Houd ze bij 22 tot 28 graden en een luchtvochtigheid van 60 tot 80 procent.</p>" * 10
) + "<script>alert(1)</script></body></html>"

PHOTO = {
    "url": "https://inaturalist-open-data.s3.amazonaws.com/photos/1/medium.jpg",
    "large_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/1/large.jpg",
    "attribution": "(c) Iemand, some rights reserved (CC BY)",
    "license": "CC-BY",
    "source_url": "https://www.inaturalist.org/photos/1",
    "taxon": "Brachypelma hamorii",
}


def _fake_ai(hass: HomeAssistant, answer: str, attachments: bool = True) -> list[ServiceCall]:
    calls: list[ServiceCall] = []

    async def generate(call: ServiceCall):
        calls.append(call)
        return {"conversation_id": "x", "data": answer}

    hass.services.async_register(
        "ai_task", "generate_data", generate, supports_response=SupportsResponse.ONLY
    )
    hass.states.async_set(
        "ai_task.claude", "unknown",
        {"supported_features": 3 if attachments else 1, "friendly_name": "Claude AI Task"},
    )
    return calls


async def _setup(hass: HomeAssistant, ws_client):
    await async_setup_component(hass, "websocket_api", {})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "C"})
    await hass.async_block_till_done()
    ws = await ws_client(hass)

    async def call(**msg):
        await ws.send_json_auto_id(msg)
        while True:
            res = await ws.receive_json()
            if res.get("type") == "result":
                return res

    return result["result"], call


async def test_extract_from_url(hass: HomeAssistant, hass_ws_client, aioclient_mock) -> None:
    calls = _fake_ai(hass, AI_YAML)
    aioclient_mock.get("https://example.org/phyllium", text=PAGE,
                       headers={"Content-Type": "text/html"})
    _, call = await _setup(hass, hass_ws_client)

    res = await call(type="arthropoda/ai/entities")
    assert res["result"]["entities"] == [
        {"entity_id": "ai_task.claude", "name": "Claude AI Task", "attachments": True}
    ]

    res = await call(type="arthropoda/caresheet/extract", url="https://example.org/phyllium")
    assert res["success"], res
    result = res["result"]
    assert result["error"] is None
    assert result["species"] == ["Phyllium philippinicum"]
    assert "AI-extractie" in result["yaml"] and "```" not in result["yaml"]
    # De paginatekst ging mee, zonder scripts en menu
    instructions = calls[0].data["instructions"]
    assert "60 tot 80 procent" in instructions
    assert "alert(1)" not in instructions and "menu" not in instructions.split("Caresheet text:")[1]

    # Niets automatisch opgeslagen
    res = await call(type="arthropoda/species/list")
    assert res["result"]["species"] == []


async def test_extract_reports_invalid_yaml(hass: HomeAssistant, hass_ws_client, aioclient_mock) -> None:
    _fake_ai(hass, "species: {scientific_name: X y, group: vogel}")
    aioclient_mock.get("https://example.org/p", text=PAGE, headers={"Content-Type": "text/html"})
    _, call = await _setup(hass, hass_ws_client)
    res = await call(type="arthropoda/caresheet/extract", url="https://example.org/p")
    assert res["success"]
    # Ongeldige waarde → bewaard onder 'extra' en gemeld, de rest blijft bruikbaar
    assert res["result"]["error"] is None
    assert res["result"]["moved"] == ["species › group"]
    assert "vogel" in res["result"]["yaml"]


async def test_extract_reports_broken_yaml(hass: HomeAssistant, hass_ws_client, aioclient_mock) -> None:
    _fake_ai(hass, "species: [dit is geen geldige caresheet")
    aioclient_mock.get("https://example.org/p", text=PAGE, headers={"Content-Type": "text/html"})
    _, call = await _setup(hass, hass_ws_client)
    res = await call(type="arthropoda/caresheet/extract", url="https://example.org/p")
    assert res["success"]
    assert "YAML" in res["result"]["error"]  # gebruiker ziet de tekst en kan verbeteren


async def test_extract_without_ai(hass: HomeAssistant, hass_ws_client) -> None:
    _, call = await _setup(hass, hass_ws_client)
    res = await call(type="arthropoda/caresheet/extract", url="https://example.org/p")
    assert not res["success"]
    assert res["error"]["code"] == "import_failed"
    assert "AI Task" in res["error"]["message"]


async def test_pdf_needs_attachment_support(hass: HomeAssistant, hass_ws_client) -> None:
    _fake_ai(hass, AI_YAML, attachments=False)
    _, call = await _setup(hass, hass_ws_client)
    res = await call(
        type="arthropoda/caresheet/extract",
        media_content_id="media-source://media_source/local/arthropoda/x.pdf",
    )
    assert not res["success"] and "bijlagen" in res["error"]["message"]


async def test_species_photo_and_image_entity(
    hass: HomeAssistant, hass_ws_client, no_inaturalist, aioclient_mock, hass_client
) -> None:
    await async_setup_component(hass, "http", {})
    no_inaturalist.return_value = [PHOTO]
    aioclient_mock.get(PHOTO["url"], content=b"\xff\xd8\xff-jpeg-")
    entry, call = await _setup(hass, hass_ws_client)

    await call(type="arthropoda/species/save", yaml=(
        "species: {scientific_name: Brachypelma hamorii, group: tarantula}\n"
        "care_profiles: [{temp_day: [22, 26]}]\n"
    ))
    (species,) = (await call(type="arthropoda/species/list"))["result"]["species"]
    res = await call(type="arthropoda/animal/add",
                     data={"name": "Rosie", "species_id": species["id"]})
    animal_id = res["result"]["animal_id"]
    await hass.async_block_till_done()

    # Bij een nieuwe soort wordt automatisch een foto opgezocht
    assert no_inaturalist.await_count >= 1
    state = hass.states.get("image.rosie_photo")
    assert state is not None
    assert state.attributes["source"] == "inaturalist"
    assert state.attributes["license"] == "CC-BY"

    # Foto bewerken in de caresheet-editor verliest de foto niet
    yaml = (await call(type="arthropoda/species/get", species_id=species["id"]))["result"]["yaml"]
    assert "photo" not in yaml
    await call(type="arthropoda/species/save", yaml=yaml, overwrite=True)
    await hass.async_block_till_done()
    assert hass.states.get("image.rosie_photo").attributes["source"] == "inaturalist"

    # De afbeelding zelf wordt opgehaald en geserveerd
    client = await hass_client()
    resp = await client.get(f"/api/image_proxy/image.rosie_photo")
    assert resp.status == HTTPStatus.OK
    assert (await resp.read()).startswith(b"\xff\xd8")

    # Eigen foto uploaden gaat voor
    form = aiohttp.FormData()
    form.add_field("file", b"\x89PNG-own-photo", filename="rosie.png", content_type="image/png")
    resp = await client.post(f"/api/arthropoda/photo/{animal_id}", data=form)
    assert resp.status == HTTPStatus.OK, await resp.text()
    await hass.async_block_till_done()
    assert hass.states.get("image.rosie_photo").attributes["source"] == "own"
    resp = await client.get("/api/image_proxy/image.rosie_photo")
    assert await resp.read() == b"\x89PNG-own-photo"

    # Eigen foto wissen → terug naar de soortfoto
    res = await call(type="arthropoda/animal/photo/delete", animal_id=animal_id)
    assert res["success"]
    await hass.async_block_till_done()
    assert hass.states.get("image.rosie_photo").attributes["source"] == "inaturalist"

    # Soortfoto wissen
    await call(type="arthropoda/species/photo/set", species_id=species["id"], photo=None)
    await hass.async_block_till_done()
    assert hass.states.get("image.rosie_photo").attributes["source"] is None


async def test_upload_caresheet_file(hass: HomeAssistant, hass_client, tmp_path) -> None:
    await async_setup_component(hass, "http", {})
    hass.config.media_dirs = {"local": str(tmp_path / "media")}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "C"})
    await hass.async_block_till_done()
    client = await hass_client()
    form = aiohttp.FormData()
    form.add_field("file", b"%PDF-1.4 test", filename="Phyllium caresheet.pdf",
                   content_type="application/pdf")
    resp = await client.post("/api/arthropoda/caresheet_upload", data=form)
    assert resp.status == HTTPStatus.OK, await resp.text()
    body = await resp.json()
    assert body["media_content_id"].startswith("media-source://media_source/local/arthropoda/Phyllium_caresheet_")
    assert list((tmp_path / "media" / "arthropoda").glob("*.pdf"))

    form = aiohttp.FormData()
    form.add_field("file", b"MZ", filename="virus.exe", content_type="application/octet-stream")
    resp = await client.post("/api/arthropoda/caresheet_upload", data=form)
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_extract_keeps_invented_fields(hass: HomeAssistant, hass_ws_client, aioclient_mock) -> None:
    """De AI bedenkt een eigen veld: niet weigeren maar onder 'extra' bewaren."""
    _fake_ai(hass, AI_YAML.replace(
        "  development: hemimetabolous\n",
        "  development: hemimetabolous\n  time_to_adulthood_months: [6, 8]\n",
    ))
    aioclient_mock.get("https://example.org/p", text=PAGE, headers={"Content-Type": "text/html"})
    _, call = await _setup(hass, hass_ws_client)
    res = await call(type="arthropoda/caresheet/extract", url="https://example.org/p")
    assert res["success"]
    assert res["result"]["error"] is None
    assert res["result"]["moved"] == ["species › time_to_adulthood_months"]
    assert "time_to_adulthood_months" in res["result"]["yaml"]
    # Het resultaat kan zo opgeslagen worden
    res = await call(type="arthropoda/species/save", yaml=res["result"]["yaml"])
    assert res["result"]["saved"] == ["Phyllium philippinicum"]
