import logging
import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_PORT, DEFAULT_OUTPUT_PORTS
from .kvm_client import KvmClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["select"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data.get("host", DEFAULT_HOST)
    port = entry.data.get("port", DEFAULT_PORT)
    output_ports = DEFAULT_OUTPUT_PORTS

    # 创建KVM客户端
    client = KvmClient(hass.loop, host, port)
    await client.connect()

    # 立即获取所有端口的初始状态，确保重启后状态正确
    _LOGGER.info("🔍 Initializing all port statuses after connection")
    for port in range(1, DEFAULT_OUTPUT_PORTS + 1):
        _LOGGER.info(f"📋 Getting initial status for Output {port}")
        await client.get_current_status(port)

    hass.data[DOMAIN][entry.entry_id] = client

    # 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, platform) for platform in PLATFORMS]
        )
    )

    if unload_ok:
        client = hass.data[DOMAIN].pop(entry.entry_id)
        await client.disconnect()

    return unload_ok