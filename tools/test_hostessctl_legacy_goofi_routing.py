from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from tools.hostessctl.connectivity_data_protocols_zeromq import (
    resolve_goofi_bridge_root,
)


class HostessCtlLegacyGoofiRoutingTests(unittest.TestCase):
    def test_legacy_goofi_root_is_never_discovered_implicitly(self) -> None:
        self.assertIsNone(
            resolve_goofi_bridge_root(
                argparse.Namespace(zeromq_goofi_bridge_root="")
            )
        )

    def test_explicit_valid_legacy_goofi_root_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
            tools = root / "tools"
            tools.mkdir()
            (tools / "goofi_pair_to_gargoyle_pub.py").write_text(
                "# explicit legacy fixture\n",
                encoding="utf-8",
            )

            self.assertEqual(
                resolve_goofi_bridge_root(
                    argparse.Namespace(zeromq_goofi_bridge_root=str(root))
                ),
                root,
            )


if __name__ == "__main__":
    unittest.main()
