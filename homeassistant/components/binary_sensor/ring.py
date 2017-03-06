"""
This component provides HA sensor support for Ring Door Bell/Chimes.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.ring/
"""
import logging
from datetime import timedelta

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.loader as loader

from homeassistant.components.binary_sensor import (
    BinarySensorDevice, PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_ENTITY_NAMESPACE, CONF_MONITORED_CONDITIONS,
    CONF_USERNAME, CONF_PASSWORD, ATTR_ATTRIBUTION,
    STATE_ON, STATE_OFF)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from requests.exceptions import HTTPError, ConnectTimeout

REQUIREMENTS = ['ring_doorbell==0.0.4']

_LOGGER = logging.getLogger(__name__)

NOTIFICATION_ID = 'ring_notification'
NOTIFICATION_TITLE = 'Ring Binary Sensor Setup'

DEFAULT_ENTITY_NAMESPACE = 'ring'
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3)

CONF_ATTRIBUTION = "Data provided by Ring.com"

# Sensor types: Name, category, device_class
SENSOR_TYPES = {
    'motion': ['Motion Sensor', ['doorbell'], 'motion'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up a sensor for a Ring device."""
    from ring_doorbell import Ring
    ring = Ring(config.get(CONF_USERNAME), config.get(CONF_PASSWORD))

    persistent_notification = loader.get_component('persistent_notification')
    try:
        ring.is_connected
    except (ConnectTimeout, HTTPError) as ex:
        _LOGGER.error("Unable to connect to Ring service: %s", str(ex))
        persistent_notification.create(
            hass, 'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)
        return False

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        for dev in ring.doorbells:
            if 'doorbell' in SENSOR_TYPES[sensor_type][1]:
                sensors.append(RingBinarySensor(dev,
                                          'doorbell',
                                          ring,
                                          sensor_type))
    add_devices(sensors, True)
    return True


class RingBinarySensor(BinarySensorDevice):
    """A binary sensor implementation for Ring device."""

    def __init__(self, name, family, ring, sensor_type):
        """Initialize a sensor for Ring device."""
        super(RingBinarySensor, self).__init__()
        self._ring = ring
        self._sensor_type = sensor_type
        self._family = family
        self._name = "{0} {1}".format(name,
                                      SENSOR_TYPES.get(self._sensor_type)[0])
        self._device_class = SENSOR_TYPES.get(self._sensor_type)[2]
        self._altname = name
        self._data = None
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the class of the binary sensor."""
        return STATE_ON if self._ring.check_activity else STATE_OFF

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {}

        attrs[ATTR_ATTRIBUTION] = CONF_ATTRIBUTION
        attrs['type'] = self._family

        if self._data:
            attrs['firmware'] = self._data['firmware_version']
            attrs['device_id'] = self._data['device_id']
            attrs['timezone'] = self._data['time_zone']

        return attrs

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data and updates the state."""
        if self._family == 'doorbell':
            self._data = self._ring.doorbell_attributes(self._altname)

            if self._data and self._sensor_type == 'motion':
                self._state = bool(self._ring.check_activity)
        _LOGGER.debug("3 debuggg %s", self)
