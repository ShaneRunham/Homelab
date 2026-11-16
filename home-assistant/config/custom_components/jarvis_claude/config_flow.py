"""One click, no settings: the service always listens on 127.0.0.1:10400."""
from homeassistant.config_entries import ConfigFlow

DOMAIN = "jarvis_claude"


class JarvisClaudeFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="JARVIS (Claude)", data={})
