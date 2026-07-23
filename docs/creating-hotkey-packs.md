# Creating a Hotkey Pack

Hotkey Packs let Hotkey Helper support another application without changing
application code. Each pack is one UTF-8 JSON file in `packs/`.

## 1. Identify the application

On CachyOS, run the local inventory tool:

```bash
python tools/inventory_apps.py --include-package-owner
```

Use the resulting desktop ID as the primary match value. Window classes are
useful aliases, but window titles are not stable and must not be used for
matching.

## 2. Copy the starter structure

Use [the Dolphin pack](../packs/org.kde.dolphin.json) as a working example.
Choose a lowercase reverse-domain-style filename and matching `id`, such as
`org.kde.kate.json`.

Required top-level fields are:

- `schemaVersion`: currently `1`;
- `id`, `name`, `version`, and `description`;
- `license`;
- `match.desktopIds` and `match.windowClasses`;
- `metadata.homepage` and at least one source; and
- at least one shortcut.

The formal [JSON Schema](../schema/hotkey-pack-v1.schema.json) is the
authoritative format.

## 3. Source the shortcuts

Prefer the application's official manual, documentation site, or maintained
upstream source. Each source needs a stable ID, title, URL, and the date you
verified it.

Every shortcut references one source through `sourceId`. If a shortcut has a
surprising or destructive effect, add a short `notes` field.

Keep the first version useful and reviewable. A focused list of common
shortcuts is better than a large unverified dump.

## 4. Validate the pack

From the repository root:

```bash
python tools/validate_pack.py packs/path-to-your-pack.json
python -m unittest discover -s tests -v
```

The validator checks the schema, source references, identifier uniqueness, and
other safety rules without needing third-party Python packages.

## 5. Test matching

When the desktop application is available, confirm that at least one declared
desktop ID or window class matches what Plasma reports. Include the application
version, Plasma version, and Wayland test result in the pull request.

If you cannot test on Plasma Wayland, say so plainly. The pack can still be
reviewed, but it should not be described as target-environment verified.

## Pack licenses

Hotkey Packs are data rather than application code. New bundled packs should
normally declare `CC0-1.0`, allowing the shortcut data to be freely reused.
Only contribute data you have the right to submit.

## Security boundary

A pack may describe applications, matches, sources, categories, actions, and
key combinations. It may not contain scripts, shell commands, plugins,
download instructions, or executable code. Source URLs are provenance only and
are never fetched during normal pack loading.
