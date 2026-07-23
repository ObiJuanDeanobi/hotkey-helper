# Hotkey Helper

Hotkey Helper is an offline, context-aware keyboard-shortcut sidebar for
KDE Plasma. It detects the focused application and displays a human-readable
JSON Hotkey Pack for that application.

The first supported target is CachyOS with KDE Plasma 6 on Wayland. The
project is currently an early vertical-slice prototype.

## First milestone

The initial end-to-end goal is deliberately small:

1. Focus Dolphin.
2. KWin reports Dolphin's application identity.
3. Hotkey Helper loads `org.kde.dolphin.json`.
4. The sidebar displays verified Dolphin shortcuts.

See [the product specification](docs/product-spec.md) for the agreed behavior
and acceptance criteria.

## Inventory a CachyOS installation

CachyOS installations are customizable, so Hotkey Helper uses the installed
applications on the actual machine rather than assuming a universal default
list.

Copy this repository to the CachyOS machine and run:

```bash
python tools/inventory_apps.py --include-package-owner
```

This creates `hotkey-helper-inventory.json`. The export contains application
identifiers and package names, but intentionally excludes host names, user
names, and application command arguments.

## Repository layout

```text
app/             Qt/QML sidebar application
kwin-script/     Plasma Wayland focused-window bridge
packs/           Built-in JSON Hotkey Packs
schema/          Pack format specification
tools/           Inventory and validation tools
tests/           Dependency-free automated tests
docs/            Product and architecture decisions
packaging/       CachyOS/Arch packaging files
```

## Project principles

- Offline and local by default
- No telemetry
- Data-only Hotkey Packs; packs cannot execute code
- Source URLs and verification metadata for bundled packs
- User overrides take precedence over bundled defaults
- Platform claims are not considered verified until tested on Plasma Wayland

## Development status

Development and schema tests can run on any system with Python 3:

```bash
python -m unittest discover -s tests -v
```

The Qt/KWin integration must be built and verified on a Plasma 6 system. Build
instructions will be finalized after the first CachyOS integration test.
