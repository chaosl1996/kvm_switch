import logging
import asyncio
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_PORT, DEFAULT_OUTPUT_PORTS
from .kvm_client import KvmClient

_LOGGER = logging.getLogger(__name__)

class KvmSwitchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            # 验证连接
            host = user_input["host"]
            port = user_input["port"]
            output_ports = user_input.get("output_ports", DEFAULT_OUTPUT_PORTS)

            # 测试连接
            client = KvmClient(self.hass.loop, host, port)
            connected = await client.connect()
            if connected:
                await client.disconnect()
                return self.async_create_entry(
                    title="KVM Switch",
                    data={
                        "host": host,
                        "port": port,
                        "output_ports": output_ports
                    }
                )
            else:
                errors["base"] = "cannot_connect"

        # 显示配置表单
        data_schema = vol.Schema({
            vol.Required("host", default=DEFAULT_HOST): str,
            vol.Required("port", default=DEFAULT_PORT): int
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)