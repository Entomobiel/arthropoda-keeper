"""Zijbalkpaneel en dashboardkaarten registreren."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN, FRONTEND_VERSION, PANEL_URL_PATH, STATIC_URL

_LOGGER = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"
_STATIC_REGISTERED = f"{DOMAIN}_static_registered"


async def async_register_frontend(hass: HomeAssistant, title: str) -> None:
    """Bestanden serveren, kaarten laden op elk dashboard en het paneel tonen.

    Zonder HA-frontend (bv. in tests) wordt dit stil overgeslagen.
    """
    if hass.http is None or "frontend" not in hass.config.components:
        return

    from homeassistant.components import frontend, panel_custom
    from homeassistant.components.http import StaticPathConfig

    if not hass.data.get(_STATIC_REGISTERED):
        # Statische paden kunnen niet afgemeld worden: één keer per HA-sessie.
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
        )
        frontend.add_extra_js_url(hass, f"{STATIC_URL}/arthropoda-cards.js?v={FRONTEND_VERSION}")
        hass.data[_STATIC_REGISTERED] = True

    if not frontend.async_panel_exists(hass, PANEL_URL_PATH):
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name="arthropoda-panel",
            sidebar_title=title,
            sidebar_icon="mdi:spider",
            module_url=f"{STATIC_URL}/arthropoda-panel.js?v={FRONTEND_VERSION}",
            require_admin=False,
            config={},
        )


def async_unregister_panel(hass: HomeAssistant) -> None:
    if "frontend" not in hass.config.components:
        return
    from homeassistant.components import frontend

    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
