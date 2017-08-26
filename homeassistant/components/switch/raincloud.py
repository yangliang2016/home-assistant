"""
Support for Melnor RainCloud sprinkler water timer.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.raincloud/
"""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.raincloud import (
    CONF_ATTRIBUTION, DEFAULT_ENTITY_NAMESPACE, DOMAIN)
from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_ENTITY_NAMESPACE, CONF_MONITORED_CONDITIONS,
    ATTR_ATTRIBUTION)
from homeassistant.helpers.entity import Entity

DEPENDENCIES = ['raincloud']

_LOGGER = logging.getLogger(__name__)

# Sensor types: label, desc, unit, icon
SENSOR_TYPES = {
    'watering_time': ['Watering Time', 'min', 'water-pump'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ENTITY_NAMESPACE, default=DEFAULT_ENTITY_NAMESPACE):
        cv.string,
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up a sensor for a raincloud device."""
    conf = config[DOMAIN]
    watering_time = conf.get(CONF_WATERING_TIME)
    raincloud = hass.data.get('raincloud')._data

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        # create an sensor for each zone managed by faucet
        for zone in raincloud.controller.faucet.zones:
            sensors.append(RainCloudSwitch(hass, zone, sensor_type))

    add_devices(sensors, True)
    return True


class RainCloudSwitch(Entity):
    """A sensor implementation for raincloud device."""

    def __init__(self, hass, data, sensor_type):
        """Initialize a sensor for raincloud device."""
        super().__init__()
        self._sensor_type = sensor_type
        self._data = data
        self._icon = 'mdi:{}'.format(SENSOR_TYPES.get(self._sensor_type)[2])
        self._name = "{0} {1}".format(
            self._data.name, SENSOR_TYPES.get(self._sensor_type)[0])
        self._state = 'on'

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {}

        attrs[ATTR_ATTRIBUTION] = CONF_ATTRIBUTION
        attrs['serial'] = self._data.serial
        attrs['current_time'] = self._data.current_time
        return attrs

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon
