from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant, Context
import homeassistant.helpers.config_validation as cv

import logging

from .manifest import manifest
from .http import HttpView
from baidu_map import BaiduMap

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.deprecated(manifest.domain)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = entry.data
    hass.http.register_view(HttpView)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    update_listener(hass, entry)
    return True

async def update_listener(hass, entry):
    options = entry.options
    ak = options.get('ak')
    service_id = options.get('service_id')
    if ak is not None and service_id is not None:
        hass.data.setdefault(manifest.domain, BaiduMap(hass, ak, service_id))

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = entry.data
    return True