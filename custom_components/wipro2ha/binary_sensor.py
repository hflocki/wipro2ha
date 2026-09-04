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

# Standard-Zuordnung für alle 8 Bits (Kontakt 0 bis 7)
WIPRO_CONTACT_NAMES = {
    0: "Kontakt 0",
    1: "Kontakt 1",
    2: "Kontakt 2",
    3: "Kontakt 3",
    4: "Kontakt 4",
    5: "Kontakt 5",
    6: "Kontakt 6",
    7: "Kontakt 7",
}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    coordinator: WiProDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Haupt-Entitäten inklusive Diagnosesensoren
    entities = [
        WiProAlarmSensor(
            coordinator,
            entry,
            "Alarmanlage Scharf",
            byte_index=1,
            bitmask=0x0C,
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
        # JETZT KORREKT EINGEBUNDEN:
        WiProByte6DiagnosticSensor(coordinator, entry, "Byte 6 Diagnose"),
    ]

    # Einzelne Kontaktsensoren (0 bis 7)
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
                unique_suffix_override=f"contact_bit_{bit}",  # Eindeutige ID
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

        if entry is not None:
            self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry.entry_id)},
                name=entry.title,
                manufacturer="Thitronik",
                model="WiPro III",
            )

        if coordinator is not None and coordinator.data is not None:
            self.update_from_hex(coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Called by the coordinator whenever a new payload has arrived."""
        if self.coordinator.data is not None:
            self.update_from_hex(self.coordinator.data)
        self.async_write_ha_state()

    def update_from_hex(self, data: bytes):
        """Base method to be overridden by subclasses."""
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
        unique_suffix = f"byte{byte_index}_eq_{bitmask:02x}"
        super().__init__(coordinator, entry, name, unique_suffix, device_class)
        self._byte_index = byte_index
        self._bitmask = bitmask

    def update_from_hex(self, data: bytes):
        if len(data) > self._byte_index:
            self._attr_is_on = (data[self._byte_index] & self._bitmask) == self._bitmask


class WiProSensor(WiProBaseSensor):
    """Generic sensor evaluating whether any bit in the bitmask is active."""

    def __init__(self, coordinator, entry, name, byte_index, bitmask, device_class=None, unique_suffix_override=None):
        unique_suffix = unique_suffix_override or f"byte{byte_index}_any_{bitmask:02x}"
        super().__init__(coordinator, entry, name, unique_suffix, device_class)
        self._byte_index = byte_index
        self._bitmask = bitmask

    def update_from_hex(self, data: bytes):
        if len(data) > self._byte_index:
            self._attr_is_on = bool(data[self._byte_index] & self._bitmask)


class WiProRawSensor(WiProBaseSensor):
    """Diagnostic sensor storing raw hex string and split bytes in attributes."""

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator, entry, name, unique_suffix="raw_data")

    def update_from_hex(self, data: bytes):
        self._attr_is_on = True
        if len(data) > 0:
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
