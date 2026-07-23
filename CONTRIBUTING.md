# Contributing to Hotkey Helper

Thanks for helping make Linux keyboard workflows easier to discover.

Hotkey Helper is at an early stage, so small and focused contributions are the
most useful. A pull request should solve one clear problem and avoid unrelated
formatting or architectural changes.

## Good ways to contribute

- Add or improve a Hotkey Pack.
- Verify shortcuts against current official application documentation.
- Test application identities on CachyOS with KDE Plasma 6 and Wayland.
- Improve pack validation, matching, accessibility, or documentation.
- Report focused-window and panel-placement behavior from a real Plasma setup.

## Before opening a pull request

1. Read the [product specification](docs/product-spec.md) and
   [architecture](docs/architecture.md).
2. Keep core functionality offline and local.
3. Do not add telemetry, runtime web requests, or executable pack fields.
4. Add or update tests for behavior changes.
5. Run:

   ```bash
   python -m unittest discover -s tests -v
   python tools/validate_pack.py packs
   ```

6. Describe what you tested and whether it was tested on Plasma Wayland.

## Contributing a Hotkey Pack

Read [Creating a Hotkey Pack](docs/creating-hotkey-packs.md). Packs should:

- use a stable reverse-domain-style identifier;
- match stable desktop IDs or window classes, not window titles;
- cite authoritative shortcut sources;
- include a recent verification date;
- contain common, useful shortcuts rather than every obscure command;
- use a permissive data license, preferably `CC0-1.0`; and
- pass the repository validator.

Do not copy shortcut lists from an incompatible license or submit shortcuts
that have only been guessed.

## Commit and pull request style

Use a short imperative summary such as `Add Kate Hotkey Pack` or
`Improve desktop ID normalization`. Explain user-visible effects, validation,
and target-environment testing in the pull request description.

By contributing, you agree that your contribution may be distributed under the
project license and that any Hotkey Pack data is available under the license
declared in that pack.
