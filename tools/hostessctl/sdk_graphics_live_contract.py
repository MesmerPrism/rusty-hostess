"""Private closed inputs and typed app-owned status projection for SDK debug."""
import hashlib
import json
from pathlib import Path
import re

from tools.hostessctl.sdk_graphics_batch import read_json
from tools.hostessctl.sdk_graphics_pixels import validate_predicate


def sha_file(path, maximum=536870912):
    path = Path(path).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError("regular_nonreparse_input_required")
    if not 0 < path.stat().st_size <= maximum:
        raise ValueError("bounded_input_required")
    sha, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1048576):
            sha.update(chunk)
            size += len(chunk)
    if size > maximum:
        raise ValueError("input_grew_beyond_bound")
    return sha.hexdigest()


def load_config(path, *, hash_file=sha_file, document=read_json):
    config = document(Path(path))
    keys = {"schema", "serial", "canonical_serial", "boot_id", "package", "pid", "uid", "start_ticks",
            "apk", "adb", "qfm", "quest_provider", "enabling_receipt", "catalog_sha256", "pixel_predicates",
            "app_status_reference", "settings_reference", "settings_provider", "operator_authorized_sdk_debug_fallback"}
    version = config.get("schema")
    if version == "rusty.hostess.sdk_graphics.live_inputs.v2":
        keys |= {"input_binding", "capture"}
        if config.get("input_binding") not in ("rehash", "windows-immutable"):
            raise ValueError("closed_input_binding_required")
        capture = config.get("capture")
        if (type(capture) is not dict or set(capture) != {"format", "width", "height"} or
                capture["format"] not in ("android-raw", "android-png") or
                any(type(capture[k]) is not int or not 0 < capture[k] <= 8192 for k in ("width", "height")) or
                capture["height"]*(capture["width"]*4+1) > 33554432):
            raise ValueError("closed_bounded_capture_required")
    elif version != "rusty.hostess.sdk_graphics.live_inputs.v1":
        raise ValueError("closed_live_inputs_required")
    if set(config) != keys:
        raise ValueError("closed_live_inputs_required")
    for field in ("serial", "canonical_serial"):
        if not isinstance(config[field], str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", config[field]):
            raise ValueError("exact_serial_required")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+", config["package"]):
        raise ValueError("android_package_required")
    if not re.fullmatch(r"[a-f0-9-]{36}", config["boot_id"]):
        raise ValueError("boot_identity_required")
    if any(type(config[k]) is not int or config[k] <= 0 for k in ("pid", "uid", "start_ticks")):
        raise ValueError("exact_actor_required")
    if config["operator_authorized_sdk_debug_fallback"] is not True:
        raise ValueError("explicit_sdk_developer_fallback_authorization_required")
    if (type(config["pixel_predicates"]) is not dict or not 1 <= len(config["pixel_predicates"]) <= 8 or
            any(not re.fullmatch(r"[a-f0-9]{64}", key) for key in config["pixel_predicates"])):
        raise ValueError("bounded_batch_bound_predicates_required")
    for value in config["pixel_predicates"].values():
        validate_predicate(value)
    for key in ("apk", "adb", "qfm", "enabling_receipt", "app_status_reference", "settings_reference"):
        pin = config[key]
        if set(pin) != {"path", "sha256"} or hash_file(pin["path"]) != pin["sha256"]:
            raise ValueError("input_pin_changed")
    if set(config["settings_provider"]) != {"script", "pwsh"}:
        raise ValueError("app_owned_status_provider_required")
    for pin in config["settings_provider"].values():
        if set(pin) != {"path", "sha256"} or hash_file(pin["path"]) != pin["sha256"]:
            raise ValueError("settings_provider_pin_changed")
    project_settings(document(Path(config["settings_reference"]["path"])))
    provider = config["quest_provider"]
    if set(provider) != {"root", "scripts"} or set(provider["scripts"]) != {
            "Prepare-FreshSdkHotload.py", "Prepare-SdkHotloadCatalog.py", "Qualify-SdkGraphicsApk.py"}:
        raise ValueError("closed_quest_provider_required")
    for name, sha in provider["scripts"].items():
        if hash_file(Path(provider["root"])/name) != sha:
            raise ValueError("quest_provider_pin_changed")
    enabled = document(Path(config["enabling_receipt"]["path"]))
    if (enabled.get("passed") is not True or enabled.get("apk_sha256") != config["apk"]["sha256"] or
            enabled.get("sdk_graphics_hot_reload_selected") is not True):
        raise ValueError("selected_enabling_apk_owner_evidence_required")
    return config


def project_settings(receipt):
    if (receipt.get("schema") != "rusty.quest.product_panel.receipt.v1" or receipt.get("status") != "current" or
            not re.fullmatch(r"[a-f0-9]{32}", receipt.get("owner_token", ""))):
        raise ValueError("current_app_owned_settings_required")
    particles = receipt["observation"]["particles"]
    if particles.get("submitted_owner_current") is not True or type(particles.get("submitted_parameters")) is not dict:
        raise ValueError("current_submitted_parameters_required")
    return {"owner_token": receipt["owner_token"], "particles": {key:particles[key] for key in
            ("submitted_parameters", "submitted_revision", "runtime_epoch", "sdk_epoch", "service_generation")}}


def parse_status(raw, config):
    text = raw.decode("utf-8")
    match = re.search(r"snapshot=(\{.*\}), observed=true(?:,|\})", text, re.DOTALL)
    if not match:
        raise ValueError("app_owned_observed_snapshot_required")
    return project_status(json.loads(match.group(1)), config)


def project_status(status, config):
    identity = status["identity"]
    if identity["packageName"] != config["package"] or identity["pid"] != config["pid"]:
        raise ValueError("app_owned_actor_mismatch")
    observer, frame = status["submissionObserver"], status["submissionObserver"]["frame"]
    if frame["focused"] is not True or frame["eligibleAtRead"] is not True or observer["binding"] != "bound_exact_context":
        raise ValueError("focused_eligible_app_frames_required")
    counters = []
    for key in ("acceptedSequence", "endSequence"):
        value = str(frame[key])
        if not re.fullmatch(r"[0-9]{1,20}", value) or int(value) > 2**64-1:
            raise ValueError("strict_unsigned_frame_counter_required")
        counters.append(int(value))
    actor = {key:status[key] for key in ("identity", "controls", "topology", "consumerBindings",
             "originalProductStartup", "producerHandle", "restoreSrgb", "flipRows")}
    actor["observer"] = {key:observer[key] for key in ("instanceGeneration", "sessionGeneration",
                          "activityOwnerEpoch", "appAttachmentEpoch")}
    actor["graphics"] = {key:observer["graphicsBinding"][key] for key in ("available", "backend",
                         "instanceGeneration", "sessionGeneration", "lifetimeRevision", "creationHostNs", "creationResult")}
    actor["producer_generation"] = {key:status["native"][key] for key in ("generation", "sourceStateGeneration")}
    return {"actor": actor, "frame": counters[0], "end_frame": counters[1], "eligible": True}
