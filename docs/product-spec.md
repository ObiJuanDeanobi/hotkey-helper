# Hotkey Helper Product Specification

## Product summary

Hotkey Helper is a small desktop companion that shows useful keyboard shortcuts
for the application the user is currently working in. It sits at a configurable
screen edge, can be revealed or hidden with a global shortcut or tray icon, and
uses simple community-maintained JSON "Hotkey Packs."

The first supported environment is CachyOS running KDE Plasma 6 on Wayland. The
project will be open source and freely available on GitHub.

## Problem

Linux desktop applications often expose substantial functionality through
keyboard shortcuts, but users are expected to already know those shortcuts or
look them up. Existing shortcut references are usually disconnected from the
user's current task, and application menus do not consistently surface the most
useful commands.

Hotkey Helper reduces that friction by presenting a concise, contextual cheat
sheet for the currently active application.

## Product principles

- Local first: normal operation requires no account, cloud service, telemetry,
  or network connection.
- Contextual: the displayed pack follows the user's active application.
- Unobtrusive: the helper remains hidden until the user asks for it.
- Approachable: users can install or author packs without writing application
  code.
- Verifiable: bundled shortcuts include human-readable provenance and should be
  checked against authoritative application documentation.
- Community friendly: packs and source code are reviewable and contribution
  workflows are documented.

## Locked product decisions

1. The initial platform is CachyOS with KDE Plasma 6 on Wayland.
2. The application is open source, free to use, and designed for publication on
   GitHub.
3. Hotkey Packs are local, data-only JSON files.
4. The user can choose between:
   - **Overlay mode**, which draws above the current application without
     changing its usable screen area.
   - **Reserved-space mode**, which reserves an edge region so ordinary
     application windows do not sit underneath the helper.
5. Panel transparency is user configurable.
6. The panel is shown or hidden by a configurable global hotkey or its system
   tray control. It is not required to remain visible merely because a
   recognized application has focus.
7. The visible panel accepts mouse clicks and scrolling. Interacting with
   Hotkey Helper retains the last non-Hotkey-Helper application as its context,
   so clicking the panel does not replace the useful pack.
8. All core functionality and packs operate offline and remain local.
9. Launching Hotkey Helper automatically with the Plasma session is an optional
   user setting.

## Target users

- People moving to Linux who are learning keyboard-driven workflows.
- Existing Plasma users learning an unfamiliar application.
- Power users who want a compact, editable reference for infrequently used
  shortcuts.
- Community contributors who want to add support for applications without
  changing Hotkey Helper's source code.

## Core user experience

### Context selection

Hotkey Helper observes the active window and resolves it to an application
identity. It selects the best matching installed Hotkey Pack. When the helper
itself receives focus, it continues using the most recent valid external
application identity.

If no pack matches, the panel shows a small, useful empty state identifying the
detected application and offering the local pack-creation/import path when that
feature is available. It must not silently display a pack for a different
application.

### Showing and hiding

- A configurable global shortcut toggles the panel.
- A tray icon exposes show/hide and settings controls.
- The chosen visibility state persists for the current session.
- Showing the panel does not require an internet connection.

### Viewing shortcuts

The panel displays the matched application name and icon, then groups shortcuts
by category. Users can scroll through a long list and use panel controls without
losing the external application context. Shortcut keys must be visually distinct
from action names and readable at every supported transparency setting.

### Display behavior

Users choose the screen edge, overlay or reserved-space behavior, and panel
transparency. Settings survive application restarts. Multi-monitor behavior
beyond a sensible single-panel default can be refined after the first vertical
slice.

### Autostart

Users may enable or disable startup with their Plasma session. Installation must
not force autostart without a user choice.

## Hotkey Packs

A Hotkey Pack is a UTF-8 JSON file containing:

- A schema version and stable pack identifier.
- Application display metadata.
- Deterministic match identifiers, such as desktop file IDs and window classes.
- Pack version and shortcut-source provenance.
- Categorized action names and key combinations.

Packs contain data only. They cannot include or invoke scripts, shell commands,
plugins, or executable code. Invalid packs are rejected with an actionable local
error and do not prevent valid packs from loading.

Bundled packs provide known-good coverage. User-installed packs live in a
documented user-data directory and can override a bundled pack with the same
stable identifier. Pack import, editing, validation, and contribution should not
require C++, QML, or knowledge of the application's internals.

## Application coverage

The long-term initial catalog goal is coverage for the default applications
actually present in the user's CachyOS installation. Installed-application
inventory and Hotkey Pack content are separate concerns:

- The inventory determines which applications are installed.
- A verified bundled or user-provided pack supplies their shortcuts.

Hotkey Helper must not claim that installed applications automatically expose
complete, reliable shortcut data. Where supported, later releases may layer
locally configured shortcuts over pack defaults.

## MVP vertical slice: Dolphin

The first implementation milestone is one complete path for KDE Dolphin.

### Acceptance criteria

1. Hotkey Helper launches successfully in a CachyOS KDE Plasma 6 Wayland
   session without network access.
2. Focusing a Dolphin window yields a stable Dolphin application identity.
3. The identity deterministically matches the bundled
   `org.kde.dolphin.json` pack.
4. The panel displays Dolphin's name and a small set of categorized, verified
   shortcuts from that pack.
5. The global shortcut and tray control can each show and hide the panel.
6. The user can click controls and scroll the panel while it continues to show
   Dolphin shortcuts.
7. Switching from Dolphin to another external application updates the context;
   if that application has no pack, an honest unmatched state is shown.
8. Overlay mode does not reserve desktop space.
9. Reserved-space mode reserves the configured screen edge, subject to the
   capabilities of Plasma 6's supported Wayland integration.
10. Transparency changes are visible immediately and preserve legibility.
11. Overlay/reserved mode, edge, transparency, global shortcut, and autostart
    preferences persist across restarts.
12. Enabling and disabling autostart respectively creates and removes the
    user-level startup configuration.
13. A malformed pack produces a clear validation error and cannot crash the
    application or replace the valid Dolphin pack.
14. Automated tests validate the Dolphin pack and its match behavior.

## Post-slice priorities

After the Dolphin slice is reliable:

1. Inventory the default applications in the target CachyOS installation.
2. Add verified packs in small, reviewable groups.
3. Add a local pack-creation and import workflow.
4. Add pack schema documentation, contribution templates, and CI validation.
5. Package the application for convenient installation on CachyOS/Arch Linux.
6. Evaluate locally configured shortcut overrides where applications expose
   them reliably.

## Non-goals for the first release

- Supporting GNOME, other desktop environments, X11, Windows, or macOS.
- A cloud account, online pack marketplace, automatic network downloads,
  synchronization, analytics, or telemetry.
- Scraping arbitrary websites or application menus to fabricate shortcut
  packs.
- Perfect automatic extraction of live shortcuts from every application.
- Running code supplied by a Hotkey Pack.
- Replacing an application's menus, command palette, or built-in shortcut
  configuration UI.
- Guaranteeing support for every installed application before the Dolphin
  vertical slice is complete.
- Complex multi-monitor placement policies or simultaneous panels on every
  display.
- Solving every distribution's packaging format in the initial milestone.

## Definition of first-release success

The product succeeds when a new Plasma user can install it, focus a supported
application, reveal the panel, and learn useful verified shortcuts without
configuration, an account, or network access—and when a contributor can add
another application by contributing a valid JSON pack.
