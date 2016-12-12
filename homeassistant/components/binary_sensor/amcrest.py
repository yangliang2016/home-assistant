"""
This component provides basic support for Amcrest IP cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.amcrest/
"""
import logging

import voluptuous as vol

import homeassistant.loader as loader

from homeassistant.components.binary_sensor import (
        BinarySensorDevice, PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_HOST, CONF_MONITORED_CONDITIONS,
    CONF_USERNAME, CONF_PASSWORD, CONF_PORT,
    STATE_ON, STATE_OFF)
from homeassistant.helpers import config_validation as cv

REQUIREMENTS = ['amcrest==1.0.0']

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 80

SCAN_INTERVAL = 30

SENSOR_TYPES = {
    'motion_detection': ['Motion', 'motion'],
    'recording': ['Recording', None],
}

NOTIFICATION_ID = 'amcrest_notification'
NOTIFICATION_TITLE = 'Amcrest Binary Sensor Setup'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up a binary sensor for an Amcrest IP Camera."""
    from amcrest import AmcrestCamera

    data = AmcrestCamera(
        config.get(CONF_HOST), config.get(CONF_PORT),
        config.get(CONF_USERNAME), config.get(CONF_PASSWORD))

    persistent_notification = loader.get_component('persistent_notification')
    try:
        data.camera.current_time
    # pylint: disable=broad-except
    except Exception as ex:
        _LOGGER.error("Unable to connect to Amcrest camera: %s", str(ex))
        persistent_notification.create(
            hass, 'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)
        return False

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        sensors.append(AmcrestSensor(data, sensor_type))

    add_devices(sensors)

    return True


class AmcrestSensor(BinarySensorDevice):
    """An binary sensor implementation for Amcrest IP camera."""

    def __init__(self, data, sensor_type):
        """Initialize an binary sensor for Amcrest camera."""
        super(AmcrestSensor, self).__init__()
        self._data = data
        self._name = SENSOR_TYPES.get(sensor_type)[0]
        self._sensor_type = sensor_type
        self._state = STATE_ON
        self._sensor_class = SENSOR_TYPES.get(sensor_type)[1]
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def sensor_class(self):
        """Return the class of the binary sensor."""
        return self._sensor_class

    def update(self):
        """Get the latest data and updates the state."""
        ## just to test
        if self._state:
            self._state = False
        else:
            self._state = True
