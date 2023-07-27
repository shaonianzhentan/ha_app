from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from .baidu_map import BaiduMap

from .manifest import manifest
from .const import CONVERSATION_ASSISTANT

DATA_SCHEMA = vol.Schema({})

DOMAIN = manifest.domain

class SimpleConfigFlow(ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        # 检测是否配置语音小助手
        if self.hass.data.get(CONVERSATION_ASSISTANT) is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors = {
                'base': 'conversation'
            })

        return self.async_create_entry(title=DOMAIN, data={})
    
    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry):
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        options = self.config_entry.options
        errors = {}
        if user_input is not None:
            # 验证一下
            ak = user_input.get('ak')
            service_id = user_input.get('service_id')
            map = BaiduMap(self.hass, ak, service_id)
            res = await map.async_get_entitylist()
            if res.get('status') == 0:
                return self.async_create_entry(title='', data=user_input)
            else:
                errors['base'] = 'fail'

        DATA_SCHEMA = vol.Schema({
            vol.Required("ak", default=options.get('ak')): str,
            vol.Required("service_id", default=options.get('service_id')): str
        })
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)