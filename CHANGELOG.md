# Changelog

## 0.0.8 - 2026-02-27

- Release: prepare and publish v0.0.8 (includes latest fixes).

## 0.0.7 - 2026-02-27

- Reverted the parent device change from 0.0.5.

## 0.0.6 - 2026-02-27

- Release: prepare and publish v0.0.6 (bugfixes and registry fixes).

## 0.0.5 - 2026-02-27

- Fix: create parent device so `via_device` references are valid and avoid registry warnings.

## 0.1.0 - 2026-02-27

- Breaking: Drop `HK_SENSORS` and `SOL_SENSORS` from the integration (these device groups will no longer be registered by default). This reduces entity count and focuses the integration on `SG` and `WTC` device groups.

## 0.0.4 - 2026-02-27

- Fix: Treat sentinel raw values (0x8000/0xFFFF) as unavailable so sensors don't report extreme negative temperatures.

## 0.0.3 - 2026-02-27

- Consolidate WEM Systemgerät diagnostic time/date registers into a single `Uhrzeit / Datum` (`sg_device_time`) timestamp sensor.
- Remove the separate `Uhrzeit (Stunden)`, `Uhrzeit (Minuten)`, `Datum (Tag)`, `Datum (Monat)`, and `Datum (Jahr)` sensors.
- Diagnostic sensors remain disabled by default.

## 0.0.2

- Previous changes.
