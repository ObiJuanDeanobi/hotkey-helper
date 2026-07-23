from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate_pack.py"
SPEC = importlib.util.spec_from_file_location("validate_pack", VALIDATOR_PATH)
assert SPEC and SPEC.loader
validate_pack = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_pack
SPEC.loader.exec_module(validate_pack)


def load_dolphin_pack() -> dict:
    with (ROOT / "packs" / "org.kde.dolphin.json").open(
        "r", encoding="utf-8"
    ) as handle:
        return json.load(handle)


class PackValidationTests(unittest.TestCase):
    def assert_issue_contains(self, pack: dict, text: str) -> None:
        messages = [str(issue) for issue in validate_pack.validate_pack(pack)]
        self.assertTrue(
            any(text in message for message in messages),
            f"{text!r} not found in issues: {messages}",
        )

    def test_starter_dolphin_pack_is_valid(self) -> None:
        self.assertEqual([], validate_pack.validate_pack(load_dolphin_pack()))

    def test_requires_supported_schema_version(self) -> None:
        pack = load_dolphin_pack()
        pack["schemaVersion"] = 2
        self.assert_issue_contains(pack, "schemaVersion")

    def test_requires_source_url(self) -> None:
        pack = load_dolphin_pack()
        pack["metadata"]["sources"][0]["url"] = ""
        self.assert_issue_contains(pack, "sources[0].url")

    def test_rejects_non_http_source_url(self) -> None:
        pack = load_dolphin_pack()
        pack["metadata"]["sources"][0]["url"] = "file:///tmp/source.html"
        self.assert_issue_contains(pack, "must be an HTTP or HTTPS URL")

    def test_rejects_duplicate_shortcut_id(self) -> None:
        pack = load_dolphin_pack()
        duplicate = copy.deepcopy(pack["shortcuts"][0])
        duplicate["action"] = "Another Action"
        duplicate["keys"] = ["Meta+9"]
        pack["shortcuts"].append(duplicate)
        self.assert_issue_contains(pack, "duplicates shortcut id")

    def test_rejects_duplicate_action_case_insensitively(self) -> None:
        pack = load_dolphin_pack()
        duplicate = copy.deepcopy(pack["shortcuts"][0])
        duplicate["id"] = "another-id"
        duplicate["action"] = "  NEW   window "
        duplicate["keys"] = ["Meta+9"]
        pack["shortcuts"].append(duplicate)
        self.assert_issue_contains(pack, "duplicates action")

    def test_rejects_duplicate_keys_with_spacing_and_case_changes(self) -> None:
        pack = load_dolphin_pack()
        duplicate = copy.deepcopy(pack["shortcuts"][0])
        duplicate["id"] = "another-id"
        duplicate["action"] = "Another Action"
        duplicate["keys"] = [" ctrl + n "]
        pack["shortcuts"].append(duplicate)
        self.assert_issue_contains(pack, "duplicates key binding")

    def test_rejects_duplicate_source_id(self) -> None:
        pack = load_dolphin_pack()
        duplicate = copy.deepcopy(pack["metadata"]["sources"][0])
        pack["metadata"]["sources"].append(duplicate)
        self.assert_issue_contains(pack, "duplicates source id")

    def test_rejects_unknown_source_reference(self) -> None:
        pack = load_dolphin_pack()
        pack["shortcuts"][0]["sourceId"] = "missing-source"
        self.assert_issue_contains(pack, "references unknown source")

    def test_rejects_executable_or_unknown_fields(self) -> None:
        pack = load_dolphin_pack()
        pack["script"] = "rm -rf /"
        self.assert_issue_contains(pack, "data-only and use a closed schema")

    def test_rejects_duplicate_pack_ids_across_files(self) -> None:
        pack = load_dolphin_pack()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            first.write_text(json.dumps(pack), encoding="utf-8")
            second.write_text(json.dumps(pack), encoding="utf-8")
            issues = validate_pack.validate_paths([first, second])
        self.assertTrue(
            any("duplicates pack id" in str(issue) for issue in issues),
            issues,
        )


if __name__ == "__main__":
    unittest.main()
