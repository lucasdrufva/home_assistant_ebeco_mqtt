"""Support for Ebeco wifi-enabled thermostats."""

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
)
#     MAIN_SENSOR,
#     PRESET_MANUAL,
#     PRESET_TIMER,
#     PRESET_WEEK,
#     EbecoClimateActions,
# )
from .entity import EbecoEntity




async def async_setup_entry(hass, config_entry, async_add_entities):
    mqtt_handler = hass.data[DOMAIN][config_entry.entry_id]["mqtt_handler"]
    async_add_entities([EbecoMqttClimate(hass, mqtt_handler, config_entry.data.get("serial"))])


class EbecoMqttClimate(ClimateEntity):
    def __init__(self, hass, mqtt_handler, serial):
        self._hass = hass
        self._mqtt_handler = mqtt_handler
        self._data = {"serial": serial}

        # Subscribe to data updates
        async def data_callback(data):
            self._data.update(data)
            self.async_write_ha_state()

        hass.async_create_task(mqtt_handler.async_subscribe(data_callback))
    
    @property
    def name(self):
        """Return the name of the device, if any."""
        return "Ebeco"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self._data['serial']}"

    @property
    def available(self) -> bool:
        """Entity is available once we have seen at least one payload."""
        return "regulatorStatus" in self._data and "userSettings" in self._data

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE
        )
    
    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes."""
        return [HVACMode.HEAT, HVACMode.OFF]

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        if self._data["userSettings"]["powerOn"]:
             return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self):
        """Return hvac action ie. the thermostat relay state."""
        if self.hvac_mode == HVACMode.HEAT:
            if self._data["regulatorStatus"]["regulatorState"]["relayOn"]:
                return HVACAction.HEATING
            return HVACAction.IDLE
        else:
            return HVACAction.OFF
    
    @property
    def temperature_unit(self):
        """Return the unit of measurement which this device uses."""
        return UnitOfTemperature.CELSIUS
    
    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 5

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 35

    @property
    def current_temperature(self):
        return self._data["regulatorStatus"]["sensorReadings"][1]["tUser"]/10 # Todo use real temp
    
    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._data["userSettings"]["manualControlTemp"]/10

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return PRECISION_WHOLE

    async def async_set_temperature(self, **kwargs):
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._target_temperature = temp
            await self._mqtt_handler.async_publish({"userSettings":{"manualControlTemp": int(temp*10)}})
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            await self._mqtt_handler.async_publish({"userSettings":{"powerOn": True}})
        elif hvac_mode == HVACMode.OFF:
            await self._mqtt_handler.async_publish({"userSettings":{"powerOn": False}})
        else:
            return