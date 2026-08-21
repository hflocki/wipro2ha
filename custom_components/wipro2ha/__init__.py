from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.bluetooth import async_ble_device_from_address
from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

DOMAIN = "wipro2ha"
STATUS_UUID = "57695072-6f20-5374-6174-757320202020"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    address = entry.data.get("mac_address", entry.unique_id)

    async def notification_handler(sender, data: bytearray):
        hex_data = data.hex()
        hass.bus.async_fire(f"{DOMAIN}_raw_data", {"raw": hex_data})

    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    
    if ble_device:
        # Nutzung von establish_connection verhindert die WARNUNG
        client = await establish_connection(
            client_class=BleakClientWithServiceCache,
            device=ble_device,
            name=address,
            hass=hass
        )
        
        await client.start_notify(STATUS_UUID, notification_handler)
        hass.data[DOMAIN][entry.entry_id] = client

    await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = hass.data[DOMAIN].pop(entry.entry_id, None)
    if client and client.is_connected:
        await client.disconnect()
    return True
