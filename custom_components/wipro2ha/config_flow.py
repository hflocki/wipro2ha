from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
import voluptuous as vol

DOMAIN = "thitronik_wipro"

class ThitronikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Thitronik WiPro", data={})
        return self.async_show_form(step_id="confirm")

    async def async_step_user(self, user_input=None):
        # Manuelle Auswahl, falls kein Auto-Discovery getriggert wird
        return await self.async_step_confirm()