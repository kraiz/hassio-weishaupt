# Additional WTC boiler/pump read-only sensors (proposed PR)

## Scope

12 additional CanApiJson GET-only WTC sensors; the existing WTC actual
modulation (`07/00/2534/00`) is deliberately not duplicated. Keys are new,
and this patch does not alter existing sensor unique IDs, write operations,
coordinator timing, request batching or scan interval.

## Source / initial hardware observations

Adapted register mappings from
[JS-DE-Tech/hacs-weishaupt-lan PR #14](https://github.com/JS-DE-Tech/hacs-weishaupt-lan/pull/14),
which documents single-register read-only probes on one WTC-GW 15-B (2026-11-10).
These are **not yet validated within kraiz/hassio-weishaupt**. The 13 source
registers returned numeric responses on that unit; the source notes partial
failed read batches, intermittent unavailable sensors, and unconfirmed meanings.

Display-checked observations on the source system:
- Burner target `07/00/2542/00`: raw 1569 -> 15.69%.
- Blower control `07/00/257E/00`: raw 1042 -> 10.42%.
- Internal pump `09/01/261B/02`: 11 W, GET VS=2 / response VS=1.
- Min/max pump settings `07/00/256B/02` / `07/00/256C/02`: 30 / 80%.
- Pump mode `09/01/266A/02`: raw 9 was *Konstantdruck Stufe 2*
  on that device; this PR intentionally exposes raw 9 until enum is verified.

Others use neutral raw values without claiming units, signedness or scaling.

## Verification checklist (not completed)

- [ ] Run `python3 -m unittest discover -s tests -p 'test_*.py' -q`
- [ ] Verify no HA unique-ID collisions, duplicate entities, or legacy regressions
- [ ] Install this branch on a dedicated WTC-GW 15-B test system
- [ ] Record and compare controller display readings for each new sensor
- [ ] Monitor hourly data gaps, communication failures, and batch errors over 24-72h
- [ ] Re-test with additional models and firmware

Avoid simultaneous external register probing during stability measurement.
The device already has a bounded 6-register batch size and request pacing;
adding twelve periodic reads increases load. Consider default-disabled entities
or staged rollout if long-duration polling shows instability.
