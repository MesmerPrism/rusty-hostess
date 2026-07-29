"""Optional Playwright CLI smoke for already-packaged Quest web assets."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from trusted_local_control_conformance.conformance import (
    asset_receipt,
    find_quest_web_root,
)
from trusted_local_control_conformance.contract import (
    validate_quest_registry,
    validate_web_assets,
)
from trusted_local_control_conformance.loopback_server import LoopbackTestServer


APP_ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quest-root", type=Path)
    parser.add_argument(
        "--fixture-assets",
        action="store_true",
        help="explicitly smoke Hostess fixture assets; never a product-asset claim",
    )
    args = parser.parse_args()

    cli = shutil.which("playwright-cli")
    if cli is None:
        print("SKIP: playwright-cli is not installed; no package or browser was downloaded")
        return 77

    if args.quest_root is None and not args.fixture_assets:
        parser.error("--quest-root is required for a product browser claim (or use --fixture-assets)")

    if args.quest_root is not None:
        registry_issues = validate_quest_registry(args.quest_root)
        web_root = find_quest_web_root(args.quest_root)
        role = "quest_packaged_assets"
        if registry_issues:
            print(json.dumps({"status": "fail", "registry_issues": registry_issues}, indent=2))
            return 1
        if web_root is None:
            print("FAIL: no unique Quest packaged index.html/app.js/styles.css directory")
            return 1
    else:
        web_root = APP_ROOT / "web"
        role = "hostess_fixture_assets"

    asset_issues = validate_web_assets(web_root)
    if asset_issues:
        print(json.dumps({"status": "fail", "asset_issues": asset_issues}, indent=2))
        return 1

    server = LoopbackTestServer(
        explicitly_enabled=True,
        bind_host="127.0.0.1",
        bind_port=0,
        web_root=web_root,
    )
    commands: list[list[str]] = []
    try:
        server.start()
        commands.append([cli, "open", server.url])
        commands.append([cli, "snapshot"])
        open_result = subprocess.run(
            commands[0],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        snapshot_result = subprocess.run(
            commands[1],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        subprocess.run(
            [cli, "close"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    finally:
        server.close()

    snapshot = snapshot_result.stdout + snapshot_result.stderr
    status = (
        "pass"
        if open_result.returncode == 0
        and snapshot_result.returncode == 0
        and snapshot.strip()
        else "fail"
    )
    report = {
        "schema": "rusty.hostess.trusted_local_control.browser_smoke.v1",
        "status": status,
        "browser": "playwright-cli",
        "listener": {"host": "127.0.0.1", "requested_port": 0},
        "asset_receipt": asset_receipt(web_root, role=role),
        "product_asset_claim": role == "quest_packaged_assets",
        "network_actions": {
            "lan_listener": False,
            "mdns": False,
            "package_install": False,
            "browser_download": False,
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
