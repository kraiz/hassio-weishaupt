"""DataUpdateCoordinator for Weishaupt WTC."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WeishauptApiClient, WeishauptApiError, WeishauptConnectionError
from .const import DOMAIN
from .sensors import (
    OPTIONAL_GROUPS,
    POLLED_SENSORS,
    WeishauptDeviceGroup,
    WeishauptSensorDefinition,
)

_LOGGER = logging.getLogger(__name__)

# Data keys for the coordinator's own diagnostics (not device objects).
KEY_BATCH_SIZE = "int_batch_size"
KEY_POLL_DURATION = "int_poll_duration"


class WeishauptDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching data from Weishaupt device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: WeishauptApiClient,
        scan_interval: int = 30,
        active_groups: set[WeishauptDeviceGroup] | None = None,
        on_groups_detected: Callable[[set[WeishauptDeviceGroup]], None] | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        # None until detection has run; then the optional groups (HK, HK3, SOL, ...)
        # that responded on this device. Restored from the config entry when stored.
        # shortcut: a module removed after detection stays polled until Reconfigure re-detects, upgrade to dropping groups after repeated CMD_ERROR
        self.active_groups = active_groups
        self._on_groups_detected = on_groups_detected
        # True while a poll is in flight. A poll that starts while this is set is
        # skipped, so slow polls (smaller batches) never pile up.
        self._poll_running = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Weishaupt device."""
        if self._poll_running:
            _LOGGER.debug("Previous poll still running, skipping this cycle")
            return self.data if self.data is not None else {}
        self._poll_running = True
        started = time.monotonic()
        try:
            results = await self._poll()
        finally:
            self._poll_running = False
        # Diagnostic values, computed here rather than read from the device.
        results[KEY_BATCH_SIZE] = {"value_int": self.client.batch_size}
        results[KEY_POLL_DURATION] = {
            "value_int": round((time.monotonic() - started) * 1000)
        }
        return results

    async def _poll(self) -> dict[str, Any]:
        """Run one poll cycle against the device."""
        detecting = self.active_groups is None
        optional_probes: dict[WeishauptDeviceGroup, WeishauptSensorDefinition] = {}
        sensor_definitions = POLLED_SENSORS
        if detecting:
            for sensor_def in POLLED_SENSORS:
                if sensor_def.group in OPTIONAL_GROUPS:
                    optional_probes.setdefault(sensor_def.group, sensor_def)
            sensor_definitions = [
                sensor_def
                for sensor_def in POLLED_SENSORS
                if sensor_def.group not in OPTIONAL_GROUPS
            ] + list(optional_probes.values())

        params = []
        for sensor_def in sensor_definitions:
            if (
                self.active_groups is not None
                and sensor_def.group in OPTIONAL_GROUPS
                and sensor_def.group not in self.active_groups
            ):
                continue
            params.append(
                {
                    "key": sensor_def.key,
                    "mi": sensor_def.mi,
                    "mx": sensor_def.mx,
                    "ox": sensor_def.ox,
                    "os": sensor_def.os,
                    "vs": sensor_def.vs,
                    "request_vs": sensor_def.request_vs,
                }
            )

        try:
            results, answered = await self.client.read_parameters_with_status(
                params, adapt_batch_size=not detecting
            )
        except WeishauptConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except WeishauptApiError as err:
            raise UpdateFailed(f"API error: {err}") from err

        if detecting:
            self._finish_detection(optional_probes, results, answered)

        return results

    def _finish_detection(
        self,
        probes: dict[WeishauptDeviceGroup, WeishauptSensorDefinition],
        results: dict[str, Any],
        answered: set[str],
    ) -> None:
        """Turn probe answers into active groups; persist only complete answers."""
        self.active_groups = {
            group for group, sensor_def in probes.items() if sensor_def.key in results
        }
        _LOGGER.info(
            "Detected optional device groups: %s",
            sorted(group.value for group in self.active_groups),
        )
        # A probe without any reply says nothing about its module. Keep the result
        # for this session, but don't persist it, so the next setup probes again.
        # shortcut: one CMD_ERROR probe is stored as absent until Reconfigure re-detects, upgrade to retry-before-store if transient errors show up
        complete = all(sensor_def.key in answered for sensor_def in probes.values())
        if complete and self._on_groups_detected is not None:
            self._on_groups_detected(self.active_groups)
