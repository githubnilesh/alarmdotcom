"""Alarmdotcom implementation of an HA cover (garage door)."""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from homeassistant import core
from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback, DiscoveryInfoType
from pyalarmdotcomajax.devices.garage_door import GarageDoor as libGarageDoor
from pyalarmdotcomajax.devices.gate import Gate as libGate
from pyalarmdotcomajax.exceptions import NotAuthorized

from .base_device import HardwareBaseDevice
from .const import DATA_CONTROLLER, DOMAIN
from .controller import AlarmIntegrationController

log = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the cover platform."""

    controller: AlarmIntegrationController = hass.data[DOMAIN][config_entry.entry_id][DATA_CONTROLLER]

    async_add_entities(
        Cover(
            controller=controller,
            device=device,
        )
        for device in list(controller.api.devices.garage_doors.values())
        + list(controller.api.devices.gates.values())
    )


class Cover(HardwareBaseDevice, CoverEntity):  # type: ignore
    """Integration Cover Entity."""

    _device_type_name: str = "Garage Door"
    _device: libGarageDoor | libGate

    def __init__(
        self,
        controller: AlarmIntegrationController,
        device: libGarageDoor | libGate,
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(controller, device, device.partition_id)

        self._attr_device_class: CoverDeviceClass = (
            CoverDeviceClass.GARAGE if isinstance(device, libGarageDoor) else CoverDeviceClass.GATE
        )

        self._attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    @callback
    def _update_device_data(self) -> None:
        """Update the entity when coordinator is updated."""

        self._attr_is_closed = self._determine_is_closed(self._device.state)
        self._attr_is_closing = False
        self._attr_is_opening = False

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""

        self._attr_is_opening = True

        try:
            await self._device.async_open()
        except NotAuthorized:
            self._show_permission_error("open")

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""

        self._attr_is_closing = True

        try:
            await self._device.async_close()
        except NotAuthorized:
            self._show_permission_error("close")

    #
    # Helpers
    #

    def _determine_is_closed(self, state: Enum | None) -> bool | None:
        """Return if the cover is closed or not."""

        if not self._device.malfunction:
            if state in [libGarageDoor.DeviceState.OPEN, libGate.DeviceState.OPEN]:
                return False

            if state in [libGarageDoor.DeviceState.CLOSED, libGate.DeviceState.CLOSED]:
                return True

            log.exception(
                "Cannot determine cover state. Found raw state of %s.",
                state,
            )

        return None
