"""Sensor platform for Weishaupt WTC integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WeishauptDataUpdateCoordinator
from .parsing import (
    build_device_time_iso,
    decode_fault_status,
    decode_fault_status_attributes,
    decode_module_attributes,
    extract_value_segment,
)
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


def _device_identifier(entry_id: str, group: WeishauptDeviceGroup) -> tuple[str, str]:
    """Return the device registry identifier for a Weishaupt group."""
    return (DOMAIN, f"{entry_id}_{group.value}")


def _system_device_identifier(entry_id: str) -> tuple[str, str]:
    """Return the device registry identifier for the system device."""
    return _device_identifier(entry_id, WeishauptDeviceGroup.SG)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Weishaupt WTC sensors from a config entry."""
    coordinator: WeishauptDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={_system_device_identifier(entry.entry_id)},
        name="Weishaupt Systemgerät",
        manufacturer="Weishaupt",
        model=DEVICE_GROUP_MODELS[WeishauptDeviceGroup.SG],
    )

    entities: list[WeishauptSensorEntity] = []
    for sensor_def in ALL_SENSORS:
        # Skip creating a read-only sensor when a writable Select or Button exists
        if sensor_def.key in {"sg_betriebsart_hk1_vorgabe", "sg_warmwasser_push"}:
            continue

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
    """Representation of a Weishaupt WTC sensor."""

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
        device_info = DeviceInfo(
            identifiers={_device_identifier(self._entry.entry_id, group)},
            name=f"Weishaupt {DEVICE_GROUP_NAMES.get(group, group.value)}",
            manufacturer="Weishaupt",
            model=DEVICE_GROUP_MODELS.get(group, "Unknown"),
        )
        if group is not WeishauptDeviceGroup.SG:
            device_info["via_device"] = _system_device_identifier(self._entry.entry_id)

        return device_info

    @property
    def available(self) -> bool:
        """Return True if the sensor data is available."""
        if self._sensor_def.key == "sg_device_time":
            required_keys = [
                "sg_uhrzeit_stunden",
                "sg_uhrzeit_minuten",
                "sg_datum_tag",
                "sg_datum_monat",
                "sg_datum_jahr",
            ]
            return (
                super().available
                and self.coordinator.data is not None
                and all(key in self.coordinator.data for key in required_keys)
            )

        data_key = self._sensor_def.source_key or self._sensor_def.key
        return (
            super().available
            and self.coordinator.data is not None
            and data_key in self.coordinator.data
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

        sensor_def = self._sensor_def

        # Special handling for the consolidated device time sensor
        if sensor_def.key == "sg_device_time":
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

            return build_device_time_iso(vals)

        data_key = sensor_def.source_key or sensor_def.key
        data = self.coordinator.data.get(data_key)
        if data is None:
            return None

        raw_value = data["value_int"]
        value_size = sensor_def.byte_length or sensor_def.vs

        if sensor_def.source_key is not None:
            extracted = extract_value_segment(
                data.get("value_hex", ""),
                sensor_def.byte_offset,
                value_size,
            )
            if extracted is None:
                return None
            _, raw_value = extracted

        # Handle common sentinel values that indicate 'not available'
        # 16-bit: 0x8000 or 0xFFFF, 32-bit: 0x80000000 or 0xFFFFFFFF
        if value_size == 2 and raw_value in (0x8000, 0xFFFF):
            return None
        if value_size == 4 and raw_value in (0x80000000, 0xFFFFFFFF):
            return None

        # Handle signed values
        if sensor_def.signed and value_size == 2:
            if raw_value > 0x7FFF:
                raw_value -= 0x10000
        elif sensor_def.signed and value_size == 4:
            if raw_value > 0x7FFFFFFF:
                raw_value -= 0x100000000

        if sensor_def.key == "sg_fehler_warnung_status":
            return decode_fault_status(raw_value)

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

        if self._sensor_def.source_key is not None:
            attrs["source_sensor"] = self._sensor_def.source_key

        if self.coordinator.data:
            data_key = self._sensor_def.source_key or self._sensor_def.key
            data = self.coordinator.data.get(data_key)
            if data:
                raw_value_hex = data.get("value_hex", "")
                raw_value_int = data.get("value_int", 0)

                if self._sensor_def.source_key is not None:
                    extracted = extract_value_segment(
                        raw_value_hex,
                        self._sensor_def.byte_offset,
                        self._sensor_def.byte_length or self._sensor_def.vs,
                    )
                    if extracted is not None:
                        raw_value_hex, raw_value_int = extracted

                attrs["raw_value_hex"] = raw_value_hex
                attrs["raw_value_int"] = raw_value_int

                if self._sensor_def.key == "sg_fehler_warnung_status":
                    attrs.update(decode_fault_status_attributes(raw_value_int))
                elif self._sensor_def.key == "sg_fehler_modul":
                    attrs.update(decode_module_attributes(raw_value_int))
                elif self._sensor_def.key == "sg_canopen_fehlerblock":
                    status = extract_value_segment(raw_value_hex, 2, 2)
                    number = extract_value_segment(raw_value_hex, 4, 2)
                    module = extract_value_segment(raw_value_hex, 6, 2)
                    if status is not None:
                        attrs["fault_status"] = decode_fault_status(status[1])
                        attrs.update(decode_fault_status_attributes(status[1]))
                    if number is not None:
                        attrs["fault_number"] = number[1]
                    if module is not None:
                        attrs.update(decode_module_attributes(module[1]))

        return attrs
