from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
import voluptuous as vol

DOMAIN = "wipro2ha"

class ThitronikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            mac_address = user_input["mac_address"].upper().strip()
            await self.async_set_unique_id(mac_address)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Thitronik ({mac_address})",
                data={"mac_address": mac_address}
            )

        # Neutraler Platzhalter für öffentliche Repositories
        data_schema = vol.Schema({
            vol.Required("mac_address", default="00:00:00:00:00:00"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        return self.async_create_entry(
            title=f"Thitronik ({discovery_info.address})",
            data={"mac_address": discovery_info.address}
        )
