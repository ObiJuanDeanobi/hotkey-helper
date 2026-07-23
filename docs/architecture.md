# Hotkey Helper Architecture

## Status

Initial architecture for the CachyOS/KDE Plasma 6/Wayland implementation.
Decisions in this document are intended to keep the Dolphin vertical slice
small while preserving clean seams for future desktop integrations.

## Architectural goals

- Reliably associate the active Plasma window with a local Hotkey Pack.
- Preserve the last external application context while the user interacts with
  the helper.
- Support both overlay and reserved-edge presentation on Wayland.
- Keep pack parsing, validation, matching, and rendering deterministic and
  testable without a running desktop session.
- Perform all core operations locally and offline.
- Make community contributions data-only wherever possible.

## System overview

```text
KWin/Plasma active-window event
              |
              v
     Plasma context adapter
              |
              v
      Context state store  <---- ignores Hotkey Helper as an external context
              |
              v
     Deterministic matcher
              |
              v
 Pack loader + validator  <---- bundled packs + user packs
              |
              v
       Qt/QML panel UI
        |           |
 overlay mode   reserved-edge mode
```

Settings, global-shortcut handling, tray controls, and autostart management are
local supporting services around this pipeline.

## Technology baseline

- **UI and application runtime:** Qt 6 with QML.
- **Plasma integration:** KDE Frameworks APIs where they reduce unsupported
  desktop-specific behavior; Kirigami may be used for native visual components.
- **Active-window source:** a narrowly scoped KWin/Plasma 6 adapter suitable for
  Wayland, rather than X11 utilities such as `xdotool`.
- **Edge placement:** a Plasma-compatible Wayland layer-shell integration, with
  an adapter exposing overlay and reserved-edge policies to QML.
- **Storage:** JSON for packs and KDE/Qt local configuration for settings.
- **Testing:** unit tests for schema validation, precedence, matching, and
  context retention; a Plasma Wayland smoke test for desktop integration.

The desktop-facing APIs must be isolated behind interfaces. This prevents KWin
or layer-shell API changes from spreading into pack and UI logic and provides a
future path to other desktop environments without claiming support now.

## Component boundaries

### 1. Plasma context adapter

The adapter emits a normalized window observation whenever the active external
window changes:

```text
desktopFileId
windowClass
windowTitle
processName (when safely available)
```

Stable identifiers take priority. Window titles are display/debug metadata and
must not be the primary match mechanism because they change with document and
page content.

The concrete implementation should use supported KWin/Plasma mechanisms
available on Plasma 6 Wayland. If a KWin script is required, it is packaged with
the application and communicates through a narrow local IPC contract. That
contract accepts only normalized metadata and exposes no general command
execution.

### 2. Context state store

The store maintains:

- `activeObservation`: the latest window observation.
- `lastExternalContext`: the latest usable observation whose identity is not
  Hotkey Helper.
- `resolvedPackId`: the result of matching `lastExternalContext`.

An observation identifying Hotkey Helper may change UI focus state, but it must
not overwrite `lastExternalContext`. Therefore clicking, focusing, or scrolling
the panel continues to show the pack for the user's working application.

When focus moves to a different external application, the store immediately
updates context and requests a new match. An unmatched result is explicit; the
previous application's pack is not retained after a genuine external context
change.

### 3. Pack loader and validator

The loader discovers JSON files from two ordered sources:

1. Bundled/system packs installed with the application.
2. User packs in a documented XDG user-data location, such as
   `$XDG_DATA_HOME/hotkey-helper/packs`.

User packs have higher precedence when the stable pack identifier collides.
Precedence is deterministic and logged locally. A bad higher-priority pack is
reported as invalid and must not silently shadow a valid bundled pack.

Validation occurs before data enters the matcher or UI. At minimum it checks:

- Supported schema version.
- Required stable identifiers and display fields.
- Valid match arrays.
- Shortcut action, key, and category fields.
- Unique IDs where the schema requires them.
- Data-size and collection-count limits.
- Absence of executable fields or unsupported data types.

The parser treats packs as untrusted data. Loading a pack never evaluates code,
expands a shell expression, follows a command, or fetches a URL. Source URLs are
provenance text only and are never fetched during normal loading.

### 4. Deterministic application matcher

Matching priority is:

1. Exact normalized desktop file ID.
2. Exact normalized window class alias.
3. Exact normalized process alias, only when supplied reliably.

Title-pattern matching is excluded from the first vertical slice. Ambiguous
matches produce a diagnosable result and use an explicit deterministic
tie-breaker; they must not depend on filesystem enumeration order.

Normalization rules and precedence are shared by runtime code and pack
validation tests.

### 5. Panel UI

The QML UI consumes a view model, not raw pack JSON. The view model exposes the
resolved application, icon reference, categories, shortcuts, validation/error
state, visibility, presentation mode, edge, and transparency.

The panel:

- Starts hidden unless the user restores an explicitly supported preference.
- Accepts mouse clicks, focus, and scrolling while visible.
- Visually distinguishes keys from action labels.
- Provides an honest unmatched and invalid-pack state.
- Does not perform matching or pack parsing in QML.

### 6. Edge presentation adapter

One adapter presents two user-selectable policies:

- **Overlay:** anchor to the configured display edge with no exclusive zone.
- **Reserved space:** anchor to the edge and request an exclusive zone matching
  the visible panel width.

Transparency changes QML surface/background opacity rather than pack content.
Legibility constraints belong to the theme layer.

Reserved-edge behavior must be verified on the targeted Plasma 6 Wayland
version before it is generalized. If Plasma rejects or cannot honor the
exclusive zone in a specific environment, the application reports that
limitation and safely falls back to overlay rather than using X11-only hacks.

### 7. Global shortcut and tray controls

A KDE-compatible global shortcut action and a tray/status-notifier action invoke
the same `toggleVisibility()` application command. A configurable shortcut is
stored locally. Conflicts or registration failures are visible to the user and
do not disable the tray fallback.

The tray menu minimally provides:

- Show/Hide.
- Settings.
- Quit.

### 8. Settings and autostart

Settings are stored in the user's local configuration and include:

- Display edge.
- Overlay or reserved-space mode.
- Transparency.
- Global shortcut.
- Autostart enabled state.

Autostart is implemented using the user-level mechanism supported by the target
Plasma session, preferably an XDG autostart desktop entry. Toggling the setting
is idempotent and affects only the current user's configuration. Installation
does not enable autostart implicitly.

## Hotkey Pack contract

The canonical schema is versioned independently of the application. A minimal
conceptual pack contains:

```json
{
  "schemaVersion": 1,
  "id": "org.kde.dolphin",
  "name": "Dolphin",
  "packVersion": "1.0.0",
  "match": {
    "desktopFileIds": ["org.kde.dolphin"],
    "windowClasses": ["dolphin"]
  },
  "sources": [
    {
      "url": "https://docs.kde.org/",
      "verifiedFor": "Dolphin version documented by the pack"
    }
  ],
  "shortcuts": [
    {
      "id": "new-tab",
      "action": "New Tab",
      "keys": ["Ctrl+T"],
      "category": "Tabs"
    }
  ]
}
```

The formal JSON Schema is the authoritative contract once added. Examples in
documentation must be generated from or tested against it to avoid drift.

## Local data and trust boundaries

```text
Trusted application code
  |-- validates --> bundled JSON
  |-- validates --> user JSON (untrusted input)
  |-- reads ------> local settings
  |-- receives ---> constrained KWin window metadata
  `-- renders ----> local UI

No runtime cloud or catalog dependency
No telemetry
No pack code execution
No automatic source-URL retrieval
```

Pack errors and diagnostic identifiers may be logged locally. Window titles can
contain sensitive document names or URLs, so normal logs must omit them or
redact them by default.

## Dolphin vertical-slice implementation order

1. Define and test schema version 1.
2. Add a source-verified `org.kde.dolphin.json`.
3. Implement pack discovery, validation, precedence, and matching as a
   desktop-independent core.
4. Implement the Plasma context adapter and verify Dolphin identity on the
   target CachyOS system.
5. Connect the context store to a minimal scrollable QML panel.
6. Add tray and global-shortcut visibility controls.
7. Add overlay mode, then reserved-edge mode and transparency.
8. Add persistent settings and opt-in autostart.
9. Run automated core tests and a manual Plasma Wayland acceptance pass.

## Test strategy

### Automated

- Valid and malformed pack fixtures.
- Unsupported schema versions.
- User/bundled precedence, including invalid user overrides.
- Desktop ID and window-class normalization.
- Deterministic ambiguous-match behavior.
- Context retention when Hotkey Helper receives focus.
- Context replacement when another external application receives focus.
- Settings serialization and autostart-state idempotence where practical.

### Target-environment integration

- Dolphin detection under CachyOS KDE Plasma 6 Wayland.
- Panel toggling through both shortcut and tray.
- Scrolling/clicking without context loss.
- Overlay placement and reserved-edge behavior.
- Transparency and readability.
- Restart persistence.
- Fully disconnected startup and use.

The target-environment pass is required before claiming the Dolphin slice is
complete. Tests run elsewhere cannot establish KWin or layer-shell behavior on
the supported desktop.

## Architectural non-goals

- Cross-desktop abstraction implementations before the Plasma slice works.
- X11 compatibility shims in the first release.
- A network service, remote API, account system, or online catalog.
- Dynamic code plugins embedded in packs.
- Guessing shortcuts from window titles, menus, or undocumented heuristics.
- A database where versioned JSON and local settings are sufficient.
- Automatic mutation of an application's own shortcut configuration.
- Privileged system services or root-required runtime behavior.

## Open implementation questions

These are technical spikes, not unresolved product decisions:

- Which supported Plasma 6 API provides the most stable active-window metadata
  on the target CachyOS version.
- Whether the chosen layer-shell integration honors the desired exclusive zone
  consistently across the target multi-monitor configurations.
- The exact KDE Frameworks components used for the global shortcut and status
  notifier.
- The final open-source license and repository governance files before public
  release.

Each spike should preserve the interfaces described above even if its concrete
library changes.
