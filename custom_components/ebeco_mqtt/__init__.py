import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .mqtt_handler import EbecoMqttHandler
from .const import DOMAIN


PLATFORMS = [
    Platform.CLIMATE,
    #Platform.SENSOR,
]

_LOGGER = logging.getLogger(__name__)



async def async_setup_entry(hass, config_entry):
    # Setup logic here (e.g. create MQTT subscriptions)


    serial = config_entry.data.get("serial")

    _LOGGER.info("Init setup run with serial %s", serial)

    mqtt_handler = EbecoMqttHandler(hass, serial)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "mqtt_handler": mqtt_handler,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True