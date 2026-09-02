"""Unit tests for Weishaupt API client edge cases."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import time
import types
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "weishaupt_wtc"


aiohttp_stub = types.ModuleType("aiohttp")


class ClientConnectorError(Exception):
    """Minimal aiohttp exception stub used by the API client."""


class BasicAuth:
    """Minimal aiohttp auth stub."""

    def __init__(self, login: str, password: str) -> None:
        self.login = login
        self.password = password


class ClientTimeout:
    """Minimal aiohttp timeout stub."""

    def __init__(self, total: int | None = None) -> None:
        self.total = total


class ClientSession:
    """Minimal aiohttp session stub for type compatibility."""

    closed = False

    async def close(self) -> None:
        """Provide the interface used by the client close method."""


aiohttp_stub.ClientConnectorError = ClientConnectorError
aiohttp_stub.BasicAuth = BasicAuth
aiohttp_stub.ClientTimeout = ClientTimeout
aiohttp_stub.ClientSession = ClientSession
sys.modules.setdefault("aiohttp", aiohttp_stub)


def load_module(module_name: str, file_path: Path):
    """Load a module from file while preserving package-relative imports."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


custom_components_pkg = types.ModuleType("custom_components")
custom_components_pkg.__path__ = [str(REPO_ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components_pkg)

integration_pkg = types.ModuleType("custom_components.weishaupt_wtc")
integration_pkg.__path__ = [str(PACKAGE_ROOT)]
sys.modules.setdefault("custom_components.weishaupt_wtc", integration_pkg)

load_module("custom_components.weishaupt_wtc.const", PACKAGE_ROOT / "const.py")
api = load_module("custom_components.weishaupt_wtc.api", PACKAGE_ROOT / "api.py")


class EmptyResponseClient(api.WeishauptApiClient):
    """API client test double that always returns an empty device response."""

    async def _post(self, payload: dict) -> dict | None:
        """Return the empty response that triggered issue #2."""
        return None


class ApiClientTests(unittest.IsolatedAsyncioTestCase):
    """Test API client behavior for empty device responses."""

    async def test_test_connection_returns_false_for_empty_response(self) -> None:
        """Connection test should not crash on an empty response."""
        client = EmptyResponseClient("wem-sg", "admin", "Admin123")

        self.assertFalse(await client.test_connection())

    async def test_read_parameters_skips_empty_response(self) -> None:
        """Batch reads should warn and skip empty responses instead of failing."""
        client = EmptyResponseClient("wem-sg", "admin", "Admin123")
        params = [
            {
                "key": "sg_betriebsart_hk1",
                "mi": 0x02,
                "mx": 0x00,
                "ox": 0x2533,
                "os": 0x02,
                "vs": 0x01,
            }
        ]

        with self.assertLogs(
            "custom_components.weishaupt_wtc.api", level="WARNING"
        ) as logs:
            result = await client.read_parameters(params)

        self.assertEqual(result, {})
        self.assertTrue(
            any("Empty response from device" in entry for entry in logs.output)
        )


class BatchCountingClient(api.WeishauptApiClient):
    """Test double that records the batch size of each request."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.batch_sizes: list[int] = []

    async def _post_once(self, payload: dict) -> dict | None:
        self.batch_sizes.append(payload["CAPI"]["NN"])
        return None


class ApiClientBatchingTests(unittest.IsolatedAsyncioTestCase):
    """Test that reads are split into batches of MAX_PARAMS_PER_REQUEST."""

    async def test_read_parameters_splits_into_batches_of_six(self) -> None:
        """Larger batches have been observed to cause CMD_ERROR on real hardware."""
        client = BatchCountingClient(
            "wem-sg", "admin", "Admin123", min_request_interval=0
        )
        params = [
            {"key": f"p{i}", "mi": 0, "mx": 0, "ox": 0, "os": 0, "vs": 1}
            for i in range(14)
        ]

        await client.read_parameters(params)

        self.assertEqual(client.batch_sizes, [6, 6, 2])


class ThrottlingClient(api.WeishauptApiClient):
    """Test double that returns an empty CAPI response for every request."""

    async def _post_once(self, payload: dict) -> dict:
        return {"CAPI": {}}


class ApiClientThrottleTests(unittest.IsolatedAsyncioTestCase):
    """Test that requests are spaced at least min_request_interval apart."""

    async def test_post_enforces_minimum_interval_between_requests(self) -> None:
        """Requests arriving too close together can cause CMD_ERROR responses."""
        client = ThrottlingClient(
            "wem-sg", "admin", "Admin123", min_request_interval=0.05
        )

        start = time.monotonic()
        await client._post({"a": 1})
        await client._post({"a": 2})
        await client._post({"a": 3})
        elapsed = time.monotonic() - start

        self.assertGreaterEqual(elapsed, 0.1)


if __name__ == "__main__":
    unittest.main()
