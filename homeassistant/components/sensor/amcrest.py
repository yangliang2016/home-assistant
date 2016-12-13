"""
This component provides basic support for Amcrest IP cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.amcrest/
"""
from datetime import timedelta
import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST, CONF_MONITORED_CONDITIONS,
    CONF_USERNAME, CONF_PASSWORD, CONF_PORT,
    STATE_UNKNOWN)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.loader as loader

REQUIREMENTS = ['amcrest==1.0.0']

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

NOTIFICATION_ID = 'amcrest_notification'
NOTIFICATION_TITLE = 'Amcrest Sensor Setup'

DEFAULT_PORT = 80

# Sensor types are defined like: Name, units
SENSOR_TYPES = {
    'motion_detector': ['Motion Detector', 'motion'],
    'recording_on_motion': ['Recording on Motion', None],
    'sdcard_used_bytes': ['SD card Used', 'GB'],
    'sdcard_total_bytes': ['SD card Total', 'GB'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up a sensor for an Amcrest IP Camera."""
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


class AmcrestSensor(Entity):
    """A sensor implementation for Amcrest IP camera."""

    def __init__(self, data, sensor_type):
        """Initialize a sensor for Amcrest camera."""
        super(AmcrestSensor, self).__init__()
        self._data = data
        self._sensor_type = sensor_type
        self._name = SENSOR_TYPES.get(self._sensor_type)[0]
        self._state = STATE_UNKNOWN
        self._counter = 1
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return 'mdi:taxi'

    @property
    def entity_picture(self):
        """Icon to use in the frontend, if any."""
        return

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return SENSOR_TYPES.get(self._sensor_type)[1]


    def update(self):
        """Get the latest data and updates the state."""
        if self._sensor_type == 'motion_detector':
            self._state = self._data.camera.is_motion_detector_on()

        elif self._sensor_type == 'recording_on_motion':
            self._state = self._data.camera.is_record_on_motion_detection()

        elif self._sensor_type == 'sdcard_used_bytes':
            self._state = 16

        elif self._sensor_type == 'sdcard_total_bytes':
            self._counter += 1
            self._state = 64 + self._counter
