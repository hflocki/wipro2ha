"""Config flow for the Thitronik WiPro III integration."""
from __future__ import annotations

import asyncio
import logging

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
)
import voluptuous as vol

DOMAIN = "wipro2ha"
_LOGGER = logging.getLogger(__name__)
CONNECT_TIMEOUT = 10


class ThitronikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            mac_address = user_input["mac_address"].upper().strip()
            await self.async_set_unique_id(mac_address)
            self._abort_if_unique_id_configured()

            if await self._async_can_connect(mac_address):
                return self.async_create_entry(
                    title=f"Thitronik ({mac_address})",
                    data={"mac_address": mac_address}
                )
            errors["base"] = "cannot_connect"

        # Neutraler Platzhalter für öffentliche Repositories
        data_schema = vol.Schema({
            vol.Required("mac_address", default="00:00:00:00:00:00"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def _async_can_connect(self, address: str) -> bool:
        """Try a short-lived connection to confirm the device is reachable."""
        ble_device = async_ble_device_from_address(self.hass, address, connectable=True)
        if ble_device is None:
            _LOGGER.debug(
                "No BLE device found for %s during setup validation", address
            )
            return False

        client = None
        try:
            client = await asyncio.wait_for(
                establish_connection(
                    client_class=BleakClientWithServiceCache,
                    device=ble_device,
                    name=address,
                    hass=self.hass,
                ),
                timeout=CONNECT_TIMEOUT,
            )
        except Exception as err:  # noqa: BLE001 - any failure here just means "unreachable"
            _LOGGER.debug(
                "Could not connect to %s during setup validation: %s", address, err
            )
            return False
        finally:
            if client and client.is_connected:
                await client.disconnect()

        return True

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        return self.async_create_entry(
            title=f"Thitronik ({discovery_info.address})",
            data={"mac_address": discovery_info.address}
        )
