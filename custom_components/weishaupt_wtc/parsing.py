"""Pure parsing helpers for Weishaupt sensor values."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Any


def extract_value_segment(
    value_hex: str,
    byte_offset: int,
    byte_length: int,
) -> tuple[str, int] | None:
    """Extract a byte segment from a raw VG value hex string."""
    start = byte_offset * 2
    end = start + (byte_length * 2)
    if len(value_hex) < end:
        return None

    segment = value_hex[start:end]
    return segment, int(segment, 16)


def decode_fault_status(raw_value: int) -> str:
    """Decode the fault status bitfield from register 121."""
    message_type = raw_value & 0x0F
    if message_type == 1:
        return "Fehler"
    if message_type == 2:
        return "Warnung"
    if message_type == 3:
        return "Info"
    if (raw_value >> 8) > 0:
        return "Fehler aktiv"
    return "Keine Meldung"


def decode_fault_status_attributes(raw_value: int) -> dict[str, Any]:
    """Decode fault status details from register 121."""
    return {
        "error_active": (raw_value >> 8) > 0,
        "system_error": bool(raw_value & 0x10),
        "message_type": decode_fault_status(raw_value),
        "module_error": not bool(raw_value & 0x10),
    }


def decode_module_attributes(raw_value: int) -> dict[str, int]:
    """Decode module identifier fields from register 123."""
    return {
        "module_id": (raw_value >> 8) & 0xFF,
        "module_index": raw_value & 0xFF,
    }


def build_device_time_iso(values: Mapping[str, int]) -> str | None:
    """Build an ISO timestamp from separate SG time/date component values."""
    year = values.get("sg_datum_jahr", 0)
    if year < 100:
        year += 2000

    try:
        dt = datetime(
            year,
            values.get("sg_datum_monat", 1),
            values.get("sg_datum_tag", 1),
            values.get("sg_uhrzeit_stunden", 0),
            values.get("sg_uhrzeit_minuten", 0),
        )
    except ValueError:
        return None

    return dt.isoformat()
