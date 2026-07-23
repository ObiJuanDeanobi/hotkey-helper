#!/usr/bin/env python3
"""Validate data-only Hotkey Helper v1 JSON packs without dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


PACK_ID_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
ITEM_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

TOP_LEVEL_FIELDS = {
    "$schema",
    "schemaVersion",
    "id",
    "name",
    "version",
    "description",
    "license",
    "match",
    "metadata",
    "shortcuts",
}
MATCH_FIELDS = {"desktopIds", "windowClasses"}
METADATA_FIELDS = {"homepage", "sources"}
SOURCE_FIELDS = {"id", "title", "url", "verifiedAt", "applicationVersion"}
SHORTCUT_FIELDS = {"id", "action", "keys", "category", "sourceId", "notes"}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _canonical(value: str) -> str:
    return " ".join(value.split()).casefold()


def _canonical_keys(value: str) -> str:
    return "+".join(part.strip().casefold() for part in value.split("+"))


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _require_object(
    value: Any, path: str, issues: list[ValidationIssue]
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        issues.append(ValidationIssue(path, "must be an object"))
        return None
    return value


def _require_string(
    obj: dict[str, Any],
    key: str,
    path: str,
    issues: list[ValidationIssue],
) -> str | None:
    value = obj.get(key)
    field_path = f"{path}.{key}"
    if not isinstance(value, str) or not value.strip():
        issues.append(ValidationIssue(field_path, "must be a non-empty string"))
        return None
    return value


def _reject_unknown_fields(
    obj: dict[str, Any],
    allowed: set[str],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    for key in sorted(set(obj) - allowed):
        issues.append(
            ValidationIssue(
                f"{path}.{key}",
                "is not allowed; packs are data-only and use a closed schema",
            )
        )


def _validate_string_list(
    obj: dict[str, Any],
    key: str,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    field_path = f"{path}.{key}"
    values = obj.get(key)
    if not isinstance(values, list) or not values:
        issues.append(ValidationIssue(field_path, "must be a non-empty array"))
        return

    seen: set[str] = set()
    for index, value in enumerate(values):
        item_path = f"{field_path}[{index}]"
        if not isinstance(value, str) or not value.strip():
            issues.append(ValidationIssue(item_path, "must be a non-empty string"))
            continue
        normalized = _canonical(value)
        if normalized in seen:
            issues.append(ValidationIssue(item_path, f"duplicates {value!r}"))
        seen.add(normalized)


def validate_pack(pack: Any, *, path: str = "$") -> list[ValidationIssue]:
    """Return every validation issue found in one decoded pack."""
    issues: list[ValidationIssue] = []
    root = _require_object(pack, path, issues)
    if root is None:
        return issues
    _reject_unknown_fields(root, TOP_LEVEL_FIELDS, path, issues)

    if root.get("schemaVersion") != 1:
        issues.append(ValidationIssue(f"{path}.schemaVersion", "must equal 1"))

    pack_id = _require_string(root, "id", path, issues)
    if pack_id and not PACK_ID_RE.fullmatch(pack_id):
        issues.append(
            ValidationIssue(
                f"{path}.id",
                "must contain lowercase letters and numbers separated by '.', '_' or '-'",
            )
        )

    _require_string(root, "name", path, issues)
    version = _require_string(root, "version", path, issues)
    if version and not SEMVER_RE.fullmatch(version):
        issues.append(
            ValidationIssue(f"{path}.version", "must use MAJOR.MINOR.PATCH")
        )
    _require_string(root, "description", path, issues)
    _require_string(root, "license", path, issues)

    match = _require_object(root.get("match"), f"{path}.match", issues)
    if match is not None:
        _reject_unknown_fields(match, MATCH_FIELDS, f"{path}.match", issues)
        _validate_string_list(match, "desktopIds", f"{path}.match", issues)
        _validate_string_list(match, "windowClasses", f"{path}.match", issues)

    source_ids: set[str] = set()
    metadata = _require_object(root.get("metadata"), f"{path}.metadata", issues)
    if metadata is not None:
        _reject_unknown_fields(metadata, METADATA_FIELDS, f"{path}.metadata", issues)
        homepage = _require_string(metadata, "homepage", f"{path}.metadata", issues)
        if homepage and not _is_http_url(homepage):
            issues.append(
                ValidationIssue(
                    f"{path}.metadata.homepage", "must be an HTTP or HTTPS URL"
                )
            )

        sources = metadata.get("sources")
        if not isinstance(sources, list) or not sources:
            issues.append(
                ValidationIssue(
                    f"{path}.metadata.sources",
                    "must contain at least one source URL",
                )
            )
        else:
            for index, value in enumerate(sources):
                source_path = f"{path}.metadata.sources[{index}]"
                source = _require_object(value, source_path, issues)
                if source is None:
                    continue
                _reject_unknown_fields(source, SOURCE_FIELDS, source_path, issues)
                source_id = _require_string(source, "id", source_path, issues)
                if source_id:
                    if not ITEM_ID_RE.fullmatch(source_id):
                        issues.append(
                            ValidationIssue(
                                f"{source_path}.id",
                                "must be a lowercase kebab-case identifier",
                            )
                        )
                    normalized_id = source_id.casefold()
                    if normalized_id in source_ids:
                        issues.append(
                            ValidationIssue(
                                f"{source_path}.id",
                                f"duplicates source id {source_id!r}",
                            )
                        )
                    source_ids.add(normalized_id)
                _require_string(source, "title", source_path, issues)
                url = _require_string(source, "url", source_path, issues)
                if url and not _is_http_url(url):
                    issues.append(
                        ValidationIssue(
                            f"{source_path}.url", "must be an HTTP or HTTPS URL"
                        )
                    )
                verified_at = _require_string(
                    source, "verifiedAt", source_path, issues
                )
                if verified_at:
                    try:
                        date.fromisoformat(verified_at)
                    except ValueError:
                        issues.append(
                            ValidationIssue(
                                f"{source_path}.verifiedAt",
                                "must be a real date in YYYY-MM-DD format",
                            )
                        )

    shortcuts = root.get("shortcuts")
    if not isinstance(shortcuts, list) or not shortcuts:
        issues.append(
            ValidationIssue(f"{path}.shortcuts", "must be a non-empty array")
        )
        return issues

    shortcut_ids: set[str] = set()
    actions: set[str] = set()
    keys: dict[str, str] = {}
    for index, value in enumerate(shortcuts):
        shortcut_path = f"{path}.shortcuts[{index}]"
        shortcut = _require_object(value, shortcut_path, issues)
        if shortcut is None:
            continue
        _reject_unknown_fields(shortcut, SHORTCUT_FIELDS, shortcut_path, issues)

        shortcut_id = _require_string(shortcut, "id", shortcut_path, issues)
        if shortcut_id:
            if not ITEM_ID_RE.fullmatch(shortcut_id):
                issues.append(
                    ValidationIssue(
                        f"{shortcut_path}.id",
                        "must be a lowercase kebab-case identifier",
                    )
                )
            normalized_id = shortcut_id.casefold()
            if normalized_id in shortcut_ids:
                issues.append(
                    ValidationIssue(
                        f"{shortcut_path}.id",
                        f"duplicates shortcut id {shortcut_id!r}",
                    )
                )
            shortcut_ids.add(normalized_id)

        action = _require_string(shortcut, "action", shortcut_path, issues)
        if action:
            normalized_action = _canonical(action)
            if normalized_action in actions:
                issues.append(
                    ValidationIssue(
                        f"{shortcut_path}.action",
                        f"duplicates action {action!r}",
                    )
                )
            actions.add(normalized_action)

        key_values = shortcut.get("keys")
        if not isinstance(key_values, list) or not key_values:
            issues.append(
                ValidationIssue(
                    f"{shortcut_path}.keys", "must be a non-empty array"
                )
            )
        else:
            for key_index, key_value in enumerate(key_values):
                key_path = f"{shortcut_path}.keys[{key_index}]"
                if not isinstance(key_value, str) or not key_value.strip():
                    issues.append(
                        ValidationIssue(key_path, "must be a non-empty string")
                    )
                    continue
                normalized_key = _canonical_keys(key_value)
                if normalized_key in keys:
                    issues.append(
                        ValidationIssue(
                            key_path,
                            f"duplicates key binding {key_value!r} used by {keys[normalized_key]!r}",
                        )
                    )
                elif action:
                    keys[normalized_key] = action

        _require_string(shortcut, "category", shortcut_path, issues)
        source_id = _require_string(shortcut, "sourceId", shortcut_path, issues)
        if source_id and source_id.casefold() not in source_ids:
            issues.append(
                ValidationIssue(
                    f"{shortcut_path}.sourceId",
                    f"references unknown source {source_id!r}",
                )
            )

    return issues


def load_and_validate(path: Path) -> tuple[dict[str, Any] | None, list[ValidationIssue]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            pack = json.load(handle)
    except OSError as error:
        return None, [ValidationIssue(str(path), f"could not read file: {error}")]
    except json.JSONDecodeError as error:
        return None, [
            ValidationIssue(
                str(path),
                f"invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}",
            )
        ]

    return pack if isinstance(pack, dict) else None, validate_pack(pack, path=str(path))


def validate_paths(paths: Iterable[Path]) -> list[ValidationIssue]:
    """Validate files and reject duplicate pack IDs across the collection."""
    issues: list[ValidationIssue] = []
    pack_ids: dict[str, Path] = {}
    for path in paths:
        pack, pack_issues = load_and_validate(path)
        issues.extend(pack_issues)
        if pack is None:
            continue
        pack_id = pack.get("id")
        if not isinstance(pack_id, str):
            continue
        normalized_id = pack_id.casefold()
        if normalized_id in pack_ids:
            issues.append(
                ValidationIssue(
                    f"{path}.id",
                    f"duplicates pack id {pack_id!r} from {pack_ids[normalized_id]}",
                )
            )
        else:
            pack_ids[normalized_id] = path
    return issues


def _expand_paths(values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_dir():
            paths.extend(sorted(path.glob("*.json")))
        else:
            paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        help="JSON pack files or directories containing JSON pack files",
    )
    args = parser.parse_args(argv)
    paths = _expand_paths(args.paths)
    if not paths:
        parser.error("no JSON packs found")

    issues = validate_paths(paths)
    if issues:
        for issue in issues:
            print(f"ERROR {issue}", file=sys.stderr)
        print(
            f"Validation failed: {len(issues)} issue(s) in {len(paths)} pack(s).",
            file=sys.stderr,
        )
        return 1

    print(f"Validated {len(paths)} pack(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
