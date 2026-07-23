#!/usr/bin/env python3
"""Inventory graphical applications installed on a Linux desktop.

The output intentionally excludes host names, user names, and command arguments.
It is suitable for deciding which Hotkey Packs a particular installation needs.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


FIELD_CODE = re.compile(r"^%[fFuUdDnNickvm]$")


def _desktop_id(applications_dir: Path, desktop_file: Path) -> str:
    relative = desktop_file.relative_to(applications_dir).as_posix()
    return relative.replace("/", "-")


def _read_desktop_entry(desktop_file: Path) -> dict[str, str] | None:
    parser = configparser.ConfigParser(
        interpolation=None,
        strict=False,
        delimiters=("=",),
        comment_prefixes=("#",),
    )
    parser.optionxform = str
    try:
        parser.read(desktop_file, encoding="utf-8")
    except (OSError, UnicodeError, configparser.Error):
        return None

    if not parser.has_section("Desktop Entry"):
        return None

    entry = dict(parser.items("Desktop Entry"))
    if entry.get("Type", "Application") != "Application":
        return None
    if entry.get("Hidden", "").lower() == "true":
        return None
    return entry


def _executable_from_exec(exec_line: str) -> str:
    if not exec_line:
        return ""
    try:
        tokens = shlex.split(exec_line, posix=True)
    except ValueError:
        tokens = exec_line.split()

    for token in tokens:
        if FIELD_CODE.match(token):
            continue
        if "=" in token and not token.startswith(("/", "./", "../")):
            key, _, _ = token.partition("=")
            if key.replace("_", "").isalnum():
                continue
        return Path(token).name
    return ""


def _package_owner(desktop_file: Path) -> str | None:
    if not shutil.which("pacman"):
        return None
    try:
        result = subprocess.run(
            ["pacman", "-Qqo", str(desktop_file)],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    owner = result.stdout.strip().splitlines()
    return owner[0] if owner else None


def scan_applications(
    data_roots: Iterable[Path],
    *,
    include_hidden_launchers: bool = False,
    include_package_owner: bool = False,
) -> list[dict[str, object]]:
    """Scan XDG data roots in priority order and return unique applications."""

    applications: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    for root in data_roots:
        applications_dir = root / "applications"
        if not applications_dir.is_dir():
            continue

        for desktop_file in sorted(applications_dir.rglob("*.desktop")):
            desktop_id = _desktop_id(applications_dir, desktop_file)
            if desktop_id in seen_ids:
                continue

            entry = _read_desktop_entry(desktop_file)
            if entry is None:
                continue
            if (
                not include_hidden_launchers
                and entry.get("NoDisplay", "").lower() == "true"
            ):
                continue

            seen_ids.add(desktop_id)
            record: dict[str, object] = {
                "desktop_id": desktop_id.removesuffix(".desktop"),
                "name": entry.get("Name", desktop_id.removesuffix(".desktop")),
                "generic_name": entry.get("GenericName", ""),
                "executable": _executable_from_exec(entry.get("Exec", "")),
                "startup_wm_class": entry.get("StartupWMClass", ""),
                "icon": entry.get("Icon", ""),
                "categories": [
                    value
                    for value in entry.get("Categories", "").split(";")
                    if value
                ],
                "origin": "user" if root == _user_data_root() else "system",
            }
            if include_package_owner:
                record["package"] = _package_owner(desktop_file)
            applications.append(record)

    return sorted(
        applications,
        key=lambda item: (
            str(item["name"]).casefold(),
            str(item["desktop_id"]).casefold(),
        ),
    )


def _user_data_root() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))


def xdg_data_roots() -> list[Path]:
    roots = [_user_data_root()]
    raw_system_roots = os.environ.get(
        "XDG_DATA_DIRS", "/usr/local/share:/usr/share"
    )
    roots.extend(Path(value) for value in raw_system_roots.split(":") if value)
    return roots


def _os_pretty_name() -> str:
    os_release = Path("/etc/os-release")
    if os_release.is_file():
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.partition("=")[2].strip().strip('"')
    return platform.platform()


def build_inventory(
    *,
    include_hidden_launchers: bool = False,
    include_package_owner: bool = False,
) -> dict[str, object]:
    applications = scan_applications(
        xdg_data_roots(),
        include_hidden_launchers=include_hidden_launchers,
        include_package_owner=include_package_owner,
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": {
            "operating_system": _os_pretty_name(),
            "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
            "session_type": os.environ.get("XDG_SESSION_TYPE", ""),
        },
        "application_count": len(applications),
        "applications": applications,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export installed Linux GUI applications for Hotkey Helper."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("hotkey-helper-inventory.json"),
        help="Output JSON path (default: hotkey-helper-inventory.json)",
    )
    parser.add_argument(
        "--include-hidden-launchers",
        action="store_true",
        help="Include launchers marked NoDisplay=true.",
    )
    parser.add_argument(
        "--include-package-owner",
        action="store_true",
        help="Ask pacman which package owns each desktop file.",
    )
    args = parser.parse_args()

    inventory = build_inventory(
        include_hidden_launchers=args.include_hidden_launchers,
        include_package_owner=args.include_package_owner,
    )
    args.output.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {inventory['application_count']} applications to "
        f"{args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
