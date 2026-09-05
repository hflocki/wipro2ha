"""The Thitronik WiPro III integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform  
from homeassistant.core import HomeAssistant

from .coordinator import WiProDataUpdateCoordinator

DOMAIN = "wipro2ha"
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Thitronik WiPro III from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = WiProDataUpdateCoordinator(hass, entry)
    await coordinator.async_start()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # On options change, reload coordinator loop
    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator: WiProDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop()
    await coordinator.async_start()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    coordinator: WiProDataUpdateCoordinator | None = hass.data[DOMAIN].pop(
        entry.entry_id, None
    )
    if coordinator:
        await coordinator.async_stop()

    return unload_ok
