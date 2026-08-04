from __future__ import annotations

import unittest
from pathlib import Path

import _app_path  # noqa: F401 - repo-root unittest discovery bootstrap

from run_browser_smoke import snapshot_ref
from trusted_local_control_conformance.conformance import asset_receipt, find_quest_web_root


class BrowserEntrypointTests(unittest.TestCase):
    def test_product_asset_discovery_requires_one_unique_packaged_directory(self) -> None:
        self.assertIsNone(find_quest_web_root(Path("missing-quest-root")))

    def test_fixture_asset_receipt_is_explicitly_not_product(self) -> None:
        web_root = Path(__file__).resolve().parents[1] / "web"
        receipt = asset_receipt(web_root, role="hostess_fixture_assets")

        self.assertEqual(receipt["role"], "hostess_fixture_assets")
        self.assertEqual([item["name"] for item in receipt["files"]], ["index.html", "app.js", "styles.css"])
        self.assertTrue(all(item["sha256"] for item in receipt["files"]))

    def test_snapshot_ref_selects_only_an_enabled_exact_control(self) -> None:
        snapshot = """
- textbox "Pairing code" [ref=e2]
- button "Select" [disabled] [ref=e7]
- button "Select" [ref=e9]
- button "Play something else" [ref=e10]
- button "Play" [ref=e11]
"""
        self.assertEqual(snapshot_ref(snapshot, role="textbox", name="Pairing code"), "e2")
        self.assertEqual(
            snapshot_ref(
                snapshot,
                role="button",
                name="Select",
                require_enabled=True,
            ),
            "e9",
        )
        self.assertEqual(snapshot_ref(snapshot, role="button", name="Play"), "e11")
        self.assertIsNone(snapshot_ref(snapshot, role="button", name="Pause"))


if __name__ == "__main__":
    unittest.main()
