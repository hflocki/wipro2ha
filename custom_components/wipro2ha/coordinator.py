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


class WiProDataUpdateCoordinator(DataUpdateCoordinator[bytes]):
    """Owns the BLE connection and holds the latest raw status payload.

    This integration is push-based (BLE notifications), not polled, so no
    `update_interval` is set. New data arrives via the notification handler
    and is pushed to listening entities with `async_set_updated_data()`.
    Keeping this logic in one coordinator (instead of firing events on the
    HA event bus) avoids every entity independently parsing the same raw
    payload and gives entities a single, well-defined source of truth.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.entry = entry
        self.address: str = entry.data.get("mac_address", entry.unique_id)
        self._client: BleakClientWithServiceCache | None = None
        self._connection_task: asyncio.Task | None = None

    @callback
    def _handle_notification(self, _sender, data: bytearray) -> None:
        """Handle an incoming status notification from the WiPro BLE device."""
        self.async_set_updated_data(bytes(data))

    async def async_start(self) -> None:
        """Start the background connection/reconnect loop."""
        self._connection_task = self.hass.async_create_background_task(
            self._connect_and_subscribe(), name=f"{DOMAIN}_ble_connection"
        )

    async def async_stop(self) -> None:
        """Stop the background connection loop and disconnect cleanly."""
        if self._connection_task:
            self._connection_task.cancel()
            self._connection_task = None

        if self._client and self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    async def _connect_and_subscribe(self) -> None:
        """Maintain an active connection with auto-reconnect on failure."""
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
                    await self._client.start_notify(
                        STATUS_UUID, self._handle_notification
                    )
                    self.last_update_success = True
                    _LOGGER.info("Successfully connected to WiPro III BLE")

                    # Keep the task alive while the client stays connected.
                    while self._client.is_connected:
                        await asyncio.sleep(5)

            except Exception as err:  # noqa: BLE001 - the retry loop must survive any error
                self.last_update_success = False
                self.async_update_listeners()
                _LOGGER.warning(
                    "BLE connection lost or failed: %s. Retrying in %ss...",
                    err,
                    RECONNECT_DELAY,
                )

            await asyncio.sleep(RECONNECT_DELAY)
