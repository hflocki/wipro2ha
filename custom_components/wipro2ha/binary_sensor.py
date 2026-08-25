from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.core import HomeAssistant, callback

DOMAIN = "wipro2ha"

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([
        WiProAlarmSensor(hass, "Alarmanlage Scharf", byte_index=1, bitmask=0x0C, device_class=BinarySensorDeviceClass.SAFETY),
        WiProSensor(hass, "Funkkontakt Offen", byte_index=6, bitmask=0xFF, device_class=BinarySensorDeviceClass.WINDOW),
        WiProRawSensor(hass, "Raw Data")
    ])

class WiProBaseSensor(BinarySensorEntity):
    def __init__(self, hass, name, device_class=None):
        self._hass = hass
        self._attr_name = f"WiPro {name}"
        self._attr_device_class = device_class
        self._attr_is_on = False

    async def async_added_to_hass(self):
        @callback
        def handle_raw_data(event):
            raw_hex = event.data.get("raw")
            if raw_hex:
                try:
                    data = bytes.fromhex(raw_hex)
                    self.update_from_hex(data)
                    self.async_write_ha_state()
                except ValueError:
                    pass

        self._hass.bus.async_listen(f"{DOMAIN}_raw_data", handle_raw_data)

    def update_from_hex(self, data: bytes):
        pass

class WiProAlarmSensor(WiProBaseSensor):
    def __init__(self, hass, name, byte_index, bitmask, device_class=None):
        super().__init__(hass, name, device_class)
        self._byte_index = byte_index
        self._bitmask = bitmask

    def update_from_hex(self, data: bytes):
        if len(data) > self._byte_index:
            # Reagiert auf das 0x0C-Muster in Byte 1 für den Scharf-Status
            self._attr_is_on = (data[self._byte_index] & self._bitmask) == self._bitmask

class WiProSensor(WiProBaseSensor):
    def __init__(self, hass, name, byte_index, bitmask, device_class=None):
        super().__init__(hass, name, device_class)
        self._byte_index = byte_index
        self._bitmask = bitmask

    def update_from_hex(self, data: bytes):
        if len(data) > self._byte_index:
            # Reagiert, wenn in Byte 6 irgendein Bit ungleich 0 ist (Fenster offen)
            self._attr_is_on = bool(data[self._byte_index] & self._bitmask)

class WiProRawSensor(WiProBaseSensor):
    def update_from_hex(self, data: bytes):
        self._attr_is_on = True
        self._attr_extra_state_attributes = {
            "raw_hex": data.hex(),
            "byte_0": f"0x{data[0]:02X}" if len(data) > 0 else None,
            "byte_1": f"0x{data[1]:02X}" if len(data) > 1 else None,
            "byte_2": f"0x{data[2]:02X}" if len(data) > 2 else None,
            "byte_3": f"0x{data[3]:02X}" if len(data) > 3 else None,
            "byte_4": f"0x{data[4]:02X}" if len(data) > 4 else None,
            "byte_5": f"0x{data[5]:02X}" if len(data) > 5 else None,
            "byte_6": f"0x{data[6]:02X}" if len(data) > 6 else None,
            "byte_7": f"0x{data[7]:02X}" if len(data) > 7 else None,
        }
