"""Fail-closed declarative Hostess project workflow planning.

Hostess composes owner artifacts but never becomes their runtime authority.
The runner validates one exact project-to-product closure, fresh role-specific
owner receipts, risk-tier gates, and then publishes an envelope/plan/receipt
generation whose completion marker is the sole atomic acceptance point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from tools.hostessctl.json_schema_validation import (
    CheckedSchemaError,
    load_and_validate_checked_schema,
)


PROJECT_SPEC_SCHEMA = "rusty.morphospace.workflow.project_spec.v2"
PRODUCT_LOCK_SCHEMA = "rusty.manifold.broker.product_lock.v1"
CLEANUP_CONTRACT_SCHEMA = "rusty.hostess.project_runner.cleanup_contract.v1"
PROJECT_RUNNER_ENVELOPE_SCHEMA = "rusty.hostess.project_runner.envelope.v1"
PROJECT_RUNNER_PLAN_SCHEMA = "rusty.hostess.project_runner.plan.v1"
PROJECT_RUNNER_RECEIPT_SCHEMA = "rusty.hostess.project_runner.receipt.v1"
PROJECT_RUNNER_COMPLETION_SCHEMA = "rusty.hostess.project_runner.generation_completion.v1"
PROJECT_RUNNER_PROJECTION_SCHEMA = "rusty.hostess.project_runner.projection.v1"

PROFILE_SCHEMAS = {
    "topology": "rusty.hostess.project_runner.topology_profile.v1",
    "media": "rusty.hostess.project_runner.media_profile.v1",
    "evidence": "rusty.hostess.project_runner.evidence_profile.v1",
}
PROFILE_OWNER_SCHEMAS = {
    "topology": "rusty.manifold.peer.topology_authorization.v1",
    "media": "rusty.manifold.media.session_descriptor.v1",
    "evidence": "rusty.quest.generic_media_session_evidence.v1",
}
PROFILE_OWNERS = {
    "topology": "rusty.manifold",
    "media": "rusty.manifold",
    "evidence": "rusty.quest",
}
PROFILE_RECEIPT_SCHEMAS = {
    "topology": "rusty.manifold.peer.topology_authorization.v1",
    "media": "rusty.manifold.broker.adapter_receipt.v1",
    "evidence": "rusty.quest.generic_media_session_evidence.v1",
}
PROFILE_BINDING_SCHEMAS = {
    "topology": "rusty.hostess.project_runner.topology_receipt_binding.v1",
    "media": "rusty.hostess.project_runner.media_receipt_binding.v1",
    "evidence": "rusty.hostess.project_runner.evidence_receipt_binding.v1",
}

SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"
INPUT_SCHEMA_FILES = {
    "project_spec": "project-runner-project-spec-input.schema.json",
    "product_lock": "project-runner-product-lock-input.schema.json",
    "topology_profile": "project-runner-topology-profile.schema.json",
    "topology_receipt": "project-runner-topology-receipt-input.schema.json",
    "media_profile": "project-runner-media-profile.schema.json",
    "media_receipt": "project-runner-media-receipt-input.schema.json",
    "evidence_profile": "project-runner-evidence-profile.schema.json",
    "evidence_receipt": "project-runner-evidence-receipt-input.schema.json",
    "cleanup_contract": "project-runner-cleanup-contract.schema.json",
}
OUTPUT_SCHEMA_FILES = {
    PROJECT_RUNNER_ENVELOPE_SCHEMA: "project-runner-envelope.schema.json",
    PROJECT_RUNNER_PLAN_SCHEMA: "project-runner-plan.schema.json",
    PROJECT_RUNNER_RECEIPT_SCHEMA: "project-runner-receipt.schema.json",
    PROJECT_RUNNER_COMPLETION_SCHEMA: "project-runner-generation-completion.schema.json",
    PROJECT_RUNNER_PROJECTION_SCHEMA: "project-runner-projection.schema.json",
}
OWNER_RECEIPT_SCHEMA_FILES = {
    "topology": "project-runner-owner-topology-receipt.schema.json",
    "media": "project-runner-owner-media-receipt.schema.json",
    "evidence": "project-runner-owner-evidence-receipt.schema.json",
}

ALLOWED_RISK_TIERS = ("quick", "standard", "deep", "device", "release")
RISK_RANK = {name: index for index, name in enumerate(ALLOWED_RISK_TIERS)}
RISK_REQUIRED_EVIDENCE_OBSERVATIONS = {
    "quick": set(),
    "standard": {"bounded_exchange", "inactive_cleanup", "package_cleanup", "zero_fatals"},
    "deep": {
        "bounded_exchange",
        "inactive_cleanup",
        "package_cleanup",
        "zero_fatals",
        "damaged_fixtures_rejected",
        "ownership_audit_passed",
    },
    "device": {
        "bounded_exchange",
        "inactive_cleanup",
        "package_cleanup",
        "zero_fatals",
        "damaged_fixtures_rejected",
        "ownership_audit_passed",
        "device_validation_passed",
        "device_cleanup_complete",
    },
    "release": {
        "bounded_exchange",
        "inactive_cleanup",
        "package_cleanup",
        "zero_fatals",
        "damaged_fixtures_rejected",
        "ownership_audit_passed",
        "device_validation_passed",
        "device_cleanup_complete",
        "release_checks_passed",
    },
}
RISK_REQUIRED_CLEANUP_KINDS = {
    "quick": {"zero_fatals"},
    "standard": {"topology_inactive", "package_cleanup", "zero_fatals"},
    "deep": {"topology_inactive", "package_cleanup", "zero_fatals"},
    "device": {
        "topology_inactive",
        "package_cleanup",
        "zero_fatals",
        "device_process_inactive",
    },
    "release": {
        "topology_inactive",
        "package_cleanup",
        "zero_fatals",
        "device_process_inactive",
        "release_artifact_cleanup",
    },
}
RISK_MAX_RECEIPT_AGE_SECONDS = {
    "quick": 86400,
    "standard": 3600,
    "deep": 3600,
    "device": 900,
    "release": 300,
}

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
FINGERPRINT_PATTERN = re.compile(r"^fnv1a64-[0-9a-f]{16}$")
QCL_IDENTIFIER_PATTERN = re.compile(
    r"(?:^|[._:/-])qcl(?:[0-9]|[._:/-])",
    re.IGNORECASE,
)


class ProjectRunnerError(ValueError):
    """Fail-closed declarative workflow validation error."""


def run_project_runner_inspect(args: argparse.Namespace) -> int:
    """Validate one complete generation and emit a read-only operator projection."""

    try:
        completion_path = Path(str(args.completion))
        completion = read_checked_hostess_output(
            completion_path,
            expected_schema=PROJECT_RUNNER_COMPLETION_SCHEMA,
            label="project runner completion marker",
        )
        refs = list_value(completion.get("artifacts"))
        roles = {str(ref.get("role")): ref for ref in refs if isinstance(ref, dict)}
        if set(roles) != {"hostess.envelope", "hostess.plan", "hostess.receipt"}:
            raise ProjectRunnerError("completion marker must bind exactly envelope, plan, and receipt")
        reverify_input_refs(refs)
        envelope = read_checked_hostess_output(
            Path(str(roles["hostess.envelope"]["path"])),
            expected_schema=PROJECT_RUNNER_ENVELOPE_SCHEMA,
            label="project runner envelope",
        )
        plan = read_checked_hostess_output(
            Path(str(roles["hostess.plan"]["path"])),
            expected_schema=PROJECT_RUNNER_PLAN_SCHEMA,
            label="project runner plan",
        )
        receipt = read_checked_hostess_output(
            Path(str(roles["hostess.receipt"]["path"])),
            expected_schema=PROJECT_RUNNER_RECEIPT_SCHEMA,
            label="project runner receipt",
        )
        for document, label in ((envelope, "envelope"), (plan, "plan"), (receipt, "receipt")):
            if document.get("generation_id") != completion["generation_id"]:
                raise ProjectRunnerError(f"{label} generation_id does not match completion marker")
            if document.get("run_id") != completion["run_id"]:
                raise ProjectRunnerError(f"{label} run_id does not match completion marker")
        projection = build_project_runner_projection(
            completion_path=completion_path,
            completion=completion,
            envelope=envelope,
            plan=plan,
            receipt=receipt,
        )
        validate_hostess_output_document(projection, "project runner projection")
        validate_output_qcl_lanes(projection, "project runner projection")
        out = Path(str(args.out))
        out.parent.mkdir(parents=True, exist_ok=True)
        temporary = out.with_name(f".{out.name}.{uuid4().hex}.tmp")
        temporary.write_bytes(serialized_json(projection))
        temporary.replace(out)
        return 0
    except (OSError, json.JSONDecodeError, CheckedSchemaError, ProjectRunnerError) as exc:
        print(f"project-runner-inspect: {exc}", file=sys.stderr)
        return 2


def run_project_runner(
    args: argparse.Namespace,
    *,
    clock_func: Callable[[], str] | None = None,
    replace_func: Callable[[Path, Path], None] | None = None,
) -> int:
    """Validate inputs and publish one completion-marker-bound generation."""

    try:
        if bool(getattr(args, "execute", False)):
            raise ProjectRunnerError(
                "project-runner execution is not implemented; omit --execute for the "
                "source-only dry-run plan"
            )
        now = (clock_func or utc_now)()
        parse_utc(now, "planner clock")
        documents = load_project_runner_inputs(args, now=now)
        run_id = str(getattr(args, "run_id", "") or "").strip()
        if not run_id:
            project_id = str(documents["project_spec"]["document"]["project_id"])
            run_id = f"{project_id}-{compact_timestamp(now)}"
        require_non_qcl_value(run_id, "run_id")
        generation_id = f"generation.{run_id}.{uuid4().hex}"

        receipt_out = Path(args.out)
        envelope_out = Path(
            str(getattr(args, "envelope_out", "") or "")
            or str(receipt_out.with_name(f"{receipt_out.stem}.envelope.json"))
        )
        plan_out = Path(
            str(getattr(args, "plan_out", "") or "")
            or str(receipt_out.with_name(f"{receipt_out.stem}.plan.json"))
        )
        completion_out = Path(
            str(getattr(args, "completion_out", "") or "")
            or str(receipt_out.with_name(f"{receipt_out.stem}.complete.json"))
        )
        generation_dir = (
            completion_out.parent.resolve()
            / ".project-runner-generations"
            / generation_id
        )
        authoritative_envelope_out = generation_dir / "envelope.json"
        authoritative_plan_out = generation_dir / "plan.json"
        authoritative_receipt_out = generation_dir / "receipt.json"

        envelope = build_project_runner_envelope(
            args,
            documents,
            run_id=run_id,
            generation_id=generation_id,
            now=now,
        )
        validate_hostess_output_document(envelope, "project runner envelope")
        validate_output_qcl_lanes(envelope, "project runner envelope")

        validate_output_paths(
            [receipt_out, envelope_out, plan_out, completion_out],
            [Path(ref["path"]) for ref in envelope["inputs"]],
        )
        envelope_ref = generated_artifact_ref(
            "hostess.envelope",
            authoritative_envelope_out,
            PROJECT_RUNNER_ENVELOPE_SCHEMA,
            envelope,
        )

        plan = build_project_runner_plan(
            envelope,
            documents,
            envelope_ref=envelope_ref,
            run_id=run_id,
            generation_id=generation_id,
            now=now,
        )
        validate_hostess_output_document(plan, "project runner plan")
        validate_output_qcl_lanes(plan, "project runner plan")
        plan_ref = generated_artifact_ref(
            "hostess.plan", authoritative_plan_out, PROJECT_RUNNER_PLAN_SCHEMA, plan
        )

        receipt = build_project_runner_receipt(
            envelope,
            documents,
            envelope_ref=envelope_ref,
            plan_ref=plan_ref,
            run_id=run_id,
            generation_id=generation_id,
            now=now,
        )
        validate_hostess_output_document(receipt, "project runner receipt")
        validate_output_qcl_lanes(receipt, "project runner receipt")
        receipt_ref = generated_artifact_ref(
            "hostess.receipt",
            authoritative_receipt_out,
            PROJECT_RUNNER_RECEIPT_SCHEMA,
            receipt,
        )
        completion = build_generation_completion(
            run_id=run_id,
            generation_id=generation_id,
            now=now,
            artifact_refs=[envelope_ref, plan_ref, receipt_ref],
        )
        validate_hostess_output_document(completion, "project runner completion marker")
        validate_output_qcl_lanes(completion, "project runner completion marker")

        reverify_input_refs(envelope["inputs"])
        publish_generation(
            [
                (envelope_out, authoritative_envelope_out, envelope),
                (plan_out, authoritative_plan_out, plan),
                (receipt_out, authoritative_receipt_out, receipt),
            ],
            completion_out=completion_out,
            completion=completion,
            replace_func=replace_func,
        )
        return 0
    except (OSError, json.JSONDecodeError, CheckedSchemaError, ProjectRunnerError) as exc:
        print(f"project-runner: {exc}", file=sys.stderr)
        return 2


def load_project_runner_inputs(
    args: argparse.Namespace,
    *,
    now: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Load, schema-check, hash-pin, and cross-bind every input."""

    now = now or utc_now()
    bindings = [
        ("project_spec", "project-spec", "project_spec_sha256"),
        ("product_lock", "product-lock", "product_lock_sha256"),
        ("topology_profile", "topology-profile", "topology_profile_sha256"),
        ("topology_receipt", "topology-receipt", "topology_receipt_sha256"),
        ("media_profile", "media-profile", "media_profile_sha256"),
        ("media_receipt", "media-receipt", "media_receipt_sha256"),
        ("evidence_profile", "evidence-profile", "evidence_profile_sha256"),
        ("evidence_receipt", "evidence-receipt", "evidence_receipt_sha256"),
        ("cleanup_contract", "cleanup-contract", "cleanup_contract_sha256"),
    ]
    documents: dict[str, dict[str, Any]] = {}
    for key, option_name, hash_attr in bindings:
        raw_path = str(getattr(args, key, "") or "").strip()
        expected_hash = str(getattr(args, hash_attr, "") or "").strip().lower()
        if not raw_path:
            raise ProjectRunnerError(f"--{option_name} is required")
        if not SHA256_PATTERN.fullmatch(expected_hash):
            raise ProjectRunnerError(
                f"--{option_name}-sha256 must be 64 lowercase hex characters"
            )
        documents[key] = load_hash_pinned_json(
            Path(raw_path),
            role=key.replace("_", "."),
            expected_sha256=expected_hash,
            checked_schema=SCHEMA_ROOT / INPUT_SCHEMA_FILES[key],
        )

    risk_tier = str(getattr(args, "risk_tier", "") or "").strip()
    if risk_tier not in RISK_RANK:
        raise ProjectRunnerError(
            "risk_tier must be one of " + ", ".join(ALLOWED_RISK_TIERS)
        )

    validate_project_spec(documents["project_spec"]["document"])
    validate_product_lock(documents["product_lock"]["document"])
    validate_project_product_closure(documents)
    expected_binding = expected_product_binding(documents)
    for role in ("topology", "media", "evidence"):
        profile = documents[f"{role}_profile"]["document"]
        receipt_binding = documents[f"{role}_receipt"]
        validate_profile(profile, role, expected_binding=expected_binding)
        receipt_binding["owner_receipt"] = validate_owner_receipt_binding(
            receipt_binding["document"],
            role,
            profile=profile,
            profile_sha256=documents[f"{role}_profile"]["ref"]["sha256"],
            expected_binding=expected_binding,
            now=now,
            risk_tier=risk_tier,
            binding_path=Path(receipt_binding["ref"]["path"]),
        )

    validate_cleanup_contract(documents["cleanup_contract"]["document"])
    capability_ids = normalized_capability_ids(getattr(args, "capability_id", None))
    validate_capability_selection(capability_ids, documents["product_lock"]["document"])
    documents["capability_ids"] = {"values": capability_ids}
    documents["risk_tier"] = {"value": risk_tier}
    validate_risk_gates(documents, risk_tier)
    validate_qcl_input_lanes(documents)
    return documents


def load_hash_pinned_json(
    path: Path,
    *,
    role: str,
    expected_sha256: str,
    checked_schema: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise ProjectRunnerError(f"{role} file does not exist: {path}")
    payload = path.read_bytes()
    observed_hash = hashlib.sha256(payload).hexdigest()
    if observed_hash != expected_sha256:
        raise ProjectRunnerError(
            f"{role} SHA256 drift: expected {expected_sha256}, observed {observed_hash}"
        )
    document = json.loads(payload.decode("utf-8"))
    if not isinstance(document, dict):
        raise ProjectRunnerError(f"{role} must contain one JSON object")
    load_and_validate_checked_schema(document, checked_schema, label=role)
    schema = schema_id(document)
    if not schema:
        raise ProjectRunnerError(f"{role} must declare an owner schema")
    return {
        "document": document,
        "ref": {
            "role": role,
            "path": str(path.resolve()),
            "sha256": observed_hash,
            "schema": schema,
            "owner": schema_owner(schema),
        },
    }


def validate_project_spec(document: dict[str, Any]) -> None:
    if document.get("schema") != PROJECT_SPEC_SCHEMA:
        raise ProjectRunnerError("project spec must use project_spec.v2")
    activation = object_value(document.get("activation_model"))
    if activation.get("runtime_rule") != "selected-lock-and-runtime-input":
        raise ProjectRunnerError(
            "project spec v2 must use selected-lock-and-runtime-input activation"
        )
    composition = object_value(document.get("composition"))
    for field in (
        "selected_features",
        "denied_features",
        "selected_modules",
        "denied_modules",
        "allowed_permissions",
        "denied_permissions",
    ):
        require_unique_list(composition[field], f"project composition {field}")
    selected_modules = set(map(str, composition["selected_modules"]))
    denied_modules = set(map(str, composition["denied_modules"]))
    if selected_modules & denied_modules:
        raise ProjectRunnerError("project selected_modules and denied_modules overlap")
    module_rows = list_value(document.get("modules"))
    selected_rows = {
        str(object_value(row).get("module_id"))
        for row in module_rows
        if object_value(row).get("selected") is True
    }
    denied_rows = {
        str(object_value(row).get("module_id"))
        for row in module_rows
        if object_value(row).get("selected") is False
    }
    if selected_modules != selected_rows or denied_modules != denied_rows:
        raise ProjectRunnerError(
            "project composition module selections must exactly match modules[].selected"
        )


def validate_product_lock(document: dict[str, Any]) -> None:
    if document.get("$schema") != PRODUCT_LOCK_SCHEMA:
        raise ProjectRunnerError("product lock must use rusty.manifold.broker.product_lock.v1")
    if document.get("lock_id") != f"lock.{document.get('product_id', '')}":
        raise ProjectRunnerError("product lock identity must be lock.<product_id>")
    if not FINGERPRINT_PATTERN.fullmatch(str(document.get("spec_fingerprint") or "")):
        raise ProjectRunnerError("product lock requires an fnv1a64-<16 lowercase hex> fingerprint")
    if bool(document.get("standalone_enabled")) == bool(document.get("embedded_enabled")):
        raise ProjectRunnerError("product lock must select exactly one broker placement mode")
    for field in ("features", "command_ids", "stream_ids", "module_ids", "permissions"):
        require_unique_list(document[field], f"product lock {field}")


def validate_project_product_closure(documents: dict[str, dict[str, Any]]) -> None:
    project_spec = documents["project_spec"]["document"]
    product_lock = documents["product_lock"]["document"]
    composition = project_spec["composition"]
    expected_features = {
        normalize_feature_id(str(value)) for value in composition["selected_features"]
    }
    denied_features = {
        normalize_feature_id(str(value)) for value in composition["denied_features"]
    }
    expected_modules = {
        normalize_module_id(str(value)) for value in composition["selected_modules"]
    }
    denied_modules = {
        normalize_module_id(str(value)) for value in composition["denied_modules"]
    }
    expected_permissions = set(map(str, composition["allowed_permissions"]))
    denied_permissions = set(map(str, composition["denied_permissions"]))

    observed_features = set(map(str, product_lock["features"]))
    observed_modules = set(map(str, product_lock["module_ids"]))
    observed_permissions = set(map(str, product_lock["permissions"]))
    mismatches = []
    if observed_features != expected_features:
        mismatches.append("selected features")
    if observed_modules != expected_modules:
        mismatches.append("selected modules")
    if observed_permissions != expected_permissions:
        mismatches.append("allowed permissions")
    if observed_features & denied_features:
        mismatches.append("denied features")
    if observed_modules & denied_modules:
        mismatches.append("denied modules")
    if observed_permissions & denied_permissions:
        mismatches.append("denied permissions")
    if mismatches:
        raise ProjectRunnerError(
            "project spec does not resolve to the exact product-lock closure: "
            + ", ".join(mismatches)
        )


def expected_product_binding(documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    project = documents["project_spec"]
    product = documents["product_lock"]
    return {
        "project_id": project["document"]["project_id"],
        "project_revision": project["document"]["revision"],
        "project_spec_sha256": project["ref"]["sha256"],
        "product_id": product["document"]["product_id"],
        "product_lock_id": product["document"]["lock_id"],
        "product_lock_revision": project["document"]["revision"],
        "product_lock_fingerprint": product["document"]["spec_fingerprint"],
        "product_lock_sha256": product["ref"]["sha256"],
    }


def validate_profile(
    document: dict[str, Any],
    role: str,
    *,
    expected_binding: dict[str, Any],
) -> None:
    if schema_id(document) != PROFILE_SCHEMAS[role]:
        raise ProjectRunnerError(f"{role} profile must use {PROFILE_SCHEMAS[role]}")
    if document.get("owner") != PROFILE_OWNERS[role]:
        raise ProjectRunnerError(f"{role} profile owner must be {PROFILE_OWNERS[role]}")
    if document.get("owner_schema") != PROFILE_OWNER_SCHEMAS[role]:
        raise ProjectRunnerError(f"{role} profile owner_schema is wrong")
    if document.get("receipt_schema") != PROFILE_RECEIPT_SCHEMAS[role]:
        raise ProjectRunnerError(f"{role} profile receipt_schema is wrong")
    if document.get("binding_schema") != PROFILE_BINDING_SCHEMAS[role]:
        raise ProjectRunnerError(f"{role} profile binding_schema is wrong")
    if document.get("product_binding") != expected_binding:
        raise ProjectRunnerError(
            f"{role} profile product_binding must exactly bind the selected project and lock"
        )
    if role == "evidence":
        if document.get("namespace_role") != "validation-profile":
            raise ProjectRunnerError(
                "evidence profile must declare namespace_role=validation-profile"
            )
    else:
        require_non_qcl_value(str(document["profile_id"]), f"{role} profile_id")


def validate_owner_receipt_binding(
    document: dict[str, Any],
    role: str,
    *,
    profile: dict[str, Any],
    profile_sha256: str,
    expected_binding: dict[str, Any],
    now: str,
    risk_tier: str,
    binding_path: Path,
) -> dict[str, Any]:
    if schema_id(document) != str(profile["binding_schema"]):
        raise ProjectRunnerError(
            f"{role} receipt binding must use {profile['binding_schema']}"
        )
    if document.get("profile_id") != profile["profile_id"]:
        raise ProjectRunnerError(f"{role} receipt binding does not name the selected profile")
    if document.get("profile_sha256") != profile_sha256:
        raise ProjectRunnerError(f"{role} receipt binding does not hash-bind the profile")
    for field, expected in expected_binding.items():
        if document.get(field) != expected:
            raise ProjectRunnerError(
                f"{role} receipt binding {field} does not bind the exact project/product lock"
            )
    owner_receipt = load_owner_receipt_ref(
        document.get("owner_receipt_ref"),
        role=role,
        binding_path=binding_path,
        expected_schema=str(profile["receipt_schema"]),
        expected_owner=PROFILE_OWNERS[role],
    )
    owner_document = owner_receipt["document"]
    reject_qcl_recursively(
        owner_document,
        label=f"owner_{role}_receipt",
        allowed_paths={("validation_profile_ref",)} if role == "evidence" else set(),
    )
    authority = profile["authority"]
    revision = int(document["authority_revision"])
    if revision < int(authority["minimum_revision"]):
        raise ProjectRunnerError(f"{role} receipt authority revision is stale")
    issued = parse_utc(str(document["issued_at_utc"]), f"{role} issued_at_utc")
    expires = parse_utc(str(document["expires_at_utc"]), f"{role} expires_at_utc")
    observed_now = parse_utc(now, "planner clock")
    if issued > observed_now:
        raise ProjectRunnerError(f"{role} receipt is future-dated")
    if expires <= observed_now or expires <= issued:
        raise ProjectRunnerError(f"{role} receipt is expired")
    age_seconds = (observed_now - issued).total_seconds()
    max_age = min(
        int(authority["max_age_seconds"]),
        RISK_MAX_RECEIPT_AGE_SECONDS[risk_tier],
    )
    if age_seconds > max_age:
        raise ProjectRunnerError(f"{role} receipt freshness window exceeded")

    observations = object_value(document.get("observations"))
    required_observations = list_value(profile.get("required_observations"))
    missing = sorted(
        str(name) for name in required_observations if observations.get(str(name)) is not True
    )
    if missing:
        raise ProjectRunnerError(
            f"{role} receipt is missing required observations: {', '.join(missing)}"
        )

    expectations = object_value(profile.get("receipt_expectations"))
    if role == "topology":
        if int(owner_document["authority_revision"]) != revision:
            raise ProjectRunnerError("topology authority revision does not match owner receipt")
        if owner_document.get("authorized") is not True:
            raise ProjectRunnerError("topology receipt must be authorized")
        if owner_document.get("topology_contract_id") != expectations.get(
            "topology_contract_id"
        ):
            raise ProjectRunnerError("topology owner receipt contract is not selected")
        if document.get("local_peer_role") != expectations.get("local_peer_role"):
            raise ProjectRunnerError("topology receipt binding local role is not selected")
    elif role == "media":
        if owner_document.get("mode") != expectations.get("mode"):
            raise ProjectRunnerError("media receipt does not match the selected runtime mode")
        if owner_document.get("product_lock_id") != expected_binding["product_lock_id"]:
            raise ProjectRunnerError("media owner receipt product lock id drifted")
        if owner_document.get("product_lock_fingerprint") != expected_binding[
            "product_lock_fingerprint"
        ]:
            raise ProjectRunnerError("media owner receipt product lock fingerprint drifted")
        application = object_value(owner_document.get("application"))
        if application.get("applied") is not True:
            raise ProjectRunnerError("media receipt application must be applied")
        if application.get("resulting_authority_revision") != revision:
            raise ProjectRunnerError(
                "media receipt authority revision must match the application receipt"
            )
    else:
        if str(owner_document.get("status") or "").lower() != "pass":
            raise ProjectRunnerError("evidence receipt status must be pass")
        if owner_document.get("validation_profile_ref") != profile["profile_id"]:
            raise ProjectRunnerError("evidence receipt validation profile reference drifted")
        if owner_document.get("cleanup_complete") is not True:
            raise ProjectRunnerError("evidence owner receipt cleanup must be complete")
        if document.get("fatal_count") != 0 or observations.get("zero_fatals") is not True:
            raise ProjectRunnerError("evidence receipt must prove an exact zero-fatal window")
    return owner_receipt


def load_owner_receipt_ref(
    raw_ref: Any,
    *,
    role: str,
    binding_path: Path,
    expected_schema: str,
    expected_owner: str,
) -> dict[str, Any]:
    ref = object_value(raw_ref)
    if ref.get("schema") != expected_schema or ref.get("owner") != expected_owner:
        raise ProjectRunnerError(
            f"{role} owner receipt ref must bind exact schema and owner"
        )
    expected_hash = str(ref.get("sha256") or "")
    if not SHA256_PATTERN.fullmatch(expected_hash):
        raise ProjectRunnerError(f"{role} owner receipt ref requires lowercase SHA-256")
    raw_path = Path(str(ref.get("path") or ""))
    if not str(raw_path):
        raise ProjectRunnerError(f"{role} owner receipt ref path is missing")
    resolved = raw_path if raw_path.is_absolute() else binding_path.parent / raw_path
    loaded = load_hash_pinned_json(
        resolved.resolve(),
        role=f"owner.{role}.receipt",
        expected_sha256=expected_hash,
        checked_schema=SCHEMA_ROOT / OWNER_RECEIPT_SCHEMA_FILES[role],
    )
    if schema_id(loaded["document"]) != expected_schema:
        raise ProjectRunnerError(f"{role} owner receipt document schema drifted")
    loaded["ref"]["role"] = f"owner.{role}.receipt"
    if loaded["ref"]["owner"] != expected_owner:
        raise ProjectRunnerError(f"{role} owner receipt document owner drifted")
    return loaded


def validate_cleanup_contract(document: dict[str, Any]) -> None:
    if document.get("$schema") != CLEANUP_CONTRACT_SCHEMA:
        raise ProjectRunnerError("unsupported cleanup contract schema")
    kinds: set[str] = set()
    for index, raw_step in enumerate(document["steps"]):
        step = object_value(raw_step)
        if step.get("required") is not True:
            raise ProjectRunnerError(f"cleanup step {index} must be required")
        kinds.add(str(step["kind"]))
    if len(kinds) != len(document["steps"]):
        raise ProjectRunnerError("cleanup contract kinds must be unique")
    if not all(object_value(row).get("required") is True for row in document["terminal_assertions"]):
        raise ProjectRunnerError("all cleanup terminal assertions must be required")


def normalized_capability_ids(raw_values: Any) -> list[str]:
    values = [str(value).strip() for value in list_value(raw_values) if str(value).strip()]
    if not values:
        raise ProjectRunnerError("at least one --capability-id is required")
    if len(values) != len(set(values)):
        raise ProjectRunnerError("capability IDs must be unique")
    for value in values:
        require_non_qcl_value(value, "capability_id")
    return sorted(values)


def validate_capability_selection(
    capability_ids: list[str], product_lock: dict[str, Any]
) -> None:
    allowed: set[str] = set()
    for field in ("features", "command_ids", "stream_ids", "module_ids"):
        allowed.update(map(str, product_lock[field]))
    missing = sorted(set(capability_ids) - allowed)
    if missing:
        raise ProjectRunnerError(
            "capability IDs are absent from the exact product lock: " + ", ".join(missing)
        )


def validate_risk_gates(
    documents: dict[str, dict[str, Any]], risk_tier: str
) -> None:
    cleanup_kinds = {
        str(object_value(step)["kind"])
        for step in documents["cleanup_contract"]["document"]["steps"]
    }
    missing_cleanup = sorted(RISK_REQUIRED_CLEANUP_KINDS[risk_tier] - cleanup_kinds)
    if missing_cleanup:
        raise ProjectRunnerError(
            f"{risk_tier} risk tier is missing cleanup gates: {', '.join(missing_cleanup)}"
        )

    evidence = documents["evidence_receipt"]["document"]
    evidence_tier = str(evidence["evidence_tier"])
    if RISK_RANK[evidence_tier] < RISK_RANK[risk_tier]:
        raise ProjectRunnerError(
            f"{risk_tier} risk tier requires evidence at least {risk_tier}, observed {evidence_tier}"
        )
    observations = object_value(evidence.get("observations"))
    missing_observations = sorted(
        name
        for name in RISK_REQUIRED_EVIDENCE_OBSERVATIONS[risk_tier]
        if observations.get(name) is not True
    )
    if missing_observations:
        raise ProjectRunnerError(
            f"{risk_tier} risk tier is missing evidence gates: "
            + ", ".join(missing_observations)
        )

    if RISK_RANK[risk_tier] >= RISK_RANK["device"]:
        device = object_value(evidence.get("device_evidence"))
        for field in (
            "serials_redacted",
            "validation_passed",
            "cleanup_complete",
            "packages_removed",
            "zero_fatals",
        ):
            if device.get(field) is not True:
                raise ProjectRunnerError(f"device risk gate requires device_evidence.{field}=true")
        if int(device.get("device_count") or 0) < 1:
            raise ProjectRunnerError("device risk gate requires at least one device")

    if risk_tier == "release":
        release = object_value(evidence.get("release_evidence"))
        for field in (
            "source_checks_passed",
            "owner_checks_passed",
            "device_checks_passed",
            "cleanup_complete",
            "zero_fatals",
        ):
            if release.get(field) is not True:
                raise ProjectRunnerError(f"release risk gate requires release_evidence.{field}=true")
        refs = list_value(release.get("owner_release_receipts"))
        if not refs:
            raise ProjectRunnerError("release risk gate requires owner release receipts")
        reverify_input_refs(refs)


def validate_qcl_input_lanes(documents: dict[str, dict[str, Any]]) -> None:
    for role in (
        "project_spec",
        "product_lock",
        "topology_profile",
        "topology_receipt",
        "media_profile",
        "media_receipt",
        "cleanup_contract",
    ):
        reject_qcl_recursively(documents[role]["document"], label=role)
    reject_qcl_recursively(
        documents["evidence_profile"]["document"],
        label="evidence_profile",
        allowed_paths={("profile_id",)},
    )
    reject_qcl_recursively(
        documents["evidence_receipt"]["document"],
        label="evidence_receipt",
        allowed_paths={("validation_profile_ref",), ("profile_id",)},
    )


def reject_qcl_recursively(
    value: Any,
    *,
    label: str,
    allowed_paths: set[tuple[str, ...]] | None = None,
    path: tuple[str, ...] = (),
) -> None:
    allowed_paths = allowed_paths or set()
    if isinstance(value, dict):
        for key, child in value.items():
            reject_qcl_recursively(
                child,
                label=label,
                allowed_paths=allowed_paths,
                path=path + (str(key),),
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_qcl_recursively(
                child,
                label=label,
                allowed_paths=allowed_paths,
                path=path + (str(index),),
            )
    elif isinstance(value, str) and QCL_IDENTIFIER_PATTERN.search(value):
        if not any(path[-len(allowed) :] == allowed for allowed in allowed_paths):
            raise ProjectRunnerError(
                f"{label} QCL identifier is outside the evidence-profile lane at "
                + ".".join(path)
            )


def build_project_runner_envelope(
    args: argparse.Namespace,
    documents: dict[str, dict[str, Any]],
    *,
    run_id: str,
    generation_id: str,
    now: str,
) -> dict[str, Any]:
    project_spec = documents["project_spec"]["document"]
    product_lock = documents["product_lock"]["document"]
    binding = expected_product_binding(documents)
    input_refs = [
        documents[key]["ref"]
        for key in (
            "project_spec",
            "product_lock",
            "topology_profile",
            "topology_receipt",
            "media_profile",
            "media_receipt",
            "evidence_profile",
            "evidence_receipt",
            "cleanup_contract",
        )
    ]
    input_refs.extend(
        documents[f"{role}_receipt"]["owner_receipt"]["ref"]
        for role in ("topology", "media", "evidence")
    )
    return {
        "$schema": PROJECT_RUNNER_ENVELOPE_SCHEMA,
        "schema_version": 1,
        "generation_id": generation_id,
        "run_id": run_id,
        "generated_at_utc": now,
        "dry_run": True,
        "project": {
            "project_id": project_spec["project_id"],
            "revision": project_spec["revision"],
            "sha256": documents["project_spec"]["ref"]["sha256"],
        },
        "product": {
            **binding,
            "closure": {
                "selected_features": product_lock["features"],
                "denied_features": project_spec["composition"]["denied_features"],
                "selected_modules": product_lock["module_ids"],
                "denied_modules": project_spec["composition"]["denied_modules"],
                "allowed_permissions": product_lock["permissions"],
                "denied_permissions": project_spec["composition"]["denied_permissions"],
            },
        },
        "capability_ids": documents["capability_ids"]["values"],
        "profile_ids": {
            role: documents[f"{role}_profile"]["document"]["profile_id"]
            for role in ("topology", "media", "evidence")
        },
        "risk_tier": str(args.risk_tier),
        "risk_gates": risk_gate_summary(str(args.risk_tier)),
        "inputs": input_refs,
        "authority": {
            "planner": "rusty.hostess",
            "runtime_execution": "external-owner-adapters",
            "product_lock": "rusty.manifold",
            "platform": "rusty.quest",
        },
    }


def build_project_runner_plan(
    envelope: dict[str, Any],
    documents: dict[str, dict[str, Any]],
    *,
    envelope_ref: dict[str, Any],
    run_id: str,
    generation_id: str,
    now: str,
) -> dict[str, Any]:
    return {
        "$schema": PROJECT_RUNNER_PLAN_SCHEMA,
        "schema_version": 1,
        "generation_id": generation_id,
        "plan_id": f"plan.{run_id}",
        "run_id": run_id,
        "generated_at_utc": now,
        "dry_run": True,
        "execution_state": "planned",
        "envelope": envelope_ref,
        "input_refs": envelope["inputs"],
        "steps": [
            plan_step("verify.exact-inputs-and-closure", "rusty.hostess", [], []),
            plan_step(
                "adopt.topology-profile",
                str(documents["topology_profile"]["document"]["owner"]),
                ["topology.profile", "product.lock"],
                ["topology.receipt"],
            ),
            plan_step(
                "adopt.media-profile",
                str(documents["media_profile"]["document"]["owner"]),
                ["media.profile", "topology.receipt", "product.lock"],
                ["media.receipt"],
            ),
            plan_step(
                "collect.validation-evidence",
                str(documents["evidence_profile"]["document"]["owner"]),
                ["evidence.profile", "media.receipt", "product.lock"],
                ["evidence.receipt"],
            ),
            plan_step(
                "verify.risk-and-cleanup-gates",
                "rusty.hostess",
                ["cleanup.contract", "evidence.receipt"],
                ["cleanup.owner-receipts"],
            ),
        ],
        "cleanup": {
            "contract": documents["cleanup_contract"]["ref"],
            "required_kinds": sorted(RISK_REQUIRED_CLEANUP_KINDS[envelope["risk_tier"]]),
            "execution": "not-performed-in-dry-run",
        },
        "risk_gates": envelope["risk_gates"],
        "constraints": {
            "qcl_role": "evidence-profile-reference-only",
            "owner_payload_embedding": False,
            "device_mutation": False,
            "git_mutation": False,
            "completion_marker_required": True,
        },
    }


def build_project_runner_receipt(
    envelope: dict[str, Any],
    documents: dict[str, dict[str, Any]],
    *,
    envelope_ref: dict[str, Any],
    plan_ref: dict[str, Any],
    run_id: str,
    generation_id: str,
    now: str,
) -> dict[str, Any]:
    return {
        "$schema": PROJECT_RUNNER_RECEIPT_SCHEMA,
        "schema_version": 1,
        "generation_id": generation_id,
        "receipt_id": f"receipt.{run_id}",
        "run_id": run_id,
        "generated_at_utc": now,
        "status": "planned",
        "dry_run": True,
        "executed": False,
        "project": envelope["project"],
        "product": envelope["product"],
        "envelope": envelope_ref,
        "plan": plan_ref,
        "owner_receipts": [
            {
                **documents[f"{role}_receipt"]["owner_receipt"]["ref"],
                "binding": documents[f"{role}_receipt"]["ref"],
                "profile_id": documents[f"{role}_profile"]["document"]["profile_id"],
                "authority_revision": documents[f"{role}_receipt"]["document"][
                    "authority_revision"
                ],
                "expires_at_utc": documents[f"{role}_receipt"]["document"]["expires_at_utc"],
            }
            for role in ("topology", "media", "evidence")
        ],
        "cleanup": {
            "contract": documents["cleanup_contract"]["ref"],
            "required_kinds": sorted(RISK_REQUIRED_CLEANUP_KINDS[envelope["risk_tier"]]),
            "status": "required-before-execution-acceptance",
        },
        "risk_gates": envelope["risk_gates"],
        "validation": {
            "status": "pass",
            "checked_in_schemas_verified": True,
            "exact_hashes_verified": True,
            "project_product_closure_exact": True,
            "owner_receipts_profile_lock_bound": True,
            "owner_receipts_fresh": True,
            "capabilities_in_product_lock": True,
            "qcl_lane_leakage": False,
            "output_schema_owner": "rusty.hostess",
            "completion_marker_required": True,
        },
    }


def build_generation_completion(
    *,
    run_id: str,
    generation_id: str,
    now: str,
    artifact_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "$schema": PROJECT_RUNNER_COMPLETION_SCHEMA,
        "schema_version": 1,
        "generation_id": generation_id,
        "run_id": run_id,
        "completed_at_utc": now,
        "status": "complete",
        "artifacts": artifact_refs,
    }


def build_project_runner_projection(
    *,
    completion_path: Path,
    completion: dict[str, Any],
    envelope: dict[str, Any],
    plan: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = [
        {
            "row_id": "project-product-closure",
            "kind": "closure",
            "title": "Exact project and product closure",
            "status": "pass",
            "owner": "rusty.hostess",
            "detail": (
                f"{envelope['project']['project_id']} r{envelope['project']['revision']} / "
                f"{envelope['product']['product_lock_id']} "
                f"r{envelope['product']['product_lock_revision']} / "
                f"{envelope['product']['product_lock_fingerprint']}"
            ),
        }
    ]
    for step in plan["steps"]:
        rows.append(
            {
                "row_id": str(step["step_id"]),
                "kind": "plan_step",
                "title": str(step["step_id"]),
                "status": "planned",
                "owner": str(step["owner"]),
                "detail": (
                    "inputs=" + ",".join(step["input_roles"])
                    + "; receipts=" + ",".join(step["required_receipt_roles"])
                ),
            }
        )
    for owner_receipt in receipt["owner_receipts"]:
        rows.append(
            {
                "row_id": "owner-" + str(owner_receipt["role"]),
                "kind": "owner_receipt",
                "title": "Owner receipt: " + str(owner_receipt["role"]),
                "status": "bound",
                "owner": str(owner_receipt["owner"]),
                "detail": (
                    f"authority revision {owner_receipt['authority_revision']}; "
                    f"expires {owner_receipt['expires_at_utc']}"
                ),
            }
        )
    rows.append(
        {
            "row_id": "cleanup-gates",
            "kind": "cleanup",
            "title": "Required cleanup gates",
            "status": "required",
            "owner": "rusty.hostess",
            "detail": ",".join(receipt["cleanup"]["required_kinds"]),
        }
    )
    return {
        "$schema": PROJECT_RUNNER_PROJECTION_SCHEMA,
        "schema_version": 1,
        "generation_id": completion["generation_id"],
        "run_id": completion["run_id"],
        "status": "complete",
        "completion_marker": str(completion_path),
        "risk_tier": envelope["risk_tier"],
        "project_id": envelope["project"]["project_id"],
        "product_lock_id": envelope["product"]["product_lock_id"],
        "product_lock_revision": envelope["product"]["product_lock_revision"],
        "product_lock_fingerprint": envelope["product"]["product_lock_fingerprint"],
        "dry_run": True,
        "executed": False,
        "rows": rows,
    }


def risk_gate_summary(risk_tier: str) -> dict[str, Any]:
    return {
        "tier": risk_tier,
        "required_evidence_observations": sorted(
            RISK_REQUIRED_EVIDENCE_OBSERVATIONS[risk_tier]
        ),
        "required_cleanup_kinds": sorted(RISK_REQUIRED_CLEANUP_KINDS[risk_tier]),
        "max_receipt_age_seconds": RISK_MAX_RECEIPT_AGE_SECONDS[risk_tier],
        "device_gate_required": RISK_RANK[risk_tier] >= RISK_RANK["device"],
        "release_gate_required": risk_tier == "release",
    }


def plan_step(
    step_id: str,
    owner: str,
    input_roles: list[str],
    required_receipt_roles: list[str],
) -> dict[str, Any]:
    require_non_qcl_value(step_id, "plan step_id")
    return {
        "step_id": step_id,
        "owner": owner,
        "input_roles": input_roles,
        "required_receipt_roles": required_receipt_roles,
        "mode": "declarative",
    }


def validate_hostess_output_document(document: dict[str, Any], label: str) -> None:
    schema = str(document.get("$schema") or "")
    schema_file = OUTPUT_SCHEMA_FILES.get(schema)
    if not schema.startswith("rusty.hostess.") or schema_file is None:
        raise ProjectRunnerError(
            f"{label} output schema must be a checked-in rusty.hostess schema, "
            f"observed {schema or '<missing>'}"
        )
    load_and_validate_checked_schema(document, SCHEMA_ROOT / schema_file, label=label)


def validate_output_qcl_lanes(document: dict[str, Any], label: str) -> None:
    reject_qcl_recursively(
        document,
        label=label,
        allowed_paths={("profile_ids", "evidence"), ("profile_id",)},
    )


def generated_artifact_ref(
    role: str,
    path: Path,
    schema: str,
    document: dict[str, Any],
) -> dict[str, Any]:
    return {
        "role": role,
        "path": str(path),
        "sha256": hashlib.sha256(serialized_json(document)).hexdigest(),
        "schema": schema,
        "owner": "rusty.hostess",
    }


def validate_output_paths(output_paths: list[Path], input_paths: list[Path]) -> None:
    output_keys = [normalized_path_key(path) for path in output_paths]
    if len(output_keys) != len(set(output_keys)):
        raise ProjectRunnerError("project runner output paths must be distinct")
    input_keys = {normalized_path_key(path) for path in input_paths}
    collisions = [str(path) for path, key in zip(output_paths, output_keys) if key in input_keys]
    if collisions:
        raise ProjectRunnerError(
            "project runner outputs must not overwrite declarative inputs: "
            + ", ".join(collisions)
        )


def publish_generation(
    outputs: list[tuple[Path, Path, dict[str, Any]]],
    *,
    completion_out: Path,
    completion: dict[str, Any],
    replace_func: Callable[[Path, Path], None] | None = None,
) -> None:
    """Publish one immutable generation, aliases, then the marker.

    The marker references only files inside the immutable generation
    directory. A failed refresh leaves any previous marker valid; partially
    replaced convenience aliases are never acceptance evidence.
    """

    replace = replace_func or (lambda source, destination: source.replace(destination))
    authoritative_parents = {path.parent for _, path, _ in outputs}
    if len(authoritative_parents) != 1:
        raise ProjectRunnerError("authoritative generation outputs need one directory")
    generation_dir = authoritative_parents.pop()
    generation_root = generation_dir.parent
    generation_root.mkdir(parents=True, exist_ok=True)
    if generation_dir.exists():
        raise ProjectRunnerError(f"generation directory already exists: {generation_dir}")
    staged_generation = generation_root / f".{generation_dir.name}.{uuid4().hex}.tmp"
    staged_aliases: list[tuple[Path, Path]] = []
    staged_completion: Path | None = None
    try:
        staged_generation.mkdir(parents=False, exist_ok=False)
        for alias, authoritative, document in outputs:
            (staged_generation / authoritative.name).write_bytes(serialized_json(document))
            alias.parent.mkdir(parents=True, exist_ok=True)
            temporary = alias.with_name(f".{alias.name}.{uuid4().hex}.tmp")
            temporary.write_bytes(serialized_json(document))
            staged_aliases.append((temporary, alias))

        # One directory replacement publishes the immutable snapshot.
        replace(staged_generation, generation_dir)
        # Aliases remain convenient but are not referenced by the marker.
        for source, destination in staged_aliases:
            replace(source, destination)

        completion_out.parent.mkdir(parents=True, exist_ok=True)
        staged_completion = completion_out.with_name(
            f".{completion_out.name}.{uuid4().hex}.tmp"
        )
        staged_completion.write_bytes(serialized_json(completion))
        # The marker is the sole acceptance point and is always replaced last.
        replace(staged_completion, completion_out)
    finally:
        for source, _ in staged_aliases:
            source.unlink(missing_ok=True)
        if staged_completion is not None:
            staged_completion.unlink(missing_ok=True)
        if staged_generation.exists():
            shutil.rmtree(staged_generation)


def reverify_input_refs(input_refs: list[dict[str, Any]]) -> None:
    for ref in input_refs:
        path = Path(str(ref.get("path") or ""))
        expected = str(ref.get("sha256") or "")
        if not path.is_file() or not SHA256_PATTERN.fullmatch(expected):
            raise ProjectRunnerError(f"invalid or missing referenced artifact: {path}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise ProjectRunnerError(
                f"{ref.get('role', 'artifact')} changed after validation: "
                f"expected {expected}, observed {observed}"
            )


def read_checked_hostess_output(
    path: Path,
    *,
    expected_schema: str,
    label: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise ProjectRunnerError(f"{label} does not exist: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("$schema") != expected_schema:
        raise ProjectRunnerError(f"{label} schema mismatch")
    validate_hostess_output_document(document, label)
    validate_output_qcl_lanes(document, label)
    return document


def require_unique_list(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise ProjectRunnerError(f"{label} must be an array")
    encoded = [json.dumps(item, sort_keys=True) for item in value]
    if len(encoded) != len(set(encoded)):
        raise ProjectRunnerError(f"{label} must not contain duplicates")


def normalize_feature_id(value: str) -> str:
    return value.replace("-", "_")


def normalize_module_id(value: str) -> str:
    return "module." + value.replace("-", ".")


def require_non_qcl_value(value: str, label: str) -> None:
    if QCL_IDENTIFIER_PATTERN.search(value):
        raise ProjectRunnerError(f"{label} must not contain a QCL validation identifier: {value}")


def schema_id(document: dict[str, Any]) -> str:
    canonical = str(document.get("schema") or "")
    if canonical.startswith("rusty."):
        return canonical
    return str(document.get("$schema") or "")


def schema_owner(schema: str) -> str:
    for prefix in ("rusty.hostess", "rusty.manifold", "rusty.quest", "rusty.morphospace"):
        if schema.startswith(prefix + "."):
            return prefix
    return "external"


def serialized_json(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def normalized_path_key(path: Path) -> str:
    return str(path.resolve(strict=False)).casefold()


def compact_timestamp(value: str) -> str:
    return re.sub(r"[^0-9]", "", value)[:14] or "run"


def parse_utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectRunnerError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ProjectRunnerError(f"{label} must include a timezone")
    return parsed.astimezone(UTC)


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = [
    "CLEANUP_CONTRACT_SCHEMA",
    "PRODUCT_LOCK_SCHEMA",
    "PROJECT_RUNNER_COMPLETION_SCHEMA",
    "PROJECT_RUNNER_ENVELOPE_SCHEMA",
    "PROJECT_RUNNER_PLAN_SCHEMA",
    "PROJECT_RUNNER_PROJECTION_SCHEMA",
    "PROJECT_RUNNER_RECEIPT_SCHEMA",
    "ProjectRunnerError",
    "build_generation_completion",
    "build_project_runner_envelope",
    "build_project_runner_plan",
    "build_project_runner_receipt",
    "load_project_runner_inputs",
    "publish_generation",
    "run_project_runner",
    "run_project_runner_inspect",
    "validate_hostess_output_document",
]
