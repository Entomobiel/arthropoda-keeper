"""HTTP-routes voor uploads (foto's van dieren, caresheet-bestanden).

Beide vereisen een aangemelde HA-gebruiker. Foto's van dieren staan in
/config/arthropoda/photos (gaan mee in back-ups) en worden getoond via de
foto-entiteit van het dier (met HA's eigen beveiligde afbeeldingslink).
"""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
import uuid

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .ai_import import ATTACHMENT_TYPES, ImportFailed, save_attachment
from .const import DATA_DIR, DOMAIN

MAX_UPLOAD = 15 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def photo_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DATA_DIR, "photos"))


def _runtime(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    return None


async def _read_upload(request: web.Request) -> tuple[bytes, str, str]:
    """Lees het veld 'file' uit een multipart-upload. Geeft (data, type, naam)."""
    reader = await request.multipart()
    async for part in reader:
        if part.name != "file":
            continue
        data = bytearray()
        while chunk := await part.read_chunk():
            data.extend(chunk)
            if len(data) > MAX_UPLOAD:
                raise web.HTTPRequestEntityTooLarge(max_size=MAX_UPLOAD, actual_size=len(data))
        content_type = (part.headers.get("Content-Type") or "").split(";")[0].lower()
        return bytes(data), content_type, part.filename or "upload"
    raise web.HTTPBadRequest(text="Geen bestand ontvangen (veld 'file').")


class AnimalPhotoView(HomeAssistantView):
    """POST /api/arthropoda/photo/{animal_id} – profielfoto van een dier."""

    url = "/api/arthropoda/photo/{animal_id}"
    name = "api:arthropoda:photo"
    requires_auth = True

    async def post(self, request: web.Request, animal_id: str) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        runtime = _runtime(hass)
        if runtime is None or animal_id not in (runtime.coordinator.data or {}):
            return self.json_message("Onbekend dier", HTTPStatus.NOT_FOUND)
        data, content_type, _name = await _read_upload(request)
        ext = PHOTO_TYPES.get(content_type)
        if ext is None:
            return self.json_message("Alleen JPG, PNG of WEBP.", HTTPStatus.BAD_REQUEST)

        folder = photo_dir(hass)
        filename = f"{animal_id}{ext}"

        def _write() -> None:
            folder.mkdir(parents=True, exist_ok=True)
            for old in folder.glob(f"{animal_id}.*"):
                old.unlink()
            (folder / filename).write_bytes(data)

        await hass.async_add_executor_job(_write)
        animal = runtime.coordinator.data[animal_id].animal
        info = {
            **animal.info,
            "photo": {"file": filename, "type": content_type, "updated": dt_util.utcnow().isoformat()},
        }
        await runtime.coordinator.async_update_animal(animal_id, info=info)
        return self.json({"ok": True})


class CaresheetUploadView(HomeAssistantView):
    """POST /api/arthropoda/caresheet_upload – PDF of foto van een caresheet."""

    url = "/api/arthropoda/caresheet_upload"
    name = "api:arthropoda:caresheet_upload"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        data, content_type, name = await _read_upload(request)
        if content_type not in ATTACHMENT_TYPES:
            return self.json_message("Alleen PDF, JPG, PNG of WEBP.", HTTPStatus.BAD_REQUEST)
        try:
            media_id = await hass.async_add_executor_job(save_attachment, hass, data, content_type, name)
        except ImportFailed as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)
        return self.json({"media_content_id": media_id, "name": name})


DOCUMENT_TYPES_FILES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def document_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DATA_DIR, "documents"))


class DocumentUploadView(HomeAssistantView):
    """POST /api/arthropoda/document – document (factuur, CITES, ...) bij een dier."""

    url = "/api/arthropoda/document"
    name = "api:arthropoda:document_upload"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        runtime = _runtime(hass)
        if runtime is None:
            return self.json_message("Niet geladen", HTTPStatus.SERVICE_UNAVAILABLE)
        fields: dict[str, str] = {}
        data, content_type, filename = b"", "", ""
        reader = await request.multipart()
        async for part in reader:
            if part.name == "file":
                buf = bytearray()
                while chunk := await part.read_chunk():
                    buf.extend(chunk)
                    if len(buf) > MAX_UPLOAD:
                        raise web.HTTPRequestEntityTooLarge(max_size=MAX_UPLOAD, actual_size=len(buf))
                data = bytes(buf)
                content_type = (part.headers.get("Content-Type") or "").split(";")[0].lower()
                filename = part.filename or "document"
            elif part.name:
                fields[part.name] = (await part.text()).strip()
        ext = DOCUMENT_TYPES_FILES.get(content_type) if data else None
        if data and ext is None:
            return self.json_message("Alleen PDF, JPG, PNG of WEBP.", HTTPStatus.BAD_REQUEST)

        stored = None
        if data:
            stored = f"{uuid.uuid4().hex}{ext}"
            folder = document_dir(hass)

            def _write() -> None:
                folder.mkdir(parents=True, exist_ok=True)
                (folder / stored).write_bytes(data)

            await hass.async_add_executor_job(_write)
        try:
            doc_id = await hass.async_add_executor_job(
                runtime.db.add_document,
                {
                    "animal_id": fields.get("animal_id") or None,
                    "type": fields.get("type") or "other",
                    "title": fields.get("title") or filename or "document",
                    "file": stored,
                    "content_type": content_type or None,
                    "issued_at": fields.get("issued_at") or None,
                    "expires_at": fields.get("expires_at") or None,
                    "notes": fields.get("notes") or None,
                },
            )
        except ValueError as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)
        await runtime.coordinator.async_refresh()
        return self.json({"id": doc_id})


class DocumentView(HomeAssistantView):
    """GET /api/arthropoda/document/{doc_id} – document openen (aangemeld of via ondertekende link)."""

    url = "/api/arthropoda/document/{doc_id}"
    name = "api:arthropoda:document"
    requires_auth = True

    async def get(self, request: web.Request, doc_id: str) -> web.StreamResponse:
        hass: HomeAssistant = request.app["hass"]
        runtime = _runtime(hass)
        if runtime is None or not doc_id.isdigit():
            return self.json_message("Niet gevonden", HTTPStatus.NOT_FOUND)
        doc = await hass.async_add_executor_job(runtime.db.get_document, int(doc_id))
        if not doc or not doc.get("file"):
            return self.json_message("Niet gevonden", HTTPStatus.NOT_FOUND)
        path = document_dir(hass) / doc["file"]
        if not await hass.async_add_executor_job(path.is_file):
            return self.json_message("Bestand ontbreekt", HTTPStatus.NOT_FOUND)
        return web.FileResponse(path, headers={"Content-Type": doc.get("content_type") or "application/octet-stream"})


def async_register_views(hass: HomeAssistant) -> None:
    if hass.http is None:
        return
    hass.http.register_view(AnimalPhotoView())
    hass.http.register_view(CaresheetUploadView())
    hass.http.register_view(DocumentUploadView())
    hass.http.register_view(DocumentView())
