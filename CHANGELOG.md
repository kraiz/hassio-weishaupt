# Changelog

## Unreleased

- Feature: Add 12 read-only WTC boiler and pump sensors: blower speed, burner target output, blower control signal, internal pump electrical power, min/max heating pump output, pump regulation mode, boiler flow temperature, burner anti-cycling lock, heating switching differential, maximum burner output in heating mode, and maximum VPT flow rate. Registers with unverified scaling are exposed as raw values. Thanks @ChristophKomenda (#24).
- Feature: The poll interval can be changed after setup: *Configure* on the integration opens the scan interval (10–300 s). The entry reloads when it changes.
- Feature: Add two diagnostic sensors on the Systemgerät device: "Parameters per request" (the current batch size, 1–6) and "Poll cycle duration" (ms). Both are disabled by default; enable them in the entity registry.
- Change: The integration starts at 6 frames per CanApiJson request. If the device answers only the first K frames and returns error echoes for the rest, the batch size drops to K (minimum 1) and grows back by one after 10 clean polls. Optional-module detection does not adapt the batch size. Refs #15, #25.
- Fix: A scheduled poll is skipped while the previous poll is still running, so slow polls no longer pile up.
- Fix: The config flow uses `probatio` as its schema library, the one Home Assistant 2026.11 uses.

## 0.3.4 - 2026-11-15

- Feature: Add read-only "Heizkurvensteilheit HK1" (heating curve slope, `MI=02`, `MX=00`, `OX=0x254B`, `OS=02`, scale 0.1) and "Heizkurve Parallelverschiebung HK1" (heating curve parallel shift, `OX=0x25AD`, signed, scale 0.1, unit K) sensors. Both were checked against the boiler controller settings on a WTC-GW 15-B. Negative parallel-shift values are decoded but not yet verified on hardware. Thanks @ChristophKomenda (#21).
- Feature: Add ten read-only HK1 settings, all validated on a WTC-GW 15-B: "Vorlaufsolltemperatur Heizgrenze" (`0x25C7`), "Frostschutz Außentemperatur" (`0x2554`), "Aufheizoptimierung" (`0x25A3`), "Gebäudebauweise" (`0x256E`), "Vorlaufsolltemperatur minimal" (`0x251B`), "Vorlaufsolltemperatur maximal" (`0x251C`), "So/Wi Umschalttemperatur" (`0x257B`), "Niveauanhebung Außentemperatur" (`0x2581`), "Warmwasserpriorität" (`0x2537`) and "Raumsolltemperatur Heizgrenze" (`0x257C`). Thanks @ChristophKomenda (#22).
- Change: Some CanApiJson objects answer with a 2-byte value to a 1-byte request. The three affected sensors (`0x251B`, `0x251C`, `0x257B`) now send `VS=1` and expect `VS=2`. The new `request_vs` field on sensor definitions only applies to these overrides; the reply check is skipped for all other sensors.
- Behaviour: "Niveauanhebung Außentemperatur HK1" (`0x2581`) reports the "Off" setting (raw −200, −20.0 °C) as unavailable instead of −20 °C.
- Behaviour: The value labels for "Warmwasserpriorität HK1" (`0x2537`) and "Raumsolltemperatur Heizgrenze HK1" (`0x257C`) list only the states observed on the reference installation (`0 = Vorrang`, `1 = Ein`). Other raw values show as "Unknown (n)".
- All new sensors are read-only and in the Systemgerät (SG) device group. No write requests are sent.
- Note: The new HK1 sensors have been verified on one WTC-GW 15-B only. Other boilers and firmware versions are unverified.

## 0.3.3 - 2026-11-07

- Feature: Add "Brennerstarts gesamt" (burner starts) and "Brennerbetriebsstunden gesamt" (burner operating hours) sensors from the CanApiJson counters `MI=09`, `MX=01`, `OX=0x2920` and `OX=0x2921` (raw values, unscaled). Requested in #20.
- Feature: Add "Zeit bis Wartung" (`OX=0x2641`) and "Wartungsintervall" (`OX=0x2642`) diagnostic sensors (`MI=09`, `MX=01`, `VS=2`, unit h). Disabled by default; enable them in the entity registry. Addresses confirmed in [JS-DE-Tech/hacs-weishaupt-lan](https://github.com/JS-DE-Tech/hacs-weishaupt-lan).

## 0.3.2 - 2026-11-01

- Fix: Swap the register addresses of the "WTC Abgastemperatur" (now `OX=0x2537`, `OS=0x00`) and "WTC Rücklauftemperatur" (now `OX=0x2533`, `OS=0x02`) sensors. The values were reversed compared to the boiler's display (#18, thanks @cg089). The Modbus register references are unchanged.

## 0.3.1 - 2026-10-21

- Upgrade: Users upgrading from a version before 0.3.0 should remove and reinstall the integration, so legacy unavailable optional entities and devices are cleared from Home Assistant's registry. Users already on 0.3.0 can simply update.
- Feature: Add a "WTC Istleistung" sensor exposing the boiler's current modulation level in percent (CanApiJson `MI=07`, `OX=0x2534`, raw / 100, rounded to whole percent to match the display). Identified and confirmed on a WTC-GB 15-B Kompakt; not part of the official Modbus register table. Thanks @Dud3z for finding the register (BorgNumberOne/Weishaupt_CanApiJson#7) and for the implementation (#16).
- Feature: Add a `Betriebsart Warmwasser` switch (DHW on/off) for the CanApiJson object `MI 03 / OX 0x2520 / OS 02` (1 = Ein, 2 = Aus). The object is not in Weishaupt's official register table; the address was verified on a WTC-GW 15-B by @jvejmelka (#4).
- Fix: Store the optional-module detection (Heizkreis 2, Heizkreis 3, Solar) in the config entry. Restarts and reloads no longer send probes to absent modules, which could lock the Systemgerät after a few quick setups (#15, thanks @zebbl for the reports and measurements). Only complete probe answers are stored; a probe without any answer is retried on the next setup.
- Feature: Add *Reconfigure → Re-detect optional modules* to probe again after adding or removing a module. Reloading the integration no longer re-detects; use this instead.

## 0.3.0 - 2026-09-16

- Fix: Replace the deprecated `via_device` parameter with `via_device_id` when linking sensor, select and button devices to the Systemgerät, avoiding a deprecation warning that would break in HA Core 2027.8.0 (#14).
- Improvement: Reduce the CanApiJson read batch size from 10 to 6 VG frames and enforce a minimum ~300ms gap between requests, avoiding intermittent `CMD_ERROR` responses observed on some hardware with larger/faster batches.
- Improvement: Auto-detect optional device groups (Heizkreis 2, Heizkreis 3, Solar) from the first successful poll instead of always creating them; installations without those expansion modules no longer get permanently-unavailable entities. Detection happens once per config entry load; reload the integration to re-probe.
- Credit: The batching, throttling and module-detection changes above are informed by real-hardware findings from [JS-DE-Tech/hacs-weishaupt-lan](https://github.com/JS-DE-Tech/hacs-weishaupt-lan), a fork of this integration, which also independently confirms the Heizkreis 3 `MX=2` assumption from #11.
- Fix: Probe optional device groups (Heizkreis 2, Heizkreis 3, Solar) once each during initial detection instead of polling every sensor in every absent group; this avoids permanently locking Systemgerät firmware that retains failed absent-module requests (#15).
- Documentation: Recommend removing and reinstalling the integration for users upgrading from before 0.3.0, so legacy unavailable optional entities and devices are cleared from Home Assistant's registry.

## 0.2.7 - 2026-09-02

- Feature: Add a "Heizkreis 3" sensor group for a second EM-HK expansion module, assuming it addresses itself as `MX=2` on the bus. Unconfirmed against real hardware; entities stay unavailable if the assumption doesn't match the device (#11).

## 0.2.6 - 2026-08-29

- Feature: Translate all sensor, select and button entity names via Home Assistant's `translation_key` mechanism instead of hardcoded German strings. Adds English and Italian translations alongside the existing German ones; any other HA language falls back to English (#12).
- Fix: Identify the existing EM-HK sensor group as Heizkreis 2 and document its `MX=1` register mapping (#11).
- Fix: Correct the swapped day/year registers and expose the device time as a timezone-aware timestamp (#10).

## 0.2.5 - 2026-04-19

- Fix: Make device timestamp timezone-aware (UTC) to fix auto-update of sensor values (#5, thanks @wagnerpizza).

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
