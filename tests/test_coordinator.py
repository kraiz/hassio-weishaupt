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
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
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


sensor_component.__dict__.update(
    SensorDeviceClass=SensorDeviceClass(), SensorStateClass=SensorStateClass()
)
sys.modules.setdefault("homeassistant.components.sensor", sensor_component)

core = types.ModuleType("homeassistant.core")
core.__dict__.update(HomeAssistant=object)
sys.modules.setdefault("homeassistant.core", core)

const = types.ModuleType("homeassistant.const")
const.__dict__.update(
    PERCENTAGE="%",
    UnitOfEnergy=SimpleNamespace(KILO_WATT_HOUR="kWh"),
    UnitOfPower=SimpleNamespace(KILO_WATT="kW"),
    UnitOfPressure=SimpleNamespace(BAR="bar"),
    UnitOfTemperature=SimpleNamespace(CELSIUS="°C"),
    UnitOfTime=SimpleNamespace(HOURS="h"),
)
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


update_coordinator.__dict__.update(
    DataUpdateCoordinator=DataUpdateCoordinator, UpdateFailed=UpdateFailed
)
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


api_stub.__dict__.update(
    WeishauptApiClient=WeishauptApiClient,
    WeishauptApiError=WeishauptApiError,
    WeishauptConnectionError=WeishauptConnectionError,
)
sys.modules["custom_components.weishaupt_wtc.api"] = api_stub

coordinator_module = load_module(
    "custom_components.weishaupt_wtc.coordinator", PACKAGE_ROOT / "coordinator.py"
)


class FakeClient:
    """Records the params passed to the read and returns canned (results, answered)."""

    def __init__(self, responses: list[tuple[dict, set]]) -> None:
        self._responses = responses
        self.calls: list[list[dict]] = []

    async def read_parameters_with_status(
        self, params: list[dict], adapt_batch_size: bool = True
    ) -> tuple[dict, set]:
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

        # First poll: HK responds, SOL and HK3 do not (CMD_ERROR, so they are answered).
        first_response = {
            sg_key: {"value_int": 0},
            hk_key: {"value_int": 0},
        }
        answered = {sg_key, hk_key, sol_key, hk3_key}
        client = FakeClient(responses=[(first_response, answered), ({}, set())])
        coordinator = coordinator_module.WeishauptDataUpdateCoordinator(
            hass=SimpleNamespace(), client=client, scan_interval=30
        )

        self.assertIsNone(coordinator.active_groups)
        await coordinator._async_update_data()

        self.assertEqual(coordinator.active_groups, {sensors.WeishauptDeviceGroup.HK})

        first_call_keys = {param["key"] for param in client.calls[0]}
        first_optional_keys = first_call_keys & {hk_key, sol_key, hk3_key}
        self.assertEqual(first_optional_keys, {hk_key, sol_key, hk3_key})
        self.assertEqual(
            sum(
                param["key"] in {hk_key, sol_key, hk3_key}
                for param in client.calls[0]
            ),
            3,
        )

        await coordinator._async_update_data()

        second_call_keys = {param["key"] for param in client.calls[1]}
        self.assertIn(sg_key, second_call_keys)
        self.assertIn(hk_key, second_call_keys)
        self.assertNotIn(sol_key, second_call_keys)
        self.assertNotIn(hk3_key, second_call_keys)

        # Detection only happens once; it doesn't get re-evaluated afterward.
        self.assertEqual(coordinator.active_groups, {sensors.WeishauptDeviceGroup.HK})

    async def test_complete_detection_is_handed_to_persist_callback(self) -> None:
        """Every probe answered (value or CMD_ERROR) means the result can be stored."""
        hk_key = sensors.HK_SENSORS[0].key
        sol_key = sensors.SOL_SENSORS[0].key
        hk3_key = sensors.HK3_SENSORS[0].key
        sg_key = sensors.SG_SENSORS[0].key
        client = FakeClient(
            responses=[
                (
                    {sg_key: {"value_int": 0}, hk_key: {"value_int": 0}},
                    {sg_key, hk_key, sol_key, hk3_key},
                )
            ]
        )
        stored: list[set] = []
        coordinator = coordinator_module.WeishauptDataUpdateCoordinator(
            hass=SimpleNamespace(),
            client=client,
            scan_interval=30,
            on_groups_detected=lambda groups: stored.append(set(groups)),
        )

        await coordinator._async_update_data()

        self.assertEqual(stored, [{sensors.WeishauptDeviceGroup.HK}])

    async def test_unanswered_probe_is_not_stored(self) -> None:
        """A probe without any reply says nothing about its module, so it is not persisted."""
        hk_key = sensors.HK_SENSORS[0].key
        sg_key = sensors.SG_SENSORS[0].key
        client = FakeClient(
            responses=[
                ({sg_key: {"value_int": 0}, hk_key: {"value_int": 0}}, {sg_key, hk_key})
            ]
        )
        stored: list[set] = []
        coordinator = coordinator_module.WeishauptDataUpdateCoordinator(
            hass=SimpleNamespace(),
            client=client,
            scan_interval=30,
            on_groups_detected=lambda groups: stored.append(set(groups)),
        )

        await coordinator._async_update_data()

        self.assertEqual(coordinator.active_groups, {sensors.WeishauptDeviceGroup.HK})
        self.assertEqual(stored, [])

    async def test_stored_groups_are_polled_without_probes(self) -> None:
        """A stored detection result skips probing: only stored optional groups are read."""
        hk_key = sensors.HK_SENSORS[0].key
        sol_key = sensors.SOL_SENSORS[0].key
        hk3_key = sensors.HK3_SENSORS[0].key
        sg_key = sensors.SG_SENSORS[0].key
        client = FakeClient(
            responses=[
                ({sg_key: {"value_int": 0}, hk_key: {"value_int": 0}}, {sg_key, hk_key})
            ]
        )
        stored: list[set] = []
        coordinator = coordinator_module.WeishauptDataUpdateCoordinator(
            hass=SimpleNamespace(),
            client=client,
            scan_interval=30,
            active_groups={sensors.WeishauptDeviceGroup.HK},
            on_groups_detected=lambda groups: stored.append(set(groups)),
        )

        await coordinator._async_update_data()

        keys = {param["key"] for param in client.calls[0]}
        self.assertIn(hk_key, keys)
        self.assertFalse(keys & {sol_key, hk3_key})
        self.assertEqual(stored, [])


class CoordinatorPollOverlapTests(unittest.IsolatedAsyncioTestCase):
    """A scheduled poll must not start while the previous one is still running."""

    async def test_poll_is_skipped_while_previous_poll_runs(self) -> None:
        client = FakeClient(responses=[({}, set())])
        coordinator = coordinator_module.WeishauptDataUpdateCoordinator(
            hass=SimpleNamespace(), client=client, scan_interval=30,
            active_groups=set(),
        )
        coordinator.data = {"previous": 1}
        coordinator._poll_running = True

        result = await coordinator._async_update_data()

        self.assertEqual(result, {"previous": 1})
        self.assertEqual(client.calls, [])

    async def test_running_flag_is_cleared_after_poll(self) -> None:
        client = FakeClient(responses=[({}, set())])
        coordinator = coordinator_module.WeishauptDataUpdateCoordinator(
            hass=SimpleNamespace(), client=client, scan_interval=30,
            active_groups=set(),
        )

        await coordinator._async_update_data()

        self.assertFalse(coordinator._poll_running)
        self.assertEqual(len(client.calls), 1)


if __name__ == "__main__":
    unittest.main()
