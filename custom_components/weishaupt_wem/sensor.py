"""Sensor platform for Weishaupt WEM integration."""

from __future__ import annotations

import logging
from typing import Any
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WeishauptDataUpdateCoordinator
from .sensors import ALL_SENSORS, WeishauptDeviceGroup, WeishauptSensorDefinition

_LOGGER = logging.getLogger(__name__)

DEVICE_GROUP_NAMES = {
    WeishauptDeviceGroup.SG: "Systemgerät",
    WeishauptDeviceGroup.WTC: "WTC Kessel",
    WeishauptDeviceGroup.HK: "Heizkreis",
    WeishauptDeviceGroup.WW: "Warmwasser",
    WeishauptDeviceGroup.SOL: "Solar",
    WeishauptDeviceGroup.KA: "Kaskade",
    WeishauptDeviceGroup.RF: "Raumfühler",
}

DEVICE_GROUP_MODELS = {
    WeishauptDeviceGroup.SG: "WEM-Systemgerät",
    WeishauptDeviceGroup.WTC: "WTC Brennwertgerät",
    WeishauptDeviceGroup.HK: "EM-HK Heizkreis",
    WeishauptDeviceGroup.WW: "EM-WW Warmwasser",
    WeishauptDeviceGroup.SOL: "EM-Sol Solar",
    WeishauptDeviceGroup.KA: "EM-KA Kaskade",
    WeishauptDeviceGroup.RF: "RF Raumfühler",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Weishaupt WEM sensors from a config entry."""
    coordinator: WeishauptDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[WeishauptSensorEntity] = []
    for sensor_def in ALL_SENSORS:
        entities.append(
            WeishauptSensorEntity(
                coordinator=coordinator,
                sensor_def=sensor_def,
                entry=entry,
            )
        )

    async_add_entities(entities)


class WeishauptSensorEntity(
    CoordinatorEntity[WeishauptDataUpdateCoordinator], SensorEntity
):
    """Representation of a Weishaupt WEM sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WeishauptDataUpdateCoordinator,
        sensor_def: WeishauptSensorDefinition,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_def = sensor_def
        self._entry = entry

        # Entity attributes
        self._attr_unique_id = f"{entry.entry_id}_{sensor_def.key}"
        self._attr_name = sensor_def.name
        self._attr_native_unit_of_measurement = sensor_def.unit
        self._attr_device_class = sensor_def.device_class
        self._attr_state_class = sensor_def.state_class
        self._attr_icon = sensor_def.icon

        if sensor_def.entity_category == "diagnostic":
            from homeassistant.helpers.entity import EntityCategory

            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            # Disable diagnostic sensors by default in the entity registry
            self._attr_entity_registry_enabled_default = False
        elif sensor_def.entity_category == "config":
            from homeassistant.helpers.entity import EntityCategory

            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this sensor."""
        group = self._sensor_def.group
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry.entry_id}_{group.value}")},
            name=f"Weishaupt {DEVICE_GROUP_NAMES.get(group, group.value)}",
            manufacturer="Weishaupt",
            model=DEVICE_GROUP_MODELS.get(group, "Unknown"),
            via_device=(DOMAIN, self._entry.entry_id),
        )

    @property
    def available(self) -> bool:
        """Return True if the sensor data is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self._sensor_def.key in self.coordinator.data
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        # Special handling for the consolidated device time sensor
        if self._sensor_def.key == "sg_device_time":
            required_keys = [
                "sg_uhrzeit_stunden",
                "sg_uhrzeit_minuten",
                "sg_datum_tag",
                "sg_datum_monat",
                "sg_datum_jahr",
            ]
            vals: dict[str, int] = {}
            for k in required_keys:
                d = self.coordinator.data.get(k)
                if not d:
                    return None
                vals[k] = d.get("value_int", 0)

            # Year register is typically two-digit; normalize to full year
            year = vals.get("sg_datum_jahr", 0)
            if year < 100:
                year += 2000

            try:
                dt = datetime(
                    year,
                    vals.get("sg_datum_monat", 1),
                    vals.get("sg_datum_tag", 1),
                    vals.get("sg_uhrzeit_stunden", 0),
                    vals.get("sg_uhrzeit_minuten", 0),
                )
            except Exception:
                return None

            # Return ISO 8601 string (Home Assistant expects timestamp strings)
            return dt.isoformat()

        data = self.coordinator.data.get(self._sensor_def.key)
        if data is None:
            return None

        raw_value = data["value_int"]

        # Handle common sentinel values that indicate 'not available'
        # 16-bit: 0x8000 or 0xFFFF, 32-bit: 0x80000000 or 0xFFFFFFFF
        if sensor_def.vs == 2 and raw_value in (0x8000, 0xFFFF):
            return None
        if sensor_def.vs == 4 and raw_value in (0x80000000, 0xFFFFFFFF):
            return None
        sensor_def = self._sensor_def

        # Handle signed values
        if sensor_def.signed and sensor_def.vs == 2:
            if raw_value > 0x7FFF:
                raw_value -= 0x10000
        elif sensor_def.signed and sensor_def.vs == 4:
            if raw_value > 0x7FFFFFFF:
                raw_value -= 0x100000000

        # If there's a value map, return the mapped string
        if sensor_def.value_map is not None:
            return sensor_def.value_map.get(raw_value, f"Unknown ({raw_value})")

        # Apply scale factor
        if sensor_def.scale != 1.0:
            return round(raw_value * sensor_def.scale, 2)

        return raw_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "modbus_register": self._sensor_def.modbus_reg,
            "device_group": self._sensor_def.group.value,
        }

        if self.coordinator.data and self._sensor_def.key in self.coordinator.data:
            data = self.coordinator.data[self._sensor_def.key]
            attrs["raw_value_hex"] = data.get("value_hex", "")
            attrs["raw_value_int"] = data.get("value_int", 0)

        return attrs
