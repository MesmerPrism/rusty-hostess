"""Finite real SDK developer backend. QFM owns typed APK/transfer operations.

Fixed serial-scoped ADB fills documented SDK/status/hash/capture provider gaps.
No install, launch, force-stop, daemon/port operation, watcher or arbitrary argv.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sys

from tools.hostessctl.process_observation import ObservationFailure, ObservationInterrupted, observe_process
from tools.hostessctl.sdk_graphics_batch import NAMES, digest, load_baseline, read_json
from tools.hostessctl.sdk_graphics_live_contract import load_config, parse_status, project_status, project_settings, sha_file
from tools.hostessctl.sdk_graphics_pixels import check_pixels
from tools.hostessctl.sdk_graphics_iteration import EffectNotDispatched


class LiveExecutor:
    evidence_scope = "sdk-debug-android-display-pixels-no-gpu-completion"

    def __init__(self, config_path, catalog, root, *, observer=observe_process):
        self.config_path = Path(config_path)
        self.config = load_config(config_path)
        self.config_digest = sha_file(config_path)
        self.catalog = Path(catalog)
        load_baseline(self.catalog)
        if sha_file(self.catalog) != self.config["catalog_sha256"]:
            raise ValueError("catalog_pin_changed")
        self.reference = project_status(read_json(Path(self.config["app_status_reference"]["path"])), self.config)
        self.settings = project_settings(read_json(Path(self.config["settings_reference"]["path"])))
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.remote = "/sdcard/Android/data/"+self.config["package"]+"/files/app_assets"
        self.observer = observer
        self.operations = {}
        self.counter = 0
        self.qualified = False
        self.last_reload = None
        self.last_end = None
        self.reporting_errors = []

    def _pins(self):
        if sha_file(self.config_path) != self.config_digest:
            raise ValueError("live_input_changed")
        load_config(self.config_path)
        if sha_file(self.catalog) != self.config["catalog_sha256"]:
            raise ValueError("catalog_pin_changed")

    def _run(self, tag, argv, *, request=None, binary=False):
        self.counter += 1
        lane = self.root/f"{self.counter:04}-{tag}"
        lane.mkdir(exist_ok=False)
        env = dict(os.environ)
        env["QUESTIONABLE_FILE_MANAGER_ADB"] = self.config["adb"]["path"]
        operation = self.operations.setdefault(request, {"retired": False, "processes": [], "files": []}) if request else None
        if operation is not None:
            operation["retired"] = False
        try:
            receipt = self.observer(argv, lane/"stdout.raw", lane/"stderr.raw", env=env, admit=self._pins,
                                    stdout_budget=33554432 if binary else 4194304, stderr_budget=1048576)
        except (ObservationFailure, ObservationInterrupted) as error:
            receipt = error.receipt
            if operation is not None:
                operation["processes"].append(deepcopy(receipt))
            self._save_receipt(lane, receipt)
            if (isinstance(error, ObservationFailure) and operation is not None and
                    all(not item["child_started"] for item in operation["processes"])):
                raise EffectNotDispatched("owned_effect_child_not_started") from error
            raise  # Original owned child remains attached to the exception.
        if operation is not None:
            operation["processes"].append(deepcopy(receipt))
        complete = (receipt["observation_complete"] and receipt["process_reaped"] and receipt["exit_known"])
        # Store terminal transport fact before reporting; journal I/O is separate.
        if operation is not None:
            operation["retired"] = bool(complete and
                (argv[0] != self.config["qfm"]["path"] or receipt["exit_code"] == 0))
        self._save_receipt(lane, receipt)
        if not complete or receipt["exit_code"] != 0:
            raise ValueError("transport_failed_or_unknown_no_replay")
        return (lane/"stdout.raw").read_bytes()

    def _save_receipt(self, lane, receipt):
        try:
            with (lane/"process.json").open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(receipt, indent=2)+"\n")
        except OSError as error:
            self.reporting_errors.append({"stage": "process-receipt", "error_type": type(error).__name__})
            # Known process/operation facts are retained in memory, not relabeled.

    def _adb(self, tag, args, **kwargs):
        return self._run(tag, [self.config["adb"]["path"], "-s", self.config["serial"], *args], **kwargs)

    def _installed(self):
        raw = self._run("qfm-installed", [self.config["qfm"]["path"], "apk", "observe", "--serial",
                        self.config["serial"], "--file", self.config["apk"]["path"], "--json"])
        result = json.loads(raw)
        artifact, installed = result["Artifact"], result["Installed"]
        if (artifact["Sha256"] != self.config["apk"]["sha256"] or installed["BaseApkSha256"] != artifact["Sha256"] or
                installed["BaseApkSizeBytes"] != artifact["SizeBytes"] or len(installed["ApkPaths"]) != 1 or
                artifact["Identity"]["PackageName"] != self.config["package"] or
                installed["Identity"] != artifact["Identity"]):
            raise ValueError("strong_installed_enabling_apk_mismatch")

    def _settings(self):
        request = self.root/f"settings-request-{self.counter+1:04}.json"
        output = self.root/f"settings-receipt-{self.counter+1:04}"
        with request.open("x") as stream:
            stream.write(json.dumps({"schema": "rusty.quest.product_panel.command.v1", "operation": "status"}))
        cfg, provider = self.config, self.config["settings_provider"]
        self._run("app-settings", [provider["pwsh"]["path"], "-NoProfile", "-File", provider["script"]["path"],
                  "-Device", cfg["serial"], "-CanonicalSerial", cfg["canonical_serial"], "-BootId", cfg["boot_id"],
                  "-Package", cfg["package"], "-Adb", cfg["adb"]["path"], "-AdbSha256", cfg["adb"]["sha256"],
                  "-RequestPath", str(request), "-OutputDirectory", str(output)])
        if project_settings(read_json(output/"app-receipt.json")) != self.settings:
            raise ValueError("app_owned_submitted_settings_changed")

    def _qualify(self):
        if self.qualified:
            return
        output = self.root/"apk-join.json"
        self._run("quest-apk-join", [sys.executable,
                  str(Path(self.config["quest_provider"]["root"])/"Qualify-SdkGraphicsApk.py"),
                  "--apk", self.config["apk"]["path"], "--catalog", str(self.catalog), "--out", str(output)])
        result = read_json(output)
        if (result["status"] != "bytes-joined" or result["apk"]["sha256"] != self.config["apk"]["sha256"] or
                result["catalog"]["sha256"] != self.config["catalog_sha256"]):
            raise ValueError("actual_apk_baseline_join_required")
        self._installed()
        self.qualified = True

    def status(self):
        self._qualify()
        cfg = self.config
        canonical = self._adb("canonical", ["shell", "getprop", "ro.serialno"]).decode().strip()
        process = self._adb("boot-actor", ["exec-out", "cat", "/proc/sys/kernel/random/boot_id",
                   f"/proc/{cfg['pid']}/stat", f"/proc/{cfg['pid']}/status", f"/proc/{cfg['pid']}/cmdline"])
        lines = process.decode().splitlines()
        if len(lines) < 4:
            raise ValueError("complete_boot_actor_readback_required")
        boot, stat = lines[:2]
        fields = stat[stat.rfind(")")+2:].split()
        actor_status = "\n".join(lines[2:-1])
        command = lines[-1].split("\0")[0]
        uids = re.search(r"^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", actor_status, re.MULTILINE)
        if (boot != cfg["boot_id"] or canonical != cfg["canonical_serial"] or command != cfg["package"] or
                not stat.startswith(str(cfg["pid"])+" (") or len(fields) < 20 or int(fields[19]) != cfg["start_ticks"] or
                not uids or any(int(uid) != cfg["uid"] for uid in uids.groups())):
            raise ValueError("exact_current_boot_actor_required")
        raw = self._adb("app-status", ["shell", "content", "call", "--uri", "content://"+cfg["package"]+".probe-control",
                                     "--method", "status"])
        status = parse_status(raw, cfg)
        if status["actor"] != self.reference["actor"]:
            raise ValueError("selected_scene_settings_or_producer_changed")
        if self.last_end is not None and status["end_frame"] < self.last_end:
            raise ValueError("end_frame_regressed")
        self.last_end = status["end_frame"]
        return status

    def upload(self, request_id, name, data):
        if name not in NAMES or not re.fullmatch(r"[a-f0-9]{32}", request_id):
            raise ValueError("closed_transfer_required")
        operation = self.operations.setdefault(request_id, {"retired": False, "processes": [], "files": []})
        if name in operation["files"]:
            raise ValueError("no_transfer_replay")
        if not operation["files"]:
            try:
                self._installed()
                self._settings()
            except Exception as error:
                raise EffectNotDispatched("transfer_predispatch_refused") from error
            self._adb("fixed-directory", ["shell", "mkdir", "-p", self.remote], request=request_id)
        local = self.root/(request_id+"-"+name)
        with local.open("xb") as stream:
            stream.write(data)
        raw = self._run("qfm-push", [self.config["qfm"]["path"], "files", "push", "--serial", self.config["serial"],
                        "--file", str(local), "--remote", self.remote+"/"+name, "--json"], request=request_id)
        operation["retired"] = False
        result = json.loads(raw)
        if (result["mutation"]["Stage"] != "confirmed" or result["mutation"]["HeadsetReadback"] is not True or
                result["result"]["command"]["ExitCode"] != 0):
            raise ValueError("qfm_original_transfer_not_terminal")
        operation["retired"] = True
        operation["files"].append(name)

    def hashes(self, names):
        if tuple(names) != NAMES:
            raise ValueError("closed_hash_names_required")
        raw = self._adb("fixed-hashes", ["shell", "sha256sum", *[self.remote+"/"+name for name in NAMES]])
        rows = raw.decode().strip().splitlines()
        if len(rows) != len(NAMES):
            raise ValueError("complete_hash_readback_required")
        result = {}
        for name, line in zip(NAMES, rows):
            match = re.fullmatch(r"([a-f0-9]{64})  "+re.escape(self.remote+"/"+name), line)
            if not match:
                raise ValueError("fixed_hash_readback_mismatch")
            result[name] = match.group(1)
        return result

    def _capture(self, predicate):
        self._settings()
        before = self.status()
        raw = self._adb("android-display", ["exec-out", "screencap"], binary=True)
        after = self.status()
        self._settings()
        if after["frame"] <= before["frame"] or after["end_frame"] <= before["end_frame"]:
            raise ValueError("capture_requires_advancing_fenced_app_frames")
        return after, raw, check_pixels(raw, predicate)

    def reload(self, request_id, batch_digest):
        try:
            predicate = self.config["pixel_predicates"][batch_digest]
            self._installed()
            before, raw, pixels = self._capture(predicate)
            if pixels["matched"]:
                raise ValueError("pretrigger_pixels_already_match_predicate")
        except Exception as error:
            raise EffectNotDispatched("reload_predispatch_refused") from error
        self.last_reload = {"request_id": request_id, "batch_digest": batch_digest, "pre_frame": before["frame"]}
        self._adb("sdk-debug-trigger", ["shell", "am", "broadcast", "-a",
                  "com.meta.spatial.debugtools.HOT_RELOAD_PUSH_COMPLETE", "-p", self.config["package"]], request=request_id)

    def observe(self):
        if not self.last_reload:
            return {**self.status(), "scope": self.evidence_scope}
        predicate = self.config["pixel_predicates"][self.last_reload["batch_digest"]]
        status, raw, pixels = self._capture(predicate)
        result = {**status, "scope": self.evidence_scope, "pixel_observation": pixels,
                  "gpu_completion": False, "sdk_completion_callback": False}
        if self.last_reload and pixels["matched"] and status["frame"] > self.last_reload["pre_frame"]:
            result.update(request_id=self.last_reload["request_id"], batch_digest=self.last_reload["batch_digest"],
                          effect_frame=status["frame"], witness_sha256=digest(raw))
        return result

    def retirement(self, request_id):
        operation = self.operations.get(request_id, {})
        return {"request_id": request_id, "retired": operation.get("retired") is True,
                "scope": "owned-transport-operation-only-not-sdk-or-gpu-retirement"}
