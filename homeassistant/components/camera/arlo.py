"""
This component provides basic support for Netgear Arlo IP cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.arlo/
"""
import logging
from datetime import timedelta
import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.components.arlo import (
    DEFAULT_BRAND, DEFAULT_ENTITY_NAMESPACE)

from homeassistant.components.camera import (Camera, PLATFORM_SCHEMA)
from homeassistant.const import CONF_ENTITY_NAMESPACE

DEPENDENCIES = ['arlo']

_LOGGER = logging.getLogger(__name__)

CONTENT_TYPE_HEADER = 'Content-Type'
TIMEOUT = 5

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=90)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ENTITY_NAMESPACE, default=DEFAULT_ENTITY_NAMESPACE):
        cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up an Arlo IP Camera."""
    arlo = hass.data.get('arlo')

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
        return self._camera.last_image

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
