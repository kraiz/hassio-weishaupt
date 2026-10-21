"""Switch platform for Weishaupt WTC integration.

Exposes the Warmwasser on/off object (MI 03 / OX 0x2520) as a Home Assistant switch.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .sensor import DEVICE_GROUP_MODELS, DEVICE_GROUP_NAMES, _device_identifier, _is_group_active, _via_device_id
from .sensors import ALL_SENSORS, WeishauptDeviceGroup, WeishauptSensorDefinition

_LOGGER = logging.getLogger(__name__)

SWITCH_KEY = "sg_betriebsart_warmwasser"
WW_EIN = 1  # Betriebsart Warmwasser values: 1 = Ein, 2 = Aus
WW_AUS = 2


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Weishaupt Switch entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[WeishauptWarmwasserSwitch] = []
    for sensor_def in ALL_SENSORS:
        if sensor_def.key == SWITCH_KEY and _is_group_active(
            coordinator, sensor_def.group
        ):
            entities.append(
                WeishauptWarmwasserSwitch(
                    coordinator=coordinator, sensor_def=sensor_def, entry=entry
                )
            )

    async_add_entities(entities)


class WeishauptWarmwasserSwitch(CoordinatorEntity, SwitchEntity):
    """Warmwasser on/off (Betriebsart Ein/Aus) as a switch."""

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
        self._attr_translation_key = sensor_def.key
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
            via_device_id = _via_device_id(self.hass, self._entry.entry_id)
            if via_device_id is not None:
                info["via_device_id"] = via_device_id
        return info

    @property
    def is_on(self) -> bool | None:
        """Return True for Ein, False for Aus, None for any other value."""
        data = (self.coordinator.data or {}).get(self._sensor_def.key)
        if not data:
            return None
        return {WW_EIN: True, WW_AUS: False}.get(data["value_int"])

    async def _write_betriebsart(self, value: int) -> None:
        try:
            await self.coordinator.client.write_parameter(
                mi=self._sensor_def.mi,
                mx=self._sensor_def.mx,
                ox=self._sensor_def.ox,
                os_val=self._sensor_def.os,
                vs=self._sensor_def.vs,
                value_int=value,
            )
        except Exception as err:  # catch client errors
            _LOGGER.error("Failed to write %s=%s: %s", self._sensor_def.key, value, err)
        # Read back even after a failed write: a write can apply despite an empty reply.
        # shortcut: no 1-write-per-minute throttle (jvejmelka firmware has one), add it if the device rejects rapid toggles
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn Warmwasser on (Betriebsart Ein)."""
        await self._write_betriebsart(WW_EIN)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn Warmwasser off (Betriebsart Aus)."""
        await self._write_betriebsart(WW_AUS)
