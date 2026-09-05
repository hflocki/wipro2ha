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

# Zuordnung: (Name, Exakter Hex-Wert / Maske)
# Wir nutzen exakte Byte-Muster, damit Kombi-Signale (z. B. 0x0B im Bad)
# nicht mehr versehentlich mehrere Kontakte gleichzeitig auslösen.
EXACT_CONTACT_MAPPING = [
    ("Kontakt 0", 0x09),
    ("Kontakt 1", 0x0A),
    ("Kontakt 2", 0x04),  
    ("Kontakt 3", 0x08),  
    ("Kontakt 4", 0x03),  
    ("Kontakt 5", 0x0B),  
    ("Kontakt 6", 0x10), #unknown
    ("Kontakt 7", 0x20), #unknown
]


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    coordinator: WiProDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Haupt-Entitäten
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
        WiProByte6DiagnosticSensor(coordinator, entry, "Byte 6 Diagnose"),
    ]

    # Generische Kontaktsensoren Kontakt 0 bis 7 auf exakte Matches prüfen
    for index, (name, match_val) in enumerate(EXACT_CONTACT_MAPPING):
        entities.append(
            WiProExactMatchSensor(
                coordinator,
                entry,
                name,
                byte_index=6,
                target_value=match_val,
                device_class=BinarySensorDeviceClass.WINDOW,
                unique_suffix_override=f"contact_exact_{index}",
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


class WiProExactMatchSensor(WiProBaseSensor):
    """Sensor that triggers ONLY if byte value matches target value exactly."""

    def __init__(self, coordinator, entry, name, byte_index, target_value, device_class=None, unique_suffix_override=None):
        unique_suffix = unique_suffix_override or f"byte{byte_index}_eq_{target_value:02x}"
        super().__init__(coordinator, entry, name, unique_suffix, device_class)
        self._byte_index = byte_index
        self._target_value = target_value

    def update_from_hex(self, data: bytes):
        if len(data) > self._byte_index:
            self._attr_is_on = (data[self._byte_index] == self._target_value)


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
                "binär": f"{val:08b}",
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
