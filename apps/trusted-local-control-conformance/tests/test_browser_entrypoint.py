from __future__ import annotations

import unittest
from pathlib import Path

import _app_path  # noqa: F401 - repo-root unittest discovery bootstrap

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


if __name__ == "__main__":
    unittest.main()
