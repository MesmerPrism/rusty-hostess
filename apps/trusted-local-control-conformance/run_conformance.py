"""Run the standard-library trusted-local-control conformance report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trusted_local_control_conformance.conformance import (
    build_report,
    find_quest_web_root,
    read_descriptor,
)
from trusted_local_control_conformance.contract import build_descriptor


APP_ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--descriptor", type=Path)
    parser.add_argument("--web-root", type=Path)
    parser.add_argument("--quest-root", type=Path)
    args = parser.parse_args()

    descriptor = read_descriptor(args.descriptor) if args.descriptor else build_descriptor()
    web_root = args.web_root
    if web_root is None and args.quest_root is not None:
        web_root = find_quest_web_root(args.quest_root)
        if web_root is None:
            parser.error("bound Quest app must contain one packaged index.html/app.js/styles.css directory")
    if web_root is None:
        web_root = APP_ROOT / "web"
    report = build_report(
        descriptor=descriptor,
        web_root=web_root,
        quest_root=args.quest_root,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
