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
        return self.entry.options.get(
            CONF_MODE, self.entry.data.get(CONF_MODE, MODE_PUSH)
        )

    @property
    def scan_interval(self) -> int:
        return self.entry.options.get(
            CONF_INTERVAL, self.entry.data.get(CONF_INTERVAL, 30)
        )

    @callback
    def _handle_notification(self, _sender, data: bytearray) -> None:
        raw_bytes = bytes(data)
        _LOGGER.debug("[%s] Empfangene BLE-Daten: %s", self.address, raw_bytes.hex())
        self.async_set_updated_data(raw_bytes)

    async def async_start(self) -> None:
        _LOGGER.info("[%s] Starte WiPro BLE Loop (Modus: %s)", self.address, self.mode)
        self._connection_task = self.hass.async_create_background_task(
            self._main_loop(), name=f"{DOMAIN}_ble_connection"
        )

    async def async_stop(self) -> None:
        _LOGGER.info("[%s] Stoppe WiPro BLE Loop", self.address)
        if self._connection_task:
            self._connection_task.cancel()
            self._connection_task = None

        if self._client and self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    async def _main_loop(self) -> None:
        while True:
            try:
                _LOGGER.debug("[%s] Suche BLE-Gerät im HA Bluetooth-Stack...", self.address)
                ble_device = async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )

                if not ble_device:
                    _LOGGER.warning("[%s] Gerät nicht in BLE-Reichweite / nicht von HA gefunden", self.address)
                else:
                    _LOGGER.debug("[%s] Verbindungsaufbau läuft...", self.address)
                    self._client = await establish_connection(
                        client_class=BleakClientWithServiceCache,
                        device=ble_device,
                        name=self.address,
                        hass=self.hass,
                    )

                    if self.mode == MODE_PUSH:
                        _LOGGER.info("[%s] BLE Verbunden. Aktiviere Notifications auf UUID %s", self.address, STATUS_UUID)
                        await self._client.start_notify(
                            STATUS_UUID, self._handle_notification
                        )

                        # Initialen Status abfragen und Status als erfolgreich markieren
                        init_data = await self._client.read_gatt_char(STATUS_UUID)
                        self.async_set_updated_data(bytes(init_data))
                        self.last_update_success = True

                        # Verbindung aufrechterhalten
                        while self._client.is_connected and self.mode == MODE_PUSH:
                            await asyncio.sleep(5)

                        if self._client and self._client.is_connected:
                            await self._client.stop_notify(STATUS_UUID)

                    else:
                        _LOGGER.debug("[%s] Lese GATT-Charakteristik (Polling)...", self.address)
                        data = await self._client.read_gatt_char(STATUS_UUID)
                        self.async_set_updated_data(bytes(data))
                        self.last_update_success = True
                        _LOGGER.info("[%s] Erfolgreich gelesen: %s", self.address, bytes(data).hex())

                        await self._client.disconnect()
                        self._client = None

                        await asyncio.sleep(self.scan_interval)
                        continue

            except Exception as err:
                _LOGGER.error("[%s] BLE-Fehler im Loop (%s): %s", self.address, type(err).__name__, err, exc_info=True)

            if self._client and self._client.is_connected:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass
            self._client = None

            _LOGGER.debug("[%s] Warte %ss vor neuem Verbindungsversuch...", self.address, RECONNECT_DELAY)
            await asyncio.sleep(RECONNECT_DELAY)
