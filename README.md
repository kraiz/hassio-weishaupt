# Weishaupt WTC - Home Assistant Integration

Custom Home Assistant integration for Weishaupt heating systems using the **CanApiJson** protocol (JSON over HTTP).

This integration communicates directly with the **Weishaupt Systemgerät (SG)** unit via the local network — no cloud required.

## Supported Hardware

- **Weishaupt Systemgerät 2.5 / 2.6** (48301122172, 48301122242, 48301122512, 48301122522)
- Any Weishaupt heating system controlled through the Systemgerät (gas boilers, heat pumps, etc.)

## Prerequisites

1. The Weishaupt Systemgerät must be connected to your local network via RJ-45
2. JSON function must be enabled in the Systemgerät settings
3. You need the IP address of the Systemgerät (default hostname: `wem-sg`)
4. Default credentials: `admin` / `Admin123`

Test access by opening in your browser:
```
http://admin:Admin123@wem-sg/ajax/CanApiJson.json
```

## Installation

### HACS (Manual Repository)

1. Open HACS in Home Assistant
2. Go to Integrations → ⋮ (top right) → Custom repositories
3. Add this repository URL and select "Integration" as category
4. Install "Weishaupt WTC"
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/weishaupt_wtc` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Weishaupt WTC"
3. Enter the IP address (or hostname) of your Systemgerät
4. Optionally adjust username, password, and scan interval

## Sensors

The integration provides **50 sensors** across these device groups:

### Systemgerät (SG) — Modbus 100-155
- Betriebsart HK1 (Vorgabe / aktuell)
- So/Wi Umschaltung, Status HK1
- Raumsolltemperaturen (Komfort / Normal / Absenk / aktuell)
- Vorlaufsolltemperaturen (Komfort / Normal / Absenk / Sonderniveau / aktuell)
- Vorlaufisttemperatur, Plattenwärmetauschertemperatur
- Pufferspeicher Temperatur (oben / unten)
- Außentemperatur
- Systembetriebsart
- Wärmeanforderung (Heizung / Warmwasser)
- Warmwasser: Status, Push, Solltemperaturen, Ist-Temperatur, Zirkulation, Pumpe
- Kaskade: Folgewechsel, Abgleichtemperatur, Modulation, Sollwerte
- Uhrzeit und Datum

### WTC Kessel — Modbus 160-177
- Betriebsphase WTC und Brenner
- Vorlaufsolltemperatur, Kesseltemperatur, Rücklauftemperatur, Abgastemperatur
- Volumenstrom VPT, Anlagendruck
- Wärmeleistung VPT
- Tageswärmemenge Vortag (Gesamt / Heizen / Warmwasser)

## Protocol

This integration uses the Weishaupt CanApiJson protocol — a CAN bus-like protocol transmitted as JSON over HTTP POST requests to `/ajax/CanApiJson.json`.

Based on research from [BorgNumberOne/Weishaupt_CanApiJson](https://github.com/BorgNumberOne/Weishaupt_CanApiJson).

## License

MIT
