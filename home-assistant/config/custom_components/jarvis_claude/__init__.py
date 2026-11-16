"""JARVIS (Claude): a conversation agent that hands Assist requests to ~/homelab/jarvis-assist/claude-wyoming.py.

Unlike HA's own Wyoming agent it also sends who is asking (the HA user id), so the service can give Shane's login
full control of the PC and every other login only the devices exposed to Assist. See ~/homelab/README.md."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.CONVERSATION]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
