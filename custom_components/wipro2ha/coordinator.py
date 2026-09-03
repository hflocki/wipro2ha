"""Data update coordinator for the Thitronik WiPro III integration."""
from __future__ import annotations

import asyncio
import logging

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "wipro2ha"
STATUS_UUID = "57695072-6f20-5374-6174-757320202020"
RECONNECT_DELAY = 10

CONF_MODE = "connection_mode"
CONF_INTERVAL = "scan_interval"
MODE_PUSH = "push"


class WiProDataUpdateCoordinator(DataUpdateCoordinator[bytes]):
    """Owns the BLE connection and holds the latest raw status payload."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.entry = entry
        self.address: str = entry.data.get("mac_address", entry.unique_id)
        self._client: BleakClientWithServiceCache | None = None
        self._connection_task: asyncio.Task | None = None

    @property
    def mode(self) -> str:
        """Get connection mode (Options take precedence over Entry Data)."""
        return self.entry.options.get(
            CONF_MODE, self.entry.data.get(CONF_MODE, MODE_PUSH)
        )

    @property
    def scan_interval(self) -> int:
        """Get scan interval in seconds."""
        return self.entry.options.get(
            CONF_INTERVAL, self.entry.data.get(CONF_INTERVAL, 30)
        )

    @callback
    def _handle_notification(self, _sender, data: bytearray) -> None:
        """Handle an incoming status notification from the WiPro BLE device."""
        self.async_set_updated_data(bytes(data))

    async def async_start(self) -> None:
        """Start the background connection/reconnect loop."""
        self._connection_task = self.hass.async_create_background_task(
            self._main_loop(), name=f"{DOMAIN}_ble_connection"
        )

    async def async_stop(self) -> None:
        """Stop the background connection loop and disconnect cleanly."""
        if self._connection_task:
            self._connection_task.cancel()
            self._connection_task = None

        if self._client and self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    async def _main_loop(self) -> None:
        """Main execution loop supporting both Push and Polling modes."""
        while True:
            try:
                ble_device = async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                if ble_device:
                    self._client = await establish_connection(
                        client_class=BleakClientWithServiceCache,
                        device=ble_device,
                        name=self.address,
                        hass=self.hass,
                    )

                    if self.mode == MODE_PUSH:
                        # PUSH MODUS: Permanent verbunden bleiben und benachrichtigen
                        await self._client.start_notify(
                            STATUS_UUID, self._handle_notification
                        )
                        self.last_update_success = True
                        _LOGGER.info("Connected to WiPro III BLE (Push Mode)")

                        while self._client.is_connected and self.mode == MODE_PUSH:
                            await asyncio.sleep(5)

                        if self._client.is_connected:
                            await self._client.stop_notify(STATUS_UUID)

                    else:
                        # POLLING MODUS: Einmalig lesen, trennen und X Sekunden warten
                        data = await self._client.read_gatt_char(STATUS_UUID)
                        self.async_set_updated_data(bytes(data))
                        self.last_update_success = True
                        _LOGGER.debug("Polled WiPro III BLE successfully")

                        await self._client.disconnect()
                        self._client = None

                        await asyncio.sleep(self.scan_interval)
                        continue

            except Exception as err:
                self.last_update_success = False
                self.async_update_listeners()
                _LOGGER.warning(
                    "BLE task error (%s mode): %s. Retrying in %ss...",
                    self.mode,
                    err,
                    RECONNECT_DELAY,
                )

            if self._client and self._client.is_connected:
                await self._client.disconnect()
            self._client = None

            await asyncio.sleep(RECONNECT_DELAY)
