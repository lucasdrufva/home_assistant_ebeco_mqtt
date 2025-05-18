"""Handle MQTT communication for Ebeco."""

import logging
import json

from homeassistant.components import mqtt

_LOGGER = logging.getLogger(__name__)

class EbecoMqttHandler:
    """Single shared MQTT helper instance per config entry."""

    def __init__(self, hass, serial: str):
        self.hass = hass
        self.serial = serial
        self._callbacks: list[callable[[float], None]] = []
        self._unsub = None  # holds the unsubscribe function

    # --------- publisher helpers -------- #
    async def async_publish(self, data) -> None:
        await mqtt.async_publish(
            self.hass, f"devices/{self.serial}/messages/devicebound/data", json.dumps(data)
        )

    # --------- subscription helpers ----- #
    async def async_subscribe(self, cb):
        """Subscribe once and fan-out every update to all registered callbacks."""
       
        _LOGGER.info("Time to subscribe")
       
        # First caller creates the subscription
        if self._unsub is None:
            async def _message(msg):

                _LOGGER.info("Got data %s", msg.payload)

                for callback in self._callbacks:
                    self.hass.async_create_task(callback(json.loads(msg.payload)))


            _LOGGER.info("Subscribed to %s", f"devices/{self.serial}/messages/events/#")

            self._unsub = await mqtt.async_subscribe(
                self.hass, f"devices/{self.serial}/messages/events/#", _message
            )

        # Register the callback for this entity
        self._callbacks.append(cb)