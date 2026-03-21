"""Unit tests for pure Weishaupt parsing helpers."""

from __future__ import annotations

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
parsing = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
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

    def test_build_device_time_iso(self) -> None:
        """Build an ISO timestamp from separate SG date/time registers."""
        iso_value = parsing.build_device_time_iso(
            {
                "sg_uhrzeit_stunden": 20,
                "sg_uhrzeit_minuten": 37,
                "sg_datum_tag": 26,
                "sg_datum_monat": 2,
                "sg_datum_jahr": 23,
            }
        )

        self.assertEqual(iso_value, "2023-02-26T20:37:00")


if __name__ == "__main__":
    unittest.main()
