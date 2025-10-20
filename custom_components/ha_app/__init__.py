from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .manifest import manifest
from .http import HttpView

CONFIG_SCHEMA = cv.deprecated(manifest.domain)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.http.register_view(HttpView)
    return True