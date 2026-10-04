"""Neutral test-owned pipe child. No device or network operations."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("volume", "wait", "short", "delay", "nonzero", "parent", "source-drift"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    (args.root / ("ready-" + args.mode)).write_text(str(os.getpid()), encoding="ascii")
    if args.mode == "volume":
        for _ in range(32):
            os.write(1, b"o" * 8192)
            os.write(2, b"e" * 8192)
    elif args.mode == "source-drift":
        args.source.write_bytes(b"changed by neutral fixture")
        print("source changed", flush=True)
    elif args.mode == "nonzero":
        print("known nonzero", file=sys.stderr, flush=True)
        return 7
    elif args.mode == "delay":
        print("delayed start", flush=True)
        time.sleep(35)  # Explicit opt-in stimulus, no observer deadline.
        print("delayed complete", flush=True)
    elif args.mode in ("wait", "short"):
        if args.mode == "short":
            print("short live diagnostic", flush=True)
        while not (args.root / "RELEASE").exists():
            time.sleep(.02)
        print("released", flush=True)
    elif args.mode == "parent":
        child = subprocess.Popen([sys.executable, __file__, "wait", "--root", str(args.root)])
        (args.root / "descendant-pid").write_text(str(child.pid), encoding="ascii")
        while not (args.root / "ready-wait").exists():
            time.sleep(.02)
        print("actual parent boundary", flush=True)
        # No wait: descendant genuinely retains both inherited pipes.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
