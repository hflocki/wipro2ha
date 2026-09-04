"""Binary sensor platform for the Thitronik WiPro III integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import WiProDataUpdateCoordinator

DOMAIN = "wipro2ha"

# Bit index -> contact name mapping (byte 6), reverse-engineered via
# nRF Connect (see docs/nrf_connect_guide.md). Bits 5-7 are not yet
# mapped; add them here once further contacts have been identified.
WIPRO_CONTACT_NAMES = {
    0: "Sensor 0",
    1: "Sensor 1",
    2: "Sensor 2",
    3: "Sensor 3",
    4: "Sensor 4",
    # 5: "Sensor 5",
    # 6: "Sensor 6",
    # 7: "Sensor 7",
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    coordinator: WiProDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Main entities: armed status, overall contact status, and raw data entity
    entities = [
        WiProAlarmSensor(
            coordinator,
            entry,
            "Alarmanlage Scharf",
            byte_index=1,
            bitmask=0x0C,
            #device_class=BinarySensorDeviceClass.LOCK,
        ),
        WiProSensor(
            coordinator,
            entry,
            "Funkkontakt Gesamt",
            byte_index=6,
            bitmask=0xFF,
            device_class=BinarySensorDeviceClass.WINDOW,
        ),
        WiProRawSensor(coordinator, entry, "Raw Data"),
    ]

    # Individual contact sensors for byte 6, named after the
    # reverse-engineered mapping (see docs/nrf_connect_guide.md).
    for bit, name in WIPRO_CONTACT_NAMES.items():
        bitmask = 1 << bit
        entities.append(
            WiProSensor(
                coordinator,
                entry,
                name,
                byte_index=6,
                bitmask=bitmask,
                device_class=BinarySensorDeviceClass.WINDOW,
            )
        )

    async_add_entities(entities)


class WiProBaseSensor(CoordinatorEntity[WiProDataUpdateCoordinator], BinarySensorEntity):
    """Base class for all WiPro binary sensors, driven by the shared coordinator."""

    def __init__(self, coordinator, entry, name, unique_suffix, device_class=None):
        super().__init__(coordinator)
        self._attr_name = f"WiPro {name}"
        self._attr_device_class = device_class
        self._attr_is_on = False

        # entry is optional so these classes stay directly unit-testable
        # (see tests/test_binary_sensor.py) without a full config entry.
        if entry is not None:
            self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry.entry_id)},
                name=entry.title,
                manufacturer="Thitronik",
                model="WiPro III",
            )

        # Apply whatever data the coordinator already has (e.g. after a
        # reload) instead of waiting for the next BLE notification.
        if coordinator is not None and coordinator.data is not None:
            self.update_from_hex(coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Called by the coordinator whenever a new payload has arrived."""
        if self.coordinator.data is not None:
            self.update_from_hex(self.coordinator.data)
        self.async_write_ha_state()

    def update_from_hex(self, data: bytes):
        """Base method to be overridden by subclasses for parsing data."""
        pass

class WiProByte6DiagnosticSensor(WiProBaseSensor):
    """Diagnosesensor für den exakten Bitcode von Byte 6."""

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name, unique_suffix="byte6_diagnostic")

    def update_from_hex(self, data: bytes):
        if len(data) > 6:
            val = data[6]
            self._attr_is_on = val > 0
            self._attr_extra_state_attributes = {
                "hex": f"0x{val:02X}",
                "dezimal": val,
                "binär": f"{val:08b}",  # Zeigt z. B. "00000100" an
            }
            
class WiProAlarmSensor(WiProBaseSensor):
    """Sensor specifically for exact bitmask match (e.g., Armed state on byte 1)."""

    def __init__(self, coordinator, entry, name, byte_index, bitmask, device_class=None):
        unique_suffix = f"byte{byte_index}_eq{bitmask:02x}"
        super().__init__(coordinator, entry, name, unique_suffix, device_class)
        self._byte_index = byte_index
        self._bitmask = bitmask

    def update_from_hex(self, data: bytes):
        if len(data) > self._byte_index:
            # Evaluates true only if all masked bits match exactly (e.g. 0x0C in byte 1)
            self._attr_is_on = (data[self._byte_index] & self._bitmask) == self._bitmask


class WiProSensor(WiProBaseSensor):
    """Generic sensor evaluating whether any bit in the bitmask is active."""

    def __init__(self, coordinator, entry, name, byte_index, bitmask, device_class=None):
        unique_suffix = f"byte{byte_index}_any{bitmask:02x}"
        super().__init__(coordinator, entry, name, unique_suffix, device_class)
        self._byte_index = byte_index
        self._bitmask = bitmask

    def update_from_hex(self, data: bytes):
        if len(data) > self._byte_index:
            # Evaluates true if any bit within the bitmask is set
            self._attr_is_on = bool(data[self._byte_index] & self._bitmask)


class WiProRawSensor(WiProBaseSensor):
    """Diagnostic sensor storing the raw hex string and split bytes in attributes."""

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name, unique_suffix="raw_data")

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
