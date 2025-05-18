import re
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_SERIAL_RE = re.compile(r"^(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}$", re.IGNORECASE)

DATA_SCHEMA = vol.Schema({vol.Required("serial"): str})

class EbecoMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ebeco MQTT."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:  # noqa: D401, WPS211
        """Ask for the serial number and create the entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            serial_raw: str = user_input["serial"].strip().upper()

            if not _SERIAL_RE.match(serial_raw):
                errors["serial"] = "invalid_serial"
            else:
                await self.async_set_unique_id(serial_raw)
                self._abort_if_unique_id_configured()

                # Friendly title – the model is unknown at this point; we update it later
                title = f"Ebeco thermostat ({serial_raw})"
                return self.async_create_entry(title=title, data={"serial": serial_raw})

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)