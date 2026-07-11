"""Exact foreign-schema ownership inventory and anti-drift audit."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.hostessctl.json_schema_validation import (
    CheckedSchemaError,
    load_and_validate_checked_schema,
)


SCHEMA_OWNERSHIP_INVENTORY_SCHEMA = (
    "rusty.hostess.schema_ownership.compatibility_inventory.v1"
)
SCHEMA_OWNERSHIP_AUDIT_SCHEMA = "rusty.hostess.schema_ownership.audit.v1"
FOREIGN_SCHEMA_PATTERN = re.compile(
    r"rusty\.(?:quest|manifold)\.[A-Za-z0-9_.-]*\.v[0-9]+"
)
HOSTESS_SCHEMA_PATTERN = re.compile(r"rusty\.hostess\.[A-Za-z0-9_.-]*\.v[0-9]+")
PRODUCTION_EXTENSIONS = (".py", ".cs", ".rs", ".java", ".kt", ".json")
SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"
INVENTORY_SCHEMA_PATH = SCHEMA_ROOT / "schema-ownership-inventory.schema.json"
AUDIT_SCHEMA_PATH = SCHEMA_ROOT / "schema-ownership-audit.schema.json"


class SchemaOwnershipError(ValueError):
    """Invalid ownership inventory or audit input."""


def run_schema_ownership_audit(args: argparse.Namespace) -> int:
    try:
        repo_root = Path(str(getattr(args, "repo_root", "") or ".")).resolve()
        inventory_path = Path(
            str(getattr(args, "inventory", "") or "")
            or repo_root / "fixtures/schema-ownership/foreign-schema-compatibility.json"
        )
        report = build_schema_ownership_audit(repo_root, inventory_path)
        load_and_validate_checked_schema(
            report,
            AUDIT_SCHEMA_PATH,
            label="schema ownership audit output",
        )
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        temporary = out.with_name(f".{out.name}.tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(out)
    except (OSError, json.JSONDecodeError, subprocess.SubprocessError, CheckedSchemaError, SchemaOwnershipError) as exc:
        print(f"schema-ownership: {exc}", file=sys.stderr)
        return 2
    if bool(getattr(args, "fail_on_error", False)) and report["status"] != "pass":
        return 2
    return 0


def build_schema_ownership_audit(repo_root: Path, inventory_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    inventory = read_inventory(inventory_path)
    known_entries = {
        occurrence_key(str(entry["schema_id"]), str(entry["path"])): entry
        for entry in inventory["foreign_schema_references"]
    }
    scanned_files = production_source_paths(repo_root)
    occurrences: dict[tuple[str, str], dict[str, Any]] = {}
    hostess_schema_ids: set[str] = set()
    for source_path in scanned_files:
        relative = source_path.relative_to(repo_root).as_posix()
        text = source_path.read_text(encoding="utf-8", errors="replace")
        hostess_schema_ids.update(HOSTESS_SCHEMA_PATTERN.findall(text))
        for schema in sorted(set(FOREIGN_SCHEMA_PATTERN.findall(text))):
            key = occurrence_key(schema, relative)
            occurrences[key] = {"schema_id": schema, "path": relative}

    observed_keys = set(occurrences)
    known_keys = set(known_entries)
    unknown_keys = sorted(observed_keys - known_keys)
    stale_keys = sorted(known_keys - observed_keys)
    unknown_rows = [occurrences[key] for key in unknown_keys]
    stale_rows = [
        {"schema_id": known_entries[key]["schema_id"], "path": known_entries[key]["path"]}
        for key in stale_keys
    ]
    rows = []
    for key in sorted(observed_keys):
        observed = occurrences[key]
        registered = known_entries.get(key)
        rows.append(
            {
                "schema_id": observed["schema_id"],
                "path": observed["path"],
                "owner": (
                    registered["owner"] if registered else schema_owner(observed["schema_id"])
                ),
                "classification": (
                    registered["classification"] if registered else "unregistered"
                ),
                "role": registered["role"] if registered else "unregistered",
                "registered": registered is not None,
                "new_hostess_output_allowed": False,
            }
        )

    report = {
        "$schema": SCHEMA_OWNERSHIP_AUDIT_SCHEMA,
        "schema_version": 1,
        "status": "pass" if not unknown_rows and not stale_rows else "fail",
        "inventory_path": str(inventory_path),
        "scan_extensions": list(PRODUCTION_EXTENSIONS),
        "scanned_file_count": len(scanned_files),
        "hostess_owned_schema_ids": sorted(hostess_schema_ids),
        "foreign_schema_references": rows,
        "unknown_foreign_references": unknown_rows,
        "stale_inventory_references": stale_rows,
        "unknown_foreign_schema_ids": sorted({row["schema_id"] for row in unknown_rows}),
        "unapproved_foreign_reference_paths": sorted({row["path"] for row in unknown_rows}),
        "stale_inventory_schema_ids": sorted({row["schema_id"] for row in stale_rows}),
        "stale_approved_reference_paths": sorted({row["path"] for row in stale_rows}),
        "policy": {
            "new_output_prefix": "rusty.hostess.",
            "new_foreign_output_allowed": False,
            "qcl_ids": "evidence-profile-reference-only",
            "exact_schema_path_inventory_required": True,
            "tracked_production_language_coverage_required": True,
            "inventory_additions_require_classification_and_role": True,
        },
    }
    load_and_validate_checked_schema(report, AUDIT_SCHEMA_PATH, label="schema ownership audit")
    return report


def read_inventory(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SchemaOwnershipError(f"schema ownership inventory does not exist: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise SchemaOwnershipError("schema ownership inventory must be a JSON object")
    load_and_validate_checked_schema(document, INVENTORY_SCHEMA_PATH, label="schema ownership inventory")
    if document.get("$schema") != SCHEMA_OWNERSHIP_INVENTORY_SCHEMA:
        raise SchemaOwnershipError("unsupported schema ownership inventory schema")
    seen: set[tuple[str, str]] = set()
    for index, entry in enumerate(document["foreign_schema_references"]):
        schema = str(entry["schema_id"])
        path_value = str(entry["path"])
        key = occurrence_key(schema, path_value)
        if key in seen:
            raise SchemaOwnershipError(
                f"inventory contains duplicate schema/path occurrence {schema} @ {path_value}"
            )
        seen.add(key)
        if entry["owner"] != schema_owner(schema):
            raise SchemaOwnershipError(f"inventory owner does not match schema {schema}")
        if "\\" in path_value or path_value.startswith(("/", "../")):
            raise SchemaOwnershipError(f"inventory path must be portable: {path_value}")
        if not str(entry.get("reason") or "").strip():
            raise SchemaOwnershipError(f"inventory entry {index} needs a reason")
    return document


def production_source_paths(repo_root: Path) -> list[Path]:
    """Return every tracked/candidate production source in supported languages."""

    relative_paths: set[str] = set()
    try:
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        candidates = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        relative_paths.update(tracked)
        relative_paths.update(candidates)
    except subprocess.SubprocessError:
        relative_paths.update(
            path.relative_to(repo_root).as_posix()
            for path in repo_root.rglob("*")
            if path.is_file()
        )

    paths = []
    for raw_path in sorted(relative_paths):
        portable = raw_path.replace("\\", "/")
        path = Path(portable)
        if path.suffix.lower() not in PRODUCTION_EXTENSIONS:
            continue
        if not is_production_surface(portable):
            continue
        absolute = repo_root / path
        if absolute.is_file():
            paths.append(absolute)
    return paths


def is_production_surface(path: str) -> bool:
    lowered = path.lower()
    name = Path(path).name.lower()
    if lowered.startswith("tests/") or "/tests/" in lowered:
        return False
    if lowered.startswith("tools/test_") or lowered.startswith("tools/connectivity_probe_tests/"):
        return False
    if name.startswith("test_"):
        return False
    if lowered.startswith("fixtures/schema-ownership/"):
        return False
    if lowered.startswith("fixtures/") and not lowered.startswith("fixtures/project-runner/"):
        return False
    if any(part in {"target", "bin", "obj", "__pycache__", ".git"} for part in Path(lowered).parts):
        return False
    return True


def occurrence_key(schema: str, path: str) -> tuple[str, str]:
    return schema, path.replace("\\", "/")


def schema_owner(schema: str) -> str:
    if schema.startswith("rusty.quest."):
        return "rusty.quest"
    if schema.startswith("rusty.manifold."):
        return "rusty.manifold"
    return "external"


__all__ = [
    "SCHEMA_OWNERSHIP_AUDIT_SCHEMA",
    "SCHEMA_OWNERSHIP_INVENTORY_SCHEMA",
    "SchemaOwnershipError",
    "build_schema_ownership_audit",
    "production_source_paths",
    "run_schema_ownership_audit",
]
