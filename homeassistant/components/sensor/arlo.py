"""
This component provides HA sensor for Netgear Arlo IP cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.arlo/
"""
from datetime import timedelta
import logging
import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.components.arlo import (
    CONF_ATTRIBUTION, DEFAULT_BRAND, DEFAULT_ENTITY_NAMESPACE)

from homeassistant.const import (
    CONF_ENTITY_NAMESPACE, CONF_MONITORED_CONDITIONS)
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity

DEPENDENCIES = ['arlo']

_LOGGER = logging.getLogger(__name__)

# sensor_type [ description, unit, icon ]
SENSOR_TYPES = {
    'total_cameras': ['Arlo Cameras', None, 'camera'],
    'recorded_today': ['Recorded Today', None, 'file-video'],
}


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ENTITY_NAMESPACE, default=DEFAULT_ENTITY_NAMESPACE):
        cv.string,
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})

SCAN_INTERVAL = timedelta(seconds=30)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up an Arlo IP sensor."""
    arlo = hass.data.get('arlo')

    #import rpdb; rpdb.set_trace()
    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        if sensor_type == 'recorded_today':
            cameras = arlo.cameras
            for cam in cameras:
                name = '{0}_{1}'.format(SENSOR_TYPES[sensor_type][0], cam.name)
                sensors.append(ArloSensor(hass, name, cam, sensor_type))
        else:
            sensors.append(ArloSensor(hass, SENSOR_TYPES[sensor_type][0], arlo, sensor_type))

    add_devices(sensors, True)
    return True


class ArloSensor(Entity):
    """An implementation of a Netgear Arlo IP sensor."""

    def __init__(self, hass, name, device, sensor_type):
        """Initialize an Arlo sensor."""
        super(ArloSensor, self).__init__()
        self._name = name
        self._hass = hass
        self._data = device
        self._sensor_type = sensor_type
        self._state = None
        self._icon = 'mdi:{}'.format(SENSOR_TYPES.get(self._sensor_type)[2])

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return SENSOR_TYPES.get(self._sensor_type)[1]

    def update(self):
        """Get the latest data and updates the state."""

        self._data.update()

        if self._sensor_type == 'total_cameras':
            self._state = len(self._data.cameras)

        elif self._sensor_type == 'recorded_today':
            self._state = len(self._data.captured_today)
