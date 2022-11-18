from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant, Context
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.network import get_url
from homeassistant.const import __version__ as current_version

import urllib.parse
import logging, json, time, uuid

from .manifest import manifest
from .http import HttpView

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.deprecated(manifest.domain)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = entry.data
    hass.http.register_view(HttpView)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = entry.data
    return True