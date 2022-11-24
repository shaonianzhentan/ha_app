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

    def handle_event(event):
        data = event.data
        dev_id = data.get('id')
        states = hass.states.async_all('persistent_notification')
        for state in states:
            if state.entity_id.startswith(f'persistent_notification.{dev_id}'):
                message = state.attributes.get('message')
                result = json.loads(message)
                result['id'] = state.entity_id.replace('persistent_notification.', '')
                hass.bus.fire(dev_id, result)

    await hass.async_add_executor_job(hass.bus.listen, "ha_app",  handle_event)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = entry.data
    return True