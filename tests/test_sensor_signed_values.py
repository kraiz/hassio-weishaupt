"""Regression tests for signed sensor values that collide with sentinel patterns.

Bug: native_value() checks the "not available" sentinels (0xFFFF / 0x8000 for
2-byte, 0xFFFFFFFF / 0x80000000 for 4-byte) on the unsigned raw value before
applying the signed conversion. A signed raw value of -1 (e.g. -0.1 °C on the
outdoor sensor) therefore reads as "unavailable".
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from test_sensor_device_info import sensor, sensors


def _entity(key: str, raw: int):
    definition = next(d for d in sensors.ALL_SENSORS if d.key == key)
    return sensor.WeishauptSensorEntity(
        coordinator=SimpleNamespace(data={key: {"value_int": raw, "value_hex": ""}}),
        sensor_def=definition,
        entry=SimpleNamespace(entry_id="entry-123"),
    )


class OutdoorTemperatureSignedEdgeTests(unittest.TestCase):
    """sg_aussentemperatur: 2-byte signed, scale 0.1 °C."""

    KEY = "sg_aussentemperatur"

    def test_signed_edge_values(self) -> None:
        cases = (
            (0x0000, 0.0),  # 0.0 °C
            (0x0001, 0.1),
            (0xFFFF, -0.1),  # -1 signed: must NOT be treated as unavailable
            (0xFFFE, -0.2),
            (0xFFF6, -1.0),  # -10
            (0xFF9C, -10.0),  # -100
            (0x7FFF, 3276.7),  # largest positive
            (0x8001, -3276.7),  # most negative non-sentinel
            (0x8000, None),  # -32768 sentinel: unavailable
        )
        for raw, expected in cases:
            with self.subTest(raw=hex(raw)):
                self.assertEqual(_entity(self.KEY, raw).native_value, expected)


class SignedSentinelCollisionTests(unittest.TestCase):
    """Every plain signed sensor must decode raw -1 as -1 * scale."""

    def test_minus_one_is_a_value_for_all_signed_sensors(self) -> None:
        failures = []
        for d in sensors.ALL_SENSORS:
            if not d.signed or d.value_map is not None or d.source_key is not None:
                continue
            if d.none_values or d.byte_length is not None or d.vs not in (2, 4):
                continue
            precision = 2 if d.precision is None else d.precision
            expected = round(-1 * d.scale, precision) if d.scale != 1.0 else -1
            if d.scale != 1.0 and precision == 0:
                expected = round(-1 * d.scale)
            raw = (1 << (8 * d.vs)) - 1  # 0xFFFF or 0xFFFFFFFF
            got = _entity(d.key, raw).native_value
            if got != expected:
                failures.append(f"{d.key}: raw {hex(raw)} -> {got!r}, expected {expected!r}")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
