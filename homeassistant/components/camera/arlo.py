"""
This component provides basic support for Netgear Arlo IP cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.arlo/
"""
import logging
import voluptuous as vol

import homeassistant.loader as loader
from homeassistant.components.camera import (Camera, PLATFORM_SCHEMA)
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv

REQUIREMENTS = ['pyarlo==0.0.1']

_LOGGER = logging.getLogger(__name__)

DEFAULT_ENTITY_NAMESPACE = 'arlo'
DEFAULT_BRAND = 'Netgear Arlo'

NOTIFICATION_ID = 'arlo_notification'
NOTIFICATION_TITLE = 'Arlo Camera Setup'

CONTENT_TYPE_HEADER = 'Content-Type'
TIMEOUT = 5

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up an Arlo IP Camera."""
    from pyarlo import PyArlo
    arlo = PyArlo(config.get(CONF_USERNAME), config.get(CONF_PASSWORD))

    persistent_notification = loader.get_component('persistent_notification')
    try:
        arlo.authenticated
    # pylint: disable=broad-except
    except Exception as ex:
        _LOGGER.error("Unable to connect to Arlo camera: %s", str(ex))
        persistent_notification.create(
            hass, 'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)
        return False

    cameras = []
    for camera in arlo.cameras:
        cameras.append(ArloCam(hass, camera))

    add_devices(cameras, True)
    return True


class ArloCam(Camera):
    """An implementation of a Netgear Arlo IP camera."""

    def __init__(self, hass, camera):
        """Initialize an Arlo camera."""
        super(ArloCam, self).__init__()
        self._camera = camera
        self._hass = hass
        self._name = self._camera.name

    def camera_image(self):
        """Return a still image reponse from the camera."""
        # Send the request to snap a picture and return raw jpg data
        _LOGGER.debug('Polling data from %s', self._name)
        try:
            return self._camera.download_snapshot()
        except:         # pylint: disable=bare-except
            return None

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    @property
    def model(self):
        """Camera model."""
        return self._camera.model_id

    @property
    def brand(self):
        """Camera brand."""
        return DEFAULT_BRAND
