"""
This component provides basic support for Amcrest IP cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.amcrest/
"""
import logging
from datetime import import timedelta

import voluptuous as vol

import homeassistant.loader as loader
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST, CONF_MONITORED_CONDITIONS,
    CONF_USERNAME, CONF_PASSWORD, CONF_PORT,
    STATE_UNKNOWN)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv


REQUIREMENTS = ['amcrest==1.0.0']

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 80

#MONITORED_CONDITIONS = {
#    'motion': ['Motion Detector', 'motion'],
#    'recording': ['Recording on Motion', None],
#}

MONITORED_CONDITIONS = [
    'motion',
    'recording',
]

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

NOTIFICATION_ID = 'amcrest_notification'
NOTIFICATION_TITLE = 'Amcrest Sensor Setup'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required(CONF_MONITORED_CONDITIONS, default=[]):
        #vol.All(cv.ensure_list, [vol.In(MONITORED_CONDITIONS)]),
        vol.All(vol.In(MONITORED_CONDITIONS)),
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
        self._name = MONITORED_CONDITIONS.get(sensor_type)[0]
        self._sensor_type = sensor_type
        self._sensor_class = MONITORED_CONDITIONS.get(sensor_type)[1]
        self._state = STATE_UNKNOWN
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._sensor_class

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return 'mdi:bike'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data and updates the state."""
        if self._sensor_type == 'motion_detector':
            self._state = self._data.camera.is_motion_detector_on()

        elif self._sensor_type == 'recording_on_motion':
            self._state = self._data.camera.is_record_on_motion_detection()
