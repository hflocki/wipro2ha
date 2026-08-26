from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.core import HomeAssistant, callback

DOMAIN = "wipro2ha"

# Bit index -> contact name mapping (byte 6), reverse-engineered via
# nRF Connect (see docs/nrf_connect_guide.md). Bits 5-7 are not yet
# mapped; add them here once further contacts have been identified.
WIPRO_CONTACT_NAMES = {
    0: "Fahrerhaustür",
    1: "Beifahrertür",
    2: "Fenster",
    3: "Heckgarage",
    4: "Dachluke",
    # 5: "TODO",
    # 6: "TODO",
    # 7: "TODO",
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    # Main entities: Armed status, overall contact status, and raw data entity
    entities = [
        WiProAlarmSensor(
            hass,
            "Alarmanlage Scharf",
            byte_index=1,
            bitmask=0x0C,
            device_class=BinarySensorDeviceClass.SAFETY,
        ),
        WiProSensor(
            hass,
            "Funkkontakt Gesamt",
            byte_index=6,
            bitmask=0xFF,
            device_class=BinarySensorDeviceClass.WINDOW,
        ),
        WiProRawSensor(hass, "Raw Data"),
    ]

    # Individual contact sensors for byte 6, named after the
    # reverse-engineered mapping (see docs/nrf_connect_guide.md).
    for bit, name in WIPRO_CONTACT_NAMES.items():
        bitmask = 1 << bit
        entities.append(
            WiProSensor(
                hass,
                name,
                byte_index=6,
                bitmask=bitmask,
                device_class=BinarySensorDeviceClass.WINDOW,
            )
        )

    async_add_entities(entities)


class WiProBaseSensor(BinarySensorEntity):
    """Base class for all WiPro binary sensors."""

    def __init__(self, hass, name, device_class=None):
        self._hass = hass
        self._attr_name = f"WiPro {name}"
        self._attr_device_class = device_class
        self._attr_is_on = False

    async def async_added_to_hass(self):
        """Subscribe to incoming raw BLE data events from Home Assistant event bus."""
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
        """Base method to be overridden by subclasses for parsing data."""
        pass


class WiProAlarmSensor(WiProBaseSensor):
    """Sensor specifically for exact bitmask match (e.g., Armed state on byte 1)."""

    def __init__(self, hass, name, byte_index, bitmask, device_class=None):
        super().__init__(hass, name, device_class)
        self._byte_index = byte_index
        self._bitmask = bitmask

    def update_from_hex(self, data: bytes):
        if len(data) > self._byte_index:
            # Evaluates true only if all masked bits match exactly (e.g. 0x0C in byte 1)
            self._attr_is_on = (data[self._byte_index] & self._bitmask) == self._bitmask


class WiProSensor(WiProBaseSensor):
    """Generic sensor evaluating whether any bit in the bitmask is active."""

    def __init__(self, hass, name, byte_index, bitmask, device_class=None):
        super().__init__(hass, name, device_class)
        self._byte_index = byte_index
        self._bitmask = bitmask

    def update_from_hex(self, data: bytes):
        if len(data) > self._byte_index:
            # Evaluates true if any bit within the bitmask is set
            self._attr_is_on = bool(data[self._byte_index] & self._bitmask)


class WiProRawSensor(WiProBaseSensor):
    """Diagnostic sensor storing the raw hex string and split bytes in attributes."""

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
