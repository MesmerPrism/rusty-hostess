"""Optional real-browser flow over committed Quest packaged assets."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import time
import uuid
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
_REF = re.compile(r'\b(?P<role>textbox|button) "(?P<name>[^"]+)"(?P<attrs>[^\r\n]*)\[ref=(?P<ref>e\d+)\]')


def snapshot_ref(
    snapshot: str,
    *,
    role: str,
    name: str,
    require_enabled: bool = False,
) -> str | None:
    """Return one exact accessibility ref from a fresh CLI snapshot."""
    matches = [
        match
        for match in _REF.finditer(snapshot)
        if match.group("role") == role
        and match.group("name") == name
        and (not require_enabled or "disabled" not in match.group("attrs"))
    ]
    return matches[0].group("ref") if matches else None


def _run_cli(
    cli: str,
    session: str,
    arguments: list[str],
    *,
    cwd: Path,
    timeout: int = 30,
) -> str:
    result = subprocess.run(
        [cli, f"-s={session}", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(
            f"playwright-cli {arguments[0]} failed with exit code "
            f"{result.returncode}: {output.strip()}"
        )
    return output


def _snapshot_until(
    cli: str,
    session: str,
    cwd: Path,
    required: tuple[str, ...],
) -> str:
    latest = ""
    for _ in range(10):
        latest = _run_cli(cli, session, ["snapshot"], cwd=cwd)
        if all(value in latest for value in required):
            return latest
        time.sleep(0.1)
    raise RuntimeError(f"browser state did not expose {required}: {latest.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quest-root", type=Path)
    parser.add_argument(
        "--fixture-assets",
        action="store_true",
        help="explicitly smoke Hostess fixture assets; never a product-asset claim",
    )
    parser.add_argument(
        "--browser",
        choices=("msedge", "chrome"),
        default="msedge",
        help="an already-installed Windows browser; no browser is downloaded",
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
        auto_apply_callbacks=True,
        web_root=web_root,
    )
    session = f"trusted-local-http-{uuid.uuid4().hex}"
    failure: str | None = None
    flow: list[str] = []
    selected_video: str | None = None
    final_playback_state: str | None = None
    console_errors: list[str] | None = None

    with tempfile.TemporaryDirectory(prefix="trusted-local-http-browser-") as temporary:
        browser_cwd = Path(temporary)
        try:
            server.start()
            _run_cli(
                cli,
                session,
                ["open", server.url, "--browser", args.browser],
                cwd=browser_cwd,
            )
            initial = _snapshot_until(
                cli,
                session,
                browser_cwd,
                ("Quest video control", "Pairing code", "Pair"),
            )
            pairing_ref = snapshot_ref(initial, role="textbox", name="Pairing code")
            pair_ref = snapshot_ref(initial, role="button", name="Pair")
            if pairing_ref is None or pair_ref is None:
                raise RuntimeError("fresh snapshot did not expose the pairing controls")
            _run_cli(
                cli,
                session,
                ["fill", pairing_ref, server.fixture.pairing_code],
                cwd=browser_cwd,
            )
            _run_cli(cli, session, ["click", pair_ref], cwd=browser_cwd)
            flow.append("pair")

            paired = _snapshot_until(
                cli,
                session,
                browser_cwd,
                ("Connected", "Synthetic grid", "Synthetic blue", "paused"),
            )
            select_ref = snapshot_ref(
                paired,
                role="button",
                name="Select",
                require_enabled=True,
            )
            if select_ref is None:
                raise RuntimeError("paired state did not expose an enabled Select control")
            _run_cli(cli, session, ["click", select_ref], cwd=browser_cwd)
            selected = _snapshot_until(
                cli,
                session,
                browser_cwd,
                ("synthetic-blue-2s", "paused"),
            )
            if "Playing" in selected:
                raise RuntimeError("select_video incorrectly started playback")
            selected_video = "synthetic-blue-2s"
            flow.append("select_video")

            play_ref = snapshot_ref(
                selected,
                role="button",
                name="Play",
                require_enabled=True,
            )
            if play_ref is None:
                raise RuntimeError("selected state did not expose an enabled Play control")
            _run_cli(cli, session, ["click", play_ref], cwd=browser_cwd)
            playing = _snapshot_until(
                cli,
                session,
                browser_cwd,
                ("synthetic-blue-2s", "Playing"),
            )
            flow.append("play")

            pause_ref = snapshot_ref(
                playing,
                role="button",
                name="Pause",
                require_enabled=True,
            )
            if pause_ref is None:
                raise RuntimeError("playing state did not expose an enabled Pause control")
            _run_cli(cli, session, ["click", pause_ref], cwd=browser_cwd)
            _snapshot_until(
                cli,
                session,
                browser_cwd,
                ("synthetic-blue-2s", "paused"),
            )
            flow.append("pause")
            final_playback_state = "paused"
            raw_console = _run_cli(
                cli,
                session,
                ["console", "error"],
                cwd=browser_cwd,
            ).strip()
            if "No console messages" in raw_console:
                console_errors = []
            elif (
                "Total messages: 1 (Errors: 1, Warnings: 0)" in raw_console
                and "favicon.ico" in raw_console
                and "404 (Not Found)" in raw_console
            ):
                console_errors = ["favicon-404"]
            else:
                raise RuntimeError(f"unexpected browser console errors: {raw_console}")
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            failure = str(error)
        finally:
            try:
                _run_cli(cli, session, ["close"], cwd=browser_cwd, timeout=10)
            except (OSError, RuntimeError, subprocess.SubprocessError):
                pass
            server.close()

    status = "pass" if failure is None else "fail"
    source_assets = asset_receipt(web_root, role=role)
    report = {
        "schema": "rusty.hostess.trusted_local_control.browser_smoke.v1",
        "status": status,
        "browser": args.browser,
        "listener": {"host": "127.0.0.1", "requested_port": 0},
        "asset_receipt": {
            "role": source_assets["role"],
            "files": [
                {"name": item["name"], "sha256": item["sha256"]}
                for item in source_assets["files"]
            ],
        },
        "product_asset_claim": role == "quest_packaged_assets",
        "flow": flow,
        "selected_video": selected_video,
        "selection_started_playback": False if "select_video" in flow else None,
        "final_playback_state": final_playback_state,
        "console_errors": console_errors,
        "failure": failure,
        "network_actions": {
            "lan_listener": False,
            "mdns": False,
            "fixed_port": False,
            "package_install": False,
            "browser_download": False,
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
