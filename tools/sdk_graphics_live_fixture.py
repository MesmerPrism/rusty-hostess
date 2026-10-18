"""Test-only executable QFM/ADB peer; local files and synthetic pixels, no GPU."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

root = Path(sys.argv[1])
argv = json.loads(sys.argv[2])
state_path = root/"state.json"
state = json.loads(state_path.read_text())
args = argv[1:]
remote = root/"remote"
remote.mkdir(exist_ok=True)
out = None
exit_code = 0
if args[:2] == ["-NoProfile", "-File"]:
    request = json.loads(Path(args[args.index("-RequestPath")+1]).read_text())
    if request != {"schema": "rusty.quest.product_panel.command.v1", "operation": "status"}:
        raise ValueError("fixture status-only settings")
    output = Path(args[args.index("-OutputDirectory")+1])
    output.mkdir()
    (output/"app-receipt.json").write_text(json.dumps(state["settings"]))
elif "Qualify-SdkGraphicsApk.py" in argv[1]:
    result = {"status": "bytes-joined", "apk": {"sha256": state["apk_sha"]},
              "catalog": {"sha256": state["catalog_sha"]}}
    Path(args[args.index("--out")+1]).write_text(json.dumps(result))
elif args[:2] == ["apk", "observe"]:
    identity = {"PackageName": "example.sdk.consumer"}
    out = {"Artifact": {"Sha256": state["apk_sha"], "SizeBytes": 32, "Identity": identity},
           "Installed": {"BaseApkSha256": state["apk_sha"], "BaseApkSizeBytes": 32,
                         "ApkPaths": ["base.apk"], "Identity": identity}}
elif args[:2] == ["files", "push"]:
    name = Path(args[args.index("--file")+1]).name.split("-", 1)[1]
    shutil.copyfile(args[args.index("--file")+1], remote/name)
    if state.get("bad_push") == name:
        out = "lost provider response"
    else:
        out = {"mutation": {"Stage": "confirmed", "HeadsetReadback": True},
               "result": {"command": {"ExitCode": 0}}}
else:
    if args[:2] != ["-s", "FIXTURE"]:
        raise ValueError("fixture exact target")
    args = args[2:]
    if args == ["shell", "cat", "/proc/sys/kernel/random/boot_id"]:
        out = state["boot"]
    elif args == ["exec-out", "cat", "/proc/sys/kernel/random/boot_id", "/proc/41/stat", "/proc/41/status", "/proc/41/cmdline"]:
        out = (state["boot"]+"\n41 (fixture) "+" ".join(["S"]+["0"]*18+["1234"])+
               "\nUid:\t10041\t10041\t10041\t10041\nexample.sdk.consumer\0").encode()
    elif args == ["shell", "getprop", "ro.serialno"]:
        out = "FIXTURE"
    elif args == ["shell", "cat", "/proc/41/stat"]:
        out = "41 (fixture) "+" ".join(["S"]+["0"]*18+["1234"])
    elif args == ["shell", "cat", "/proc/41/status"]:
        out = "Uid:\t10041\t10041\t10041\t10041\n"
    elif args == ["exec-out", "cat", "/proc/41/cmdline"]:
        out = b"example.sdk.consumer\0"
    elif args[:3] == ["shell", "content", "call"]:
        status = state["snapshot"]
        state["frame"] += 1
        status["submissionObserver"]["frame"].update(acceptedSequence=str(state["frame"]), endSequence=str(state["frame"]))
        out = "Bundle[{snapshot="+json.dumps(status)+", observed=true}]"
    elif args[:3] == ["shell", "mkdir", "-p"]:
        out = ""
    elif args[:2] == ["shell", "sha256sum"]:
        out = "\n".join(hashlib.sha256((remote/Path(name).name).read_bytes()).hexdigest()+"  "+name for name in args[2:])
    elif args[:3] == ["shell", "am", "broadcast"]:
        state["reloads"] += 1
        state["candidate"] = b"changed" in (remote/"workload.vert.spv").read_bytes()
        out = "Broadcast completed: result=0"
        if state.get("unknown_trigger"):
            exit_code = 7
    elif args == ["exec-out", "screencap"]:
        rgb = bytes((255, 0, 0, 255) if state["candidate"] else (0, 255, 0, 255))
        out = struct.pack("<III", 8, 8, 1)+rgb*64
    else:
        raise ValueError("fixture unknown closed operation")
state_path.write_text(json.dumps(state))
if type(out) is bytes:
    sys.stdout.buffer.write(out)
elif type(out) is dict:
    print(json.dumps(out))
elif out is not None:
    print(out)
sys.exit(exit_code)
