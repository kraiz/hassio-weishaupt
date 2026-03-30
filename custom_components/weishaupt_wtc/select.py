"""Select platform for Weishaupt WTC integration.

Exposes writable registers with value maps as dropdowns in Home Assistant.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .sensors import ALL_SENSORS, WeishauptSensorDefinition

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Weishaupt Select entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[WeishauptSelectEntity] = []

    # Implement writable select for the specific register key
    for sensor_def in ALL_SENSORS:
        if sensor_def.key == "sg_betriebsart_hk1_vorgabe":
            entities.append(
                WeishauptSelectEntity(
                    coordinator=coordinator, sensor_def=sensor_def, entry=entry
                )
            )

    async_add_entities(entities)


class WeishauptSelectEntity(CoordinatorEntity, SelectEntity):
    """Representation of a writable Weishaupt value-map as a Select."""

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
    def options(self) -> list[str]:
        """Return available options for the select (ordered by raw value)."""
        if not self._sensor_def.value_map:
            return []
        return [
            self._sensor_def.value_map[k]
            for k in sorted(self._sensor_def.value_map.keys())
        ]

    @property
    def current_option(self) -> str | None:
        """Return currently selected option string, or None if unknown."""
        if self.coordinator.data is None:
            return None

        data = self.coordinator.data.get(self._sensor_def.key)
        if not data:
            return None

        raw = data.get("value_int")
        if raw is None:
            return None

        return self._sensor_def.value_map.get(raw)

    async def async_select_option(self, option: Any) -> None:  # type: ignore[override]
        """Write the chosen option back to the device and refresh data."""
        # Find raw integer matching the selected option
        inv_map = {v: k for k, v in (self._sensor_def.value_map or {}).items()}
        if option not in inv_map:
            _LOGGER.error(
                "Invalid option selected for %s: %s", self._sensor_def.key, option
            )
            return

        raw_value = inv_map[option]

        try:
            success = await self.coordinator.client.write_parameter(
                mi=self._sensor_def.mi,
                mx=self._sensor_def.mx,
                ox=self._sensor_def.ox,
                os_val=self._sensor_def.os,
                vs=self._sensor_def.vs,
                value_int=raw_value,
            )
        except Exception as err:  # catch client errors
            _LOGGER.error(
                "Failed to write %s=%s: %s", self._sensor_def.key, option, err
            )
            return

        if success:
            # Refresh coordinator data to reflect the new state
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.debug("Write reported unsuccessful for %s", self._sensor_def.key)
