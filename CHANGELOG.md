# Changelog

## 0.2.3 - 2026-04-04

- Fix: Add missing `device_info` to `WeishauptSelectEntity` so the Select is visible in the HA device view.
- Feature: Add Button platform with `Warmwasser-Push` button (Register 131) that writes value 1 to trigger a domestic hot water push cycle.

## 0.2.2 - 2026-03-30

- Feature: Add writable Select for `sg_betriebsart_hk1_vorgabe` (Register 100) to allow changing Heizkreis 1 Betriebsart (#4).
- Feature: Add API write support for CanApiJson SET frames so writable registers can be updated from HA.

## 0.2.1 - 2026-03-21

- Fix: Create the SG system device explicitly so child devices reference a valid `via_device` parent and avoid upcoming Home Assistant registry breakage.
- Test: Add regression coverage for the SG root device and child device hierarchy.

## 0.2.0 - 2026-03-21

- Feature: Re-add the documented HK and SOL sensor groups from the PDF register map, restoring Heizkreis and Solar entities.
- Feature: Add the documented SG fault block diagnostics from Modbus 120-123 as disabled-by-default diagnostic sensors.
- Fix: Restore the documented SG time/date component registers so the consolidated `sg_device_time` sensor is populated correctly.
- Fix: Poll only real device frames and derive synthetic sensors from the fetched source frames.
- Fix: Guard against empty device responses and log a warning instead of failing with a `NoneType` error during coordinator refresh (#2).

## 0.1.3 - 2026-02-27

- Feature: Added logo.

## 0.1.2 - 2026-02-27

- Fix: sensor amount in README.md was outdated after removing HK and SOL device groups. Updated to reflect current sensor count (50).
- Fix: update manifest version to 0.1.2 for latest release.

## 0.1.1 - 2026-02-27

- Breaking: Drop `HK_SENSORS` and `SOL_SENSORS` from the integration (these device groups will no longer be registered by default). This reduces entity count and focuses the integration on `SG` and `WTC` device groups.

## 0.0.8 - 2026-02-27

- Release: prepare and publish v0.0.8 (includes latest fixes).

## 0.0.7 - 2026-02-27

- Reverted the parent device change from 0.0.5.

## 0.0.6 - 2026-02-27

- Release: prepare and publish v0.0.6 (bugfixes and registry fixes).

## 0.0.5 - 2026-02-27

- Fix: create parent device so `via_device` references are valid and avoid registry warnings.


## 0.0.4 - 2026-02-27

- Fix: Treat sentinel raw values (0x8000/0xFFFF) as unavailable so sensors don't report extreme negative temperatures.

## 0.0.3 - 2026-02-27

- Consolidate WEM Systemgerät diagnostic time/date registers into a single `Uhrzeit / Datum` (`sg_device_time`) timestamp sensor.
- Remove the separate `Uhrzeit (Stunden)`, `Uhrzeit (Minuten)`, `Datum (Tag)`, `Datum (Monat)`, and `Datum (Jahr)` sensors.
- Diagnostic sensors remain disabled by default.

## 0.0.2

- Previous changes.
