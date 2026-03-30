"""API client for Weishaupt WTC CanApiJson protocol."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_ENDPOINT, CMD_GET, CMD_SET, CMD_RESPONSE, CMD_ERROR, SRC_DDC

_LOGGER = logging.getLogger(__name__)

REQUEST_ID = "12345678"
MAX_PARAMS_PER_REQUEST = 10  # Weishaupt supports up to 10 VG frames per request


class WeishauptApiError(Exception):
    """Exception for Weishaupt API errors."""


class WeishauptConnectionError(WeishauptApiError):
    """Exception for connection errors."""


class WeishauptAuthError(WeishauptApiError):
    """Exception for authentication errors."""


def build_vg_frame(cmd: int, mi: int, mx: int, ox: int, os_val: int, vs: int) -> str:
    """Build a VG hex frame string for a CanApiJson request.

    Format: CM(1B) MI(1B) MX(1B) OX(2B) OS(1B) VS(2B)
    """
    return f"{cmd:02x}{mi:02x}{mx:02x}{ox:04x}{os_val:02x}{vs:04x}00"


def build_read_vg(mi: int, mx: int, ox: int, os_val: int, vs: int) -> str:
    """Build a VG read request frame (CMD=0x01 GET)."""
    # For read, we pad with zeros for the value area
    padding = "00" * vs
    return f"{CMD_GET:02x}{mi:02x}{mx:02x}{ox:04x}{os_val:02x}{vs:04x}{padding}"


def build_write_vg(
    mi: int, mx: int, ox: int, os_val: int, vs: int, value_hex: str
) -> str:
    """Build a VG write request frame (CMD=0x03 SET) including value area."""
    return f"{CMD_SET:02x}{mi:02x}{mx:02x}{ox:04x}{os_val:02x}{vs:04x}{value_hex}"


def parse_vg_response(vg: str) -> dict[str, Any]:
    """Parse a VG response frame.

    Returns dict with keys: cmd, mi, mx, ox, os, vs, value_hex, value_int
    """
    if len(vg) < 16:
        raise WeishauptApiError(f"VG frame too short: {vg}")

    cmd = int(vg[0:2], 16)
    mi = int(vg[2:4], 16)
    mx = int(vg[4:6], 16)
    ox = int(vg[6:10], 16)
    os_val = int(vg[10:12], 16)
    vs = int(vg[12:16], 16)

    value_hex = vg[16:]
    value_int = int(value_hex, 16) if value_hex else 0

    return {
        "cmd": cmd,
        "mi": mi,
        "mx": mx,
        "ox": ox,
        "os": os_val,
        "vs": vs,
        "value_hex": value_hex,
        "value_int": value_int,
    }


class WeishauptApiClient:
    """Client to interact with Weishaupt WTC CanApiJson API."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._host = host
        self._username = username
        self._password = password
        self._session = session
        self._own_session = session is None
        self._base_url = f"http://{host}{API_ENDPOINT}"

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active session."""
        if self._session is None or self._session.closed:
            auth = aiohttp.BasicAuth(self._username, self._password)
            self._session = aiohttp.ClientSession(auth=auth)
            self._own_session = True
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    async def _post(self, payload: dict) -> dict:
        """Post a JSON payload to the Weishaupt device."""
        session = await self._ensure_session()
        headers = {
            "Connection": "keep-alive",
            "Referer": f"http://{self._host}/",
            "Content-Type": "application/json",
        }

        try:
            async with session.post(
                self._base_url,
                json=payload,
                headers=headers,
                auth=aiohttp.BasicAuth(self._username, self._password),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401:
                    raise WeishauptAuthError(
                        "Authentication failed. Check username/password."
                    )
                if response.status != 200:
                    raise WeishauptApiError(
                        f"Unexpected HTTP status: {response.status}"
                    )
                return await response.json(content_type=None)
        except aiohttp.ClientConnectorError as err:
            raise WeishauptConnectionError(
                f"Cannot connect to Weishaupt device at {self._host}: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            raise WeishauptConnectionError(
                f"Timeout connecting to Weishaupt device at {self._host}"
            ) from err

    async def test_connection(self) -> bool:
        """Test if we can connect and authenticate to the device."""
        # Try reading a simple register (Betriebsart HK1 - reg 100)
        vg = build_read_vg(mi=0x02, mx=0x00, ox=0x2533, os_val=0x02, vs=0x01)
        payload = {
            "ID": REQUEST_ID,
            "SRC": SRC_DDC,
            "CAPI": {"NN": 1, "N01": {"VG": vg}},
        }
        try:
            result = await self._post(payload)
            return bool(result and "CAPI" in result)
        except WeishauptApiError:
            raise
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False

    async def read_parameters(self, params: list[dict[str, int]]) -> dict[str, Any]:
        """Read multiple parameters from the device.

        Args:
            params: List of dicts with keys: mi, mx, ox, os, vs, key
                    where 'key' is a unique identifier for the parameter.

        Returns:
            Dict mapping key -> parsed response value dict
        """
        results = {}

        # Split into batches of MAX_PARAMS_PER_REQUEST
        for batch_start in range(0, len(params), MAX_PARAMS_PER_REQUEST):
            batch = params[batch_start : batch_start + MAX_PARAMS_PER_REQUEST]
            capi = {"NN": len(batch)}

            for i, param in enumerate(batch):
                vg = build_read_vg(
                    mi=param["mi"],
                    mx=param["mx"],
                    ox=param["ox"],
                    os_val=param["os"],
                    vs=param["vs"],
                )
                capi[f"N{i + 1:02d}"] = {"VG": vg}

            payload = {
                "ID": REQUEST_ID,
                "SRC": SRC_DDC,
                "CAPI": capi,
            }

            try:
                response = await self._post(payload)
            except WeishauptApiError as err:
                _LOGGER.error("Failed to read batch: %s", err)
                continue

            if not response:
                _LOGGER.warning("Empty response from device for payload: %s", payload)
                continue

            if "CAPI" not in response:
                _LOGGER.warning("No CAPI in response: %s", response)
                continue

            response_capi = response["CAPI"]
            for i, param in enumerate(batch):
                key = f"N{i + 1:02d}"
                if key not in response_capi:
                    _LOGGER.debug("Missing %s in response", key)
                    continue

                vg_str = response_capi[key].get("VG", "")
                if not vg_str:
                    continue

                try:
                    parsed = parse_vg_response(vg_str)
                except (ValueError, WeishauptApiError) as err:
                    _LOGGER.debug(
                        "Failed to parse VG response for %s: %s",
                        param.get("key", key),
                        err,
                    )
                    continue

                # Check for error response
                if parsed["cmd"] == CMD_ERROR:
                    _LOGGER.debug(
                        "Error response for %s: %s",
                        param.get("key", key),
                        vg_str,
                    )
                    continue

                # Check it's a proper response
                if parsed["cmd"] == CMD_RESPONSE:
                    results[param["key"]] = parsed

        return results

    async def write_parameter(
        self,
        mi: int,
        mx: int,
        ox: int,
        os_val: int,
        vs: int,
        value_int: int,
    ) -> bool:
        """Write a single parameter value to the device.

        Returns True on success, False on failure.
        """
        # Encode value_int as big-endian hex with vs bytes
        value_hex = f"{value_int:0{vs * 2}x}"
        vg = build_write_vg(
            mi=mi, mx=mx, ox=ox, os_val=os_val, vs=vs, value_hex=value_hex
        )

        payload = {
            "ID": REQUEST_ID,
            "SRC": SRC_DDC,
            "CAPI": {"NN": 1, "N01": {"VG": vg}},
        }

        try:
            response = await self._post(payload)
        except WeishauptApiError as err:
            _LOGGER.error("Failed to write parameter: %s", err)
            raise

        if not response:
            _LOGGER.debug("Empty response from device for write payload: %s", payload)
            return False

        if "CAPI" not in response:
            _LOGGER.debug("No CAPI in write response: %s", response)
            return False

        response_capi = response["CAPI"]
        key = "N01"
        if key not in response_capi:
            _LOGGER.debug("Missing %s in write response", key)
            return False

        vg_str = response_capi[key].get("VG", "")
        if not vg_str:
            _LOGGER.debug("No VG in write response for %s", key)
            return False

        try:
            parsed = parse_vg_response(vg_str)
        except (ValueError, WeishauptApiError) as err:
            _LOGGER.debug("Failed to parse VG write response: %s", err)
            return False

        if parsed["cmd"] == CMD_ERROR:
            _LOGGER.debug("Error response for write VG: %s", vg_str)
            return False

        return True
