"""Sensor platform for the Thitronik WiPro III integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import WiProDataUpdateCoordinator

DOMAIN = "wipro2ha"


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    coordinator: WiProDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        WiProByte6TextSensor(coordinator, entry, "Byte 6 Hex-Muster"),
    ]

    async_add_entities(entities)


class WiProByte6TextSensor(CoordinatorEntity[WiProDataUpdateCoordinator], SensorEntity):
    """Text sensor displaying the raw hex and binary pattern of Byte 6."""

    def __init__(self, coordinator, entry, name):
        super().__init__(coordinator)
        self._attr_name = f"WiPro {name}"
        self._attr_icon = "mdi:binary"
        self._attr_native_value = "0x00"

        if entry is not None:
            self._attr_unique_id = f"{entry.entry_id}_byte6_hex_pattern"
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
        if len(data) > 6:
            val = data[6]
            # Zeigt z. B. "0x0B (Binär: 00001011)" als Hauptwert an
            self._attr_native_value = f"0x{val:02X}"
            self._attr_extra_state_attributes = {
                "hex": f"0x{val:02X}",
                "dezimal": val,
                "binär": f"{val:08b}",
            }
