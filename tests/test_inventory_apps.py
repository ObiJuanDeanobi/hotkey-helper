import tempfile
import unittest
from pathlib import Path

from tools.inventory_apps import scan_applications


class InventoryTests(unittest.TestCase):
    def _write_entry(self, root: Path, filename: str, body: str) -> Path:
        target = root / "applications" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return target

    def test_scans_visible_application_and_sanitizes_exec(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_entry(
                root,
                "org.kde.dolphin.desktop",
                """[Desktop Entry]
Type=Application
Name=Dolphin
GenericName=File Manager
Exec=dolphin %U
Icon=org.kde.dolphin
Categories=Qt;KDE;System;FileTools;
StartupWMClass=dolphin
""",
            )

            applications = scan_applications([root])

            self.assertEqual(len(applications), 1)
            self.assertEqual(applications[0]["desktop_id"], "org.kde.dolphin")
            self.assertEqual(applications[0]["executable"], "dolphin")
            self.assertEqual(applications[0]["startup_wm_class"], "dolphin")
            self.assertEqual(
                applications[0]["categories"],
                ["Qt", "KDE", "System", "FileTools"],
            )

    def test_skips_hidden_and_no_display_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_entry(
                root,
                "hidden.desktop",
                "[Desktop Entry]\nType=Application\nName=Hidden\nHidden=true\n",
            )
            self._write_entry(
                root,
                "internal.desktop",
                "[Desktop Entry]\nType=Application\nName=Internal\nNoDisplay=true\n",
            )

            self.assertEqual(scan_applications([root]), [])
            included = scan_applications(
                [root], include_hidden_launchers=True
            )
            self.assertEqual([item["name"] for item in included], ["Internal"])

    def test_first_xdg_root_wins_for_duplicate_desktop_id(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_root = Path(first)
            second_root = Path(second)
            filename = "example.desktop"
            self._write_entry(
                first_root,
                filename,
                "[Desktop Entry]\nType=Application\nName=User Version\n",
            )
            self._write_entry(
                second_root,
                filename,
                "[Desktop Entry]\nType=Application\nName=System Version\n",
            )

            applications = scan_applications([first_root, second_root])

            self.assertEqual(len(applications), 1)
            self.assertEqual(applications[0]["name"], "User Version")


if __name__ == "__main__":
    unittest.main()
