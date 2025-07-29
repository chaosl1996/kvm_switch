import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, COMMAND_MAP, STATE_MAP, DEFAULT_OUTPUT_PORTS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    client = hass.data[DOMAIN][entry.entry_id]
    output_ports = DEFAULT_OUTPUT_PORTS

    entities = []
    for port in range(1, output_ports + 1):
        entities.append(KvmSelect(client, port))

    async_add_entities(entities, True)

class KvmSelect(SelectEntity):
    def __init__(self, client, output_port):
        self.client = client
        self._output_port = output_port
        self._attr_name = f"OUT{output_port} Source"
        self._attr_unique_id = f"kvm_select_out{output_port}"
        self._attr_options = ["IN1", "IN2", "IN3", "IN4"]
        self._attr_current_option = None

        # 注册状态更新回调
        self.client.register_callback(str(output_port), self._update_state)

    async def async_select_option(self, option: str):
        # 根据输出口和选择的输入源获取对应的指令
        command_key = f"OUT{self._output_port}_{option}"
        if command_key in COMMAND_MAP:
            await self.client.send_command(COMMAND_MAP[command_key])
            self._attr_current_option = option
            self.async_write_ha_state()
        else:
            _LOGGER.error(f"No command mapping for {command_key}")

    def _update_state(self, device_code: str):
        # 从状态映射更新当前选项
        state_key = f"s{self._output_port}{device_code}"
        self._attr_current_option = STATE_MAP.get(state_key)
        self.async_write_ha_state()

    @property
    def icon(self):
        return "mdi:video-input-hdmi"