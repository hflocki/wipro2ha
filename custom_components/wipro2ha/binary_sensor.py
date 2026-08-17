from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant, callback

DOMAIN = "thitronik_wipro"

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([
        WiProSensor(hass, "Küchenfenster", 0), # Index/Bit für Küchenfenster
        WiProSensor(hass, "Alarmanlage Status", 1, BinarySensorDeviceClass.SAFETY)
    ])

class WiProSensor(BinarySensorEntity):
    def __init__(self, hass, name, byte_index, device_class=BinarySensorDeviceClass.WINDOW):
        self._hass = hass
        self._attr_name = f"Thitronik {name}"
        self._byte_index = byte_index
        self._attr_device_class = device_class
        self._attr_is_on = False

    async def async_added_to_hass(self):
        @callback
        def handle_raw_data(event):
            raw_hex = event.data.get("raw")
            # Beispielhafte Bit-Auswertung des Byte-Pakets:
            # Hier musst du deine spezifische Byte-Logik einfügen!
            if len(raw_hex) >= 16:
                byte_val = int(raw_hex[self._byte_index*2:(self._byte_index+1)*2], 16)
                self._attr_is_on = bool(byte_val & 0x01)
                self.async_write_ha_state()

        self._hass.bus.async_listen(f"{DOMAIN}_raw_data", handle_raw_data)