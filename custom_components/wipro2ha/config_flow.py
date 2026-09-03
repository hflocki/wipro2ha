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
from homeassistant.core import callback
import voluptuous as vol

DOMAIN = "wipro2ha"
_LOGGER = logging.getLogger(__name__)
CONNECT_TIMEOUT = 10

CONF_MODE = "connection_mode"
CONF_INTERVAL = "scan_interval"

MODE_PUSH = "push"
MODE_POLL = "poll"

DEFAULT_MODE = MODE_PUSH
DEFAULT_INTERVAL = 30


class ThitronikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ThitronikOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            mac_address = user_input["mac_address"].upper().strip()
            await self.async_set_unique_id(mac_address)
            self._abort_if_unique_id_configured()

            if await self._async_can_connect(mac_address):
                return self.async_create_entry(
                    title=f"Thitronik ({mac_address})",
                    data={
                        "mac_address": mac_address,
                        CONF_MODE: user_input.get(CONF_MODE, DEFAULT_MODE),
                        CONF_INTERVAL: user_input.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                    },
                )
            errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required("mac_address", default="00:00:00:00:00:00"): str,
            vol.Required(CONF_MODE, default=DEFAULT_MODE): vol.In({
                MODE_PUSH: "Dauerhaft (Push / Notifications)",
                MODE_POLL: "Intervall (Polling)",
            }),
            vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=3600)
            ),
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
            _LOGGER.debug("No BLE device found for %s during setup validation", address)
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
        except Exception as err:
            _LOGGER.debug("Could not connect to %s: %s", address, err)
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
            data={
                "mac_address": discovery_info.address,
                CONF_MODE: DEFAULT_MODE,
                CONF_INTERVAL: DEFAULT_INTERVAL,
            }
        )


class ThitronikOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Thitronik WiPro III."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_mode = self.config_entry.options.get(
            CONF_MODE, self.config_entry.data.get(CONF_MODE, DEFAULT_MODE)
        )
        current_interval = self.config_entry.options.get(
            CONF_INTERVAL, self.config_entry.data.get(CONF_INTERVAL, DEFAULT_INTERVAL)
        )

        options_schema = vol.Schema({
            vol.Required(CONF_MODE, default=current_mode): vol.In({
                MODE_PUSH: "Dauerhaft (Push / Notifications)",
                MODE_POLL: "Intervall (Polling)",
            }),
            vol.Optional(CONF_INTERVAL, default=current_interval): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=3600)
            ),
        })

        return self.async_show_form(step_id="init", data_schema=options_schema)
