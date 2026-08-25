import asyncio
import logging

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "wipro2ha"
STATUS_UUID = "57695072-6f20-5374-6174-757320202020"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Thitronik WiPro III from a config entry with permanent GATT connection."""
    hass.data.setdefault(DOMAIN, {})
    address = entry.data.get("mac_address", entry.unique_id)

    async def notification_handler(sender, data: bytearray):
        """Handle incoming status notifications from WiPro BLE."""
        hex_data = data.hex()
        hass.bus.async_fire(f"{DOMAIN}_raw_data", {"raw": hex_data})

    async def _connect_and_subscribe():
        """Maintain active connection loop with auto-reconnect."""
        while True:
            try:
                ble_device = async_ble_device_from_address(
                    hass, address, connectable=True
                )
                if ble_device:
                    client = await establish_connection(
                        client_class=BleakClientWithServiceCache,
                        device=ble_device,
                        name=address,
                        hass=hass,
                    )
                    hass.data[DOMAIN][entry.entry_id] = client

                    # Subscribe to notifications
                    await client.start_notify(STATUS_UUID, notification_handler)
                    _LOGGER.info("Successfully connected to WiPro III BLE")

                    # Keep task alive while client is connected
                    while client.is_connected:
                        await asyncio.sleep(5)

            except Exception as err:
                _LOGGER.warning(
                    "BLE connection lost or failed: %s. Retrying in 10s...", err
                )

            await asyncio.sleep(10)

    # Start permanent connection task in background
    conn_task = hass.async_create_background_task(
        _connect_and_subscribe(), name=f"{DOMAIN}_ble_connection"
    )
    hass.data[DOMAIN][f"{entry.entry_id}_task"] = conn_task

    await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Cancel connection background task
    conn_task = hass.data[DOMAIN].pop(f"{entry.entry_id}_task", None)
    if conn_task:
        conn_task.cancel()

    # Disconnect BLE client
    client = hass.data[DOMAIN].pop(entry.entry_id, None)
    if client and client.is_connected:
        await client.disconnect()

    return True
