from __future__ import annotations

from typing import Any
import voluptuous as vol
import hashlib

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

DATA_SCHEMA = vol.Schema({})

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

        key = str(uuid.uuid1())
        topic = hashlib.md5(str(uuid.uuid1()).encode('utf-8')).hexdigest()

        # 生成密钥二维码
        self.hass.services.call('persistent_notification', 'create', {
                    'title': '使用【家庭助理Android应用】扫码关联',
                    'message': '[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)'
                })

        return self.async_create_entry(title=DOMAIN, data={
            'key': key,
            'topic': topic
        })