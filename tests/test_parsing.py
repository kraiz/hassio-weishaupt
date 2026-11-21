"""Unit tests for pure Weishaupt parsing helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "weishaupt_wtc"
    / "parsing.py"
)

SPEC = importlib.util.spec_from_file_location("weishaupt_parsing", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
parsing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parsing)


class ParsingTests(unittest.TestCase):
    """Test pure parsing helpers without importing Home Assistant."""

    def test_extract_value_segment(self) -> None:
        """Extract a two-byte segment after skipping one 16-bit register."""
        segment = parsing.extract_value_segment("1234567890abcdef", 2, 2)

        self.assertEqual(segment, ("5678", 0x5678))

    def test_decode_fault_status(self) -> None:
        """Decode documented fault status values."""
        self.assertEqual(parsing.decode_fault_status(0x0000), "Keine Meldung")
        self.assertEqual(parsing.decode_fault_status(0x0001), "Fehler")
        self.assertEqual(parsing.decode_fault_status(0x0002), "Warnung")
        self.assertEqual(parsing.decode_fault_status(0x0003), "Info")
        self.assertEqual(parsing.decode_fault_status(0x0100), "Fehler aktiv")

    def test_decode_module_attributes(self) -> None:
        """Split module identifier into documented ID and index fields."""
        attrs = parsing.decode_module_attributes(0x1234)

        self.assertEqual(attrs["module_id"], 0x12)
        self.assertEqual(attrs["module_index"], 0x34)

    def test_build_device_time(self) -> None:
        """Build a timestamp from separate SG date/time registers."""
        timestamp = parsing.build_device_time(
            {
                "sg_uhrzeit_stunden": 20,
                "sg_uhrzeit_minuten": 37,
                "sg_datum_tag": 26,
                "sg_datum_monat": 2,
                "sg_datum_jahr": 23,
            },
            timezone.utc,
        )

        self.assertEqual(timestamp, datetime(2023, 2, 26, 20, 37, tzinfo=timezone.utc))


class AccumulateDailyTotalTests(unittest.TestCase):
    """The running total only changes when the source value changes."""

    def test_first_reading_is_recorded_not_added(self) -> None:
        self.assertEqual(parsing.accumulate_daily_total(0.0, None, 3200, 0.01), (0.0, 3200))

    def test_unchanged_source_adds_nothing(self) -> None:
        self.assertEqual(parsing.accumulate_daily_total(12.5, 3200, 3200, 0.01), (12.5, 3200))

    def test_changed_source_adds_new_day_value(self) -> None:
        total, last = parsing.accumulate_daily_total(0.0, 3200, 3850, 0.01)
        self.assertAlmostEqual(total, 38.5)
        self.assertEqual(last, 3850)

    def test_totals_accumulate_over_days(self) -> None:
        total, last = 0.0, None
        for raw in (3200, 3200, 3850, 3000, 3000, 2950):
            total, last = parsing.accumulate_daily_total(total, last, raw, 0.01)
        self.assertAlmostEqual(total, 38.5 + 30.0 + 29.5)
        self.assertEqual(last, 2950)


if __name__ == "__main__":
    unittest.main()
