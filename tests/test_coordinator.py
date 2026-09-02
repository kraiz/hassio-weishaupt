"""Regression tests for optional device group auto-detection in the coordinator."""

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


class SensorDeviceClass:
    """Return the requested enum member name as a string."""

    def __getattr__(self, name: str) -> str:
        return name


class SensorStateClass:
    """Return the requested enum member name as a string."""

    def __getattr__(self, name: str) -> str:
        return name


sensor_component.SensorDeviceClass = SensorDeviceClass()
sensor_component.SensorStateClass = SensorStateClass()
sys.modules.setdefault("homeassistant.components.sensor", sensor_component)

core = types.ModuleType("homeassistant.core")
core.HomeAssistant = object
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

update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")


class DataUpdateCoordinator:
    """Minimal coordinator base stub exposing only what our subclass needs."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, logger, name, update_interval) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None


class UpdateFailed(Exception):
    """Minimal update failure stub."""


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
sensors = load_module(
    "custom_components.weishaupt_wtc.sensors", PACKAGE_ROOT / "sensors.py"
)

api_stub = types.ModuleType("custom_components.weishaupt_wtc.api")


class WeishauptApiClient:
    """Unused by these tests; coordinator only needs the type for annotations."""


class WeishauptApiError(Exception):
    """Stub API error."""


class WeishauptConnectionError(WeishauptApiError):
    """Stub connection error."""


api_stub.WeishauptApiClient = WeishauptApiClient
api_stub.WeishauptApiError = WeishauptApiError
api_stub.WeishauptConnectionError = WeishauptConnectionError
sys.modules["custom_components.weishaupt_wtc.api"] = api_stub

coordinator_module = load_module(
    "custom_components.weishaupt_wtc.coordinator", PACKAGE_ROOT / "coordinator.py"
)


class FakeClient:
    """Records the params passed to read_parameters and returns canned results."""

    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self.calls: list[list[dict]] = []

    async def read_parameters(self, params: list[dict]) -> dict:
        self.calls.append(params)
        return self._responses[len(self.calls) - 1]


class CoordinatorOptionalGroupDetectionTests(unittest.IsolatedAsyncioTestCase):
    """Verify optional device groups are detected once and then not re-probed."""

    async def test_undetected_optional_groups_are_skipped_on_next_poll(self) -> None:
        """Only groups that answered on the first poll stay in later polls."""
        hk_key = sensors.HK_SENSORS[0].key
        sol_key = sensors.SOL_SENSORS[0].key
        hk3_key = sensors.HK3_SENSORS[0].key
        sg_key = sensors.SG_SENSORS[0].key

        # First poll: HK responds, SOL and HK3 do not.
        first_response = {
            sg_key: {"value_int": 0},
            hk_key: {"value_int": 0},
        }
        client = FakeClient(responses=[first_response, {}])
        coordinator = coordinator_module.WeishauptDataUpdateCoordinator(
            hass=SimpleNamespace(), client=client, scan_interval=30
        )

        self.assertIsNone(coordinator.active_groups)
        await coordinator._async_update_data()

        self.assertEqual(coordinator.active_groups, {sensors.WeishauptDeviceGroup.HK})

        first_call_keys = {param["key"] for param in client.calls[0]}
        self.assertIn(sol_key, first_call_keys)
        self.assertIn(hk3_key, first_call_keys)

        await coordinator._async_update_data()

        second_call_keys = {param["key"] for param in client.calls[1]}
        self.assertIn(sg_key, second_call_keys)
        self.assertIn(hk_key, second_call_keys)
        self.assertNotIn(sol_key, second_call_keys)
        self.assertNotIn(hk3_key, second_call_keys)

        # Detection only happens once; it doesn't get re-evaluated afterward.
        self.assertEqual(coordinator.active_groups, {sensors.WeishauptDeviceGroup.HK})


if __name__ == "__main__":
    unittest.main()
