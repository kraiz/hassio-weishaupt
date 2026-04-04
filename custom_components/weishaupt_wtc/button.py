"""Button platform for Weishaupt WTC integration.

Exposes one-shot writable registers as press buttons in Home Assistant.
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .sensor import DEVICE_GROUP_MODELS, DEVICE_GROUP_NAMES, _device_identifier
from .sensors import ALL_SENSORS, WeishauptDeviceGroup, WeishauptSensorDefinition

_LOGGER = logging.getLogger(__name__)

# Keys that are exposed as buttons rather than sensors
BUTTON_KEYS = {"sg_warmwasser_push"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Weishaupt Button entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[WeishauptButtonEntity] = []
    for sensor_def in ALL_SENSORS:
        if sensor_def.key in BUTTON_KEYS:
            entities.append(
                WeishauptButtonEntity(
                    coordinator=coordinator, sensor_def=sensor_def, entry=entry
                )
            )

    async_add_entities(entities)


class WeishauptButtonEntity(CoordinatorEntity, ButtonEntity):
    """Representation of a one-shot Weishaupt writable register as a Button."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        sensor_def: WeishauptSensorDefinition,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._sensor_def = sensor_def
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_{sensor_def.key}"
        self._attr_name = sensor_def.name
        self._attr_icon = sensor_def.icon

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info so the entity is attached to the correct device."""
        group = self._sensor_def.group
        info = DeviceInfo(
            identifiers={_device_identifier(self._entry.entry_id, group)},
            name=f"Weishaupt {DEVICE_GROUP_NAMES.get(group, group.value)}",
            manufacturer="Weishaupt",
            model=DEVICE_GROUP_MODELS.get(group, "Unknown"),
        )
        if group is not WeishauptDeviceGroup.SG:
            info["via_device"] = _device_identifier(
                self._entry.entry_id, WeishauptDeviceGroup.SG
            )
        return info

    async def async_press(self) -> None:
        """Trigger the warm-water push by writing 1 to the register."""
        try:
            success = await self.coordinator.client.write_parameter(
                mi=self._sensor_def.mi,
                mx=self._sensor_def.mx,
                ox=self._sensor_def.ox,
                os_val=self._sensor_def.os,
                vs=self._sensor_def.vs,
                value_int=1,
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to trigger %s: %s", self._sensor_def.key, err
            )
            return

        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.debug("Write reported unsuccessful for %s", self._sensor_def.key)
