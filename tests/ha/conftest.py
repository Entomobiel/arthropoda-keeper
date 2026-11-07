"""Fixtures voor integratietests met pytest-homeassistant-custom-component."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Laat HA de integratie uit custom_components laden."""
    return


@pytest.fixture(autouse=True)
def isolated_config_dir(hass, tmp_path):
    """Elke test een eigen configuratiemap, dus een eigen database."""
    hass.config.config_dir = str(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def no_inaturalist():
    """Geen echte netwerkoproepen naar iNaturalist in tests."""
    with patch(
        "custom_components.arthropoda.websocket_api.async_inat_photos",
        AsyncMock(return_value=[]),
    ) as mock:
        yield mock
