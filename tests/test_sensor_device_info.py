"""Regression tests for Weishaupt device registry metadata."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import types
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "weishaupt_wtc"


def load_module(module_name: str, file_path: Path):
    """Load a module from file while preserving package-relative imports."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


homeassistant_pkg = types.ModuleType("homeassistant")
homeassistant_pkg.__path__ = []
sys.modules.setdefault("homeassistant", homeassistant_pkg)

components_pkg = types.ModuleType("homeassistant.components")
components_pkg.__path__ = []
sys.modules.setdefault("homeassistant.components", components_pkg)

sensor_component = types.ModuleType("homeassistant.components.sensor")


class SensorEntity:
    """Minimal sensor entity stub."""


class SensorDeviceClass:
    """Return the requested enum member name as a string."""

    def __getattr__(self, name: str) -> str:
        return name


class SensorStateClass:
    """Return the requested enum member name as a string."""

    def __getattr__(self, name: str) -> str:
        return name


sensor_component.SensorEntity = SensorEntity
sensor_component.SensorDeviceClass = SensorDeviceClass()
sensor_component.SensorStateClass = SensorStateClass()
sys.modules.setdefault("homeassistant.components.sensor", sensor_component)

config_entries = types.ModuleType("homeassistant.config_entries")


class ConfigEntry:
    """Minimal config entry stub."""


config_entries.ConfigEntry = ConfigEntry
sys.modules.setdefault("homeassistant.config_entries", config_entries)

core = types.ModuleType("homeassistant.core")
core.HomeAssistant = object
core.callback = lambda func: func
sys.modules.setdefault("homeassistant.core", core)

const = types.ModuleType("homeassistant.const")
const.PERCENTAGE = "%"
const.UnitOfEnergy = SimpleNamespace(KILO_WATT_HOUR="kWh")
const.UnitOfPower = SimpleNamespace(KILO_WATT="kW")
const.UnitOfPressure = SimpleNamespace(BAR="bar")
const.UnitOfTemperature = SimpleNamespace(CELSIUS="°C")
const.UnitOfTime = SimpleNamespace(HOURS="h")
sys.modules.setdefault("homeassistant.const", const)

helpers_pkg = types.ModuleType("homeassistant.helpers")
helpers_pkg.__path__ = []
sys.modules.setdefault("homeassistant.helpers", helpers_pkg)

device_registry_module = types.ModuleType("homeassistant.helpers.device_registry")
device_registry_module.DeviceInfo = dict
device_registry_module.async_get = lambda hass: None
helpers_pkg.device_registry = device_registry_module
sys.modules["homeassistant.helpers.device_registry"] = device_registry_module

entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
entity_platform.AddEntitiesCallback = object
sys.modules.setdefault("homeassistant.helpers.entity_platform", entity_platform)

update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")


class CoordinatorEntity:
    """Minimal coordinator entity stub."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator) -> None:
        self.coordinator = coordinator

    @property
    def available(self) -> bool:
        return True


class DataUpdateCoordinator:
    """Minimal data update coordinator stub."""

    def __class_getitem__(cls, item):
        return cls


class UpdateFailed(Exception):
    """Minimal update failure stub."""


update_coordinator.CoordinatorEntity = CoordinatorEntity
update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = UpdateFailed
sys.modules.setdefault("homeassistant.helpers.update_coordinator", update_coordinator)

custom_components_pkg = types.ModuleType("custom_components")
custom_components_pkg.__path__ = [str(REPO_ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components_pkg)

integration_pkg = types.ModuleType("custom_components.weishaupt_wtc")
integration_pkg.__path__ = [str(PACKAGE_ROOT)]
sys.modules.setdefault("custom_components.weishaupt_wtc", integration_pkg)

load_module("custom_components.weishaupt_wtc.const", PACKAGE_ROOT / "const.py")
load_module("custom_components.weishaupt_wtc.parsing", PACKAGE_ROOT / "parsing.py")
sensors = load_module(
    "custom_components.weishaupt_wtc.sensors", PACKAGE_ROOT / "sensors.py"
)

coordinator_module = types.ModuleType("custom_components.weishaupt_wtc.coordinator")


class WeishauptDataUpdateCoordinator:
    """Minimal coordinator type stub used by the sensor module."""


coordinator_module.WeishauptDataUpdateCoordinator = WeishauptDataUpdateCoordinator
sys.modules["custom_components.weishaupt_wtc.coordinator"] = coordinator_module

sensor = load_module(
    "custom_components.weishaupt_wtc.sensor", PACKAGE_ROOT / "sensor.py"
)


class SensorDeviceInfoTests(unittest.TestCase):
    """Test device registry metadata for sensor entities."""

    def test_system_device_has_no_via_device(self) -> None:
        """The SG device is the root of the device tree."""
        entity = sensor.WeishauptSensorEntity(
            coordinator=SimpleNamespace(data={}),
            sensor_def=sensors.SG_SENSORS[0],
            entry=SimpleNamespace(entry_id="entry-123"),
        )

        self.assertEqual(
            entity.device_info["identifiers"],
            {("weishaupt_wtc", "entry-123_sg")},
        )
        self.assertNotIn("via_device", entity.device_info)

    def test_child_device_points_to_system_device(self) -> None:
        """Non-SG groups should reference the SG device as their parent."""
        entity = sensor.WeishauptSensorEntity(
            coordinator=SimpleNamespace(data={}),
            sensor_def=sensors.WTC_SENSORS[0],
            entry=SimpleNamespace(entry_id="entry-123"),
        )

        self.assertEqual(
            entity.device_info["identifiers"],
            {("weishaupt_wtc", "entry-123_wtc")},
        )
        self.assertEqual(
            entity.device_info["via_device"],
            ("weishaupt_wtc", "entry-123_sg"),
        )


if __name__ == "__main__":
    unittest.main()
