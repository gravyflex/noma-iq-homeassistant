# NOMA iQ Home Assistant Integration

Custom Home Assistant integration for Canadian Tire `NOMA iQ` devices, starting with dehumidifiers.

This repo exists because the `NOMA iQ` dehumidifier on my network was not compatible with the existing `midea_ac_lan` custom integration. I verified that directly:

- A working Midea dehumidifier on my network responds on local Midea port `6444` and is discoverable by `midealocal`.
- The NOMA unit does not respond on `6444`.
- The NOMA unit does not show up in `midealocal.discover(...)`.
- The NOMA Android app is Ayla-backed, not Midea-LAN-backed.

So this integration targets the NOMA cloud path through Ayla.

## What This Repo Contains

- A Home Assistant custom integration under `custom_components/noma_iq`
- A small Ayla wrapper specialized for the NOMA iQ app tenant
- A debug CLI under `scripts/dump_noma_iq.py`
- A dehumidifier-focused first implementation

## What I Verified Before Writing This

From the live environment:

- The NOMA/Nook dehumidifier is on the network at `10.168.20.68`
- Its MAC is `08:b6:1f:c5:40:1c`
- It is visible in UniFi as `Numa Dehumidifier`
- It does **not** accept Midea LAN connections on `6444`
- It **does** expose TCP `80`, but not in a way that makes it a drop-in Home Assistant local integration

From the official NOMA iQ Android APK:

- The app includes Ayla SDK components
- The app identifies the dehumidifier family as:
  - `oem_model = dehum`
  - `group_type = dehumidifier`
- The app includes dehumidifier-related notifications/properties such as:
  - `filter_clean_alarm`
  - `water_bucket_full`
- The app tenant identifiers are stored in `assets/ctc.json`

This means the right starting point is Ayla cloud auth plus device/property enumeration, not trying to fake a Midea LAN device.

## Current Scope

This repo currently aims to support:

- login to the NOMA iQ / Ayla tenant
- choose a device during config flow
- poll device properties
- expose a dehumidifier entity when the expected properties are present
- expose basic binary sensors for water bucket and filter alarms
- expose additional writable boolean properties as switches
- expose target humidity as a number entity
- expose writable enumerated properties like mode and fan speed as select entities
- provide a CLI tool to dump raw properties for mapping refinement

This first version is intentionally conservative. It is designed to be debuggable and extendable instead of pretending the entire device model is known up front.

## Live Dehumidifier Property Map Confirmed

For the DSN `AC000W029233145` / `Nook DH` device, I confirmed these live Ayla properties:

- writable:
  - `power`
  - `humidity` (target humidity)
  - `mode`
  - `fan_speed`
- read-only:
  - `indoor_humidity`
  - `water_bucket_full`
  - `filter_clean_alarm`
  - `humidity_sensor_fault`
  - `wifi_rssi`
  - `version`

That live property dump is why this repo maps:

- target humidity -> `humidity`
- current humidity -> `indoor_humidity`

for this device family.

## Architecture

### 1. Authentication

The integration authenticates against the Ayla cloud using the same app tenant identifiers embedded in the NOMA iQ Android application.

That avoids guessing tenant IDs or pretending the device is on a generic Ayla tenant.

### 2. Device Selection

The config flow:

1. asks for your NOMA iQ email and password
2. logs in to Ayla
3. lists the devices visible to your account
4. lets you choose which device to add

The selected device DSN is stored in the Home Assistant config entry.

### 3. Polling

The integration uses a `DataUpdateCoordinator` to:

- refresh the device list when needed
- locate the configured DSN
- fetch all device properties

### 4. Property Mapping Strategy

This integration uses a two-layer approach:

- exact/known aliases for dehumidifier properties
- dynamic fallback for simple writable boolean properties

That is deliberate. NOMA/Ayla property names can vary across products and firmware versions. The only sane way to build this safely is to:

- support the obvious/confirmed fields first
- provide a debug dump tool
- expand the mapping with real captured property payloads

## Installation

### Option A: Manual custom component install

Copy `custom_components/noma_iq` into your Home Assistant config directory:

```bash
cp -r custom_components/noma_iq /config/custom_components/
```

Restart Home Assistant.

### Option B: Development symlink

If you are developing locally:

```bash
ln -s /path/to/repo/custom_components/noma_iq /config/custom_components/noma_iq
```

Restart Home Assistant.

## Home Assistant Setup

1. Go to `Settings -> Devices & Services`
2. Click `Add Integration`
3. Search for `NOMA iQ`
4. Enter your NOMA iQ email and password
5. Select the dehumidifier you want to add

If login succeeds but no devices appear:

- verify the device is bound to the same NOMA iQ account
- use the CLI debug tool below to inspect the returned device list

## Debug CLI

The CLI is intentionally included because Ayla-backed devices often need real property inspection before building clean entities.

### List devices

```bash
python scripts/dump_noma_iq.py \
  --username you@example.com \
  --password 'your-password'
```

### Dump one device’s full property map

```bash
python scripts/dump_noma_iq.py \
  --username you@example.com \
  --password 'your-password' \
  --dsn AC000W029233145
```

### Output as JSON

```bash
python scripts/dump_noma_iq.py \
  --username you@example.com \
  --password 'your-password' \
  --dsn AC000W029233145 \
  --json
```

This is the tool to use if:

- the device logs in but entities are missing
- a control is present in the NOMA app but not exposed in HA yet
- you want to contribute support for another NOMA product family

## Current Entity Behavior

### Confirmed entities for the tested Nook dehumidifier

For the live `Nook DH` unit used during development, the integration now creates:

- a dehumidifier entity
- a power switch
- a target humidity number
- a mode select
- a fan speed select
- a current humidity sensor
- bucket-full and filter-clean binary sensors

The extra power switch and target humidity number are intentional even when the humidifier entity exists. They give you direct control surfaces in the UI and make debugging much easier if Home Assistant’s humidifier domain behavior changes between releases.

### Binary sensors

When present, it exposes:

- bucket full / water full status
- filter-clean alarm

### Switches

Writable boolean properties are exposed as switches, including `power` for the current dehumidifier implementation.

### Number entities

Writable numeric properties that map cleanly to a core control are exposed as number entities. For the tested dehumidifier, that means:

- target humidity

### Select entities

Writable enumerated properties are exposed as selects. For the tested dehumidifier, that means:

- mode
- fan speed

That gives a safe path for additional product-specific toggles without hardcoding every feature on day one.

## Limitations

### 1. This is cloud-backed

This is not a local integration today.

That is not a design preference. It is a consequence of the live device behavior I observed:

- no Midea local protocol
- no useful local control path discovered yet

If a local API is later identified, this repo can grow a local mode.

### 2. Property mapping is still evolving

The NOMA app clearly supports more than the first version of this integration exposes.

That is why the CLI dumper is included from the start.

### 3. App tenant coupling

This integration depends on the current NOMA iQ app tenant identifiers. If Canadian Tire changes tenants or app credentials in a future app version, login could break until the tenant metadata is refreshed.

## Publishing Plan

If this proves stable, the next steps are:

1. add screenshots
2. add diagnostics support
3. add more dehumidifier properties and controls
4. add tests around property alias resolution
5. package for HACS

## Development Notes

### Known app facts extracted from the APK

From `assets/ctc.json`:

- app id: `ctc-noma-Bg-id`
- app secret: `ctc-noma-WNHWBmAGLoaMl8xq8lx9XxGmiTQ`

From `assets/supported_devices_info_prod.json`:

- dehumidifier `oem_model`: `dehum`
- notifications include:
  - `filter_clean_alarm`
  - `water_bucket_full`

These values were extracted directly from the published NOMA iQ Android application.

## Repo Layout

```text
custom_components/noma_iq/
  __init__.py
  ayla.py
  binary_sensor.py
  config_flow.py
  const.py
  coordinator.py
  entity.py
  humidifier.py
  manifest.json
  sensor.py
  strings.json
  switch.py
scripts/
  dump_noma_iq.py
```

## Status

The repo is implementation-ready and designed for live account testing.

What still requires real credentials:

- confirming the exact live property names returned by your account for the Nook device
- validating that the dehumidifier controls map cleanly to HA entity behaviors

That is the point of the first test pass.
