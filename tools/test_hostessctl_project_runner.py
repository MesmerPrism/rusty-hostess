from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.hostessctl.cli_parser import build_hostessctl_parser
from tools.hostessctl.project_runner import (
    PROJECT_RUNNER_COMPLETION_SCHEMA,
    PROJECT_RUNNER_ENVELOPE_SCHEMA,
    PROJECT_RUNNER_PLAN_SCHEMA,
    PROJECT_RUNNER_PROJECTION_SCHEMA,
    PROJECT_RUNNER_RECEIPT_SCHEMA,
    ProjectRunnerError,
    run_project_runner,
    run_project_runner_inspect,
    validate_hostess_output_document,
)
from tools.hostessctl.schema_ownership import build_schema_ownership_audit


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "fixtures/project-runner/valid"
OWNERSHIP_INVENTORY = (
    REPO_ROOT / "fixtures/schema-ownership/foreign-schema-compatibility.json"
)


class HostessCtlProjectRunnerTests(unittest.TestCase):
    def test_valid_dry_run_writes_hostess_envelope_plan_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "project-run.receipt.json"
            args = runner_args(out)
            status = run_project_runner(
                args,
                clock_func=lambda: "2026-07-11T12:00:00Z",
            )
            envelope_path = out.with_name("project-run.receipt.envelope.json")
            plan_path = out.with_name("project-run.receipt.plan.json")
            completion_path = out.with_name("project-run.receipt.complete.json")
            envelope = read_json(envelope_path)
            plan = read_json(plan_path)
            receipt = read_json(out)
            completion = read_json(completion_path)
            envelope_hash = sha256(envelope_path)
            plan_hash = sha256(plan_path)

        self.assertEqual(status, 0)
        self.assertEqual(envelope["$schema"], PROJECT_RUNNER_ENVELOPE_SCHEMA)
        self.assertEqual(plan["$schema"], PROJECT_RUNNER_PLAN_SCHEMA)
        self.assertEqual(receipt["$schema"], PROJECT_RUNNER_RECEIPT_SCHEMA)
        self.assertEqual(completion["$schema"], PROJECT_RUNNER_COMPLETION_SCHEMA)
        self.assertEqual(completion["status"], "complete")
        self.assertEqual(
            {row["role"] for row in completion["artifacts"]},
            {"hostess.envelope", "hostess.plan", "hostess.receipt"},
        )
        self.assertTrue(envelope["dry_run"])
        self.assertTrue(plan["dry_run"])
        self.assertFalse(receipt["executed"])
        self.assertEqual(receipt["status"], "planned")
        self.assertEqual(envelope["profile_ids"]["evidence"], "qcl-100-full-stereo")
        self.assertEqual(len(envelope["inputs"]), 12)
        self.assertEqual(len(receipt["owner_receipts"]), 3)
        self.assertEqual(
            {row["owner"] for row in receipt["owner_receipts"]},
            {"rusty.manifold", "rusty.quest"},
        )
        self.assertTrue(
            all(
                row["binding"]["schema"].startswith("rusty.hostess.")
                for row in receipt["owner_receipts"]
            )
        )
        self.assertTrue(all(ref["sha256"] == sha256(Path(ref["path"])) for ref in envelope["inputs"]))
        self.assertEqual(receipt["envelope"]["sha256"], envelope_hash)
        self.assertEqual(receipt["plan"]["sha256"], plan_hash)
        self.assertEqual(receipt["validation"]["output_schema_owner"], "rusty.hostess")
        self.assertEqual(receipt["validation"]["qcl_lane_leakage"], False)
        self.assertTrue(receipt["validation"]["checked_in_schemas_verified"])
        self.assertTrue(receipt["validation"]["project_product_closure_exact"])
        self.assertNotIn("document", json.dumps(receipt))

    def test_missing_product_lock_fails_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "run.json"
            args = runner_args(out)
            args.product_lock = str(Path(tmpdir) / "missing.lock.json")
            status = run_project_runner(args)

        self.assertEqual(status, 2)
        self.assertFalse(out.exists())

    def test_owner_receipt_hash_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            receipt_copy = root / "topology-receipt.json"
            shutil.copyfile(FIXTURE_ROOT / "topology-receipt.json", receipt_copy)
            expected = sha256(receipt_copy)
            receipt_copy.write_text(
                receipt_copy.read_text(encoding="utf-8") + " ",
                encoding="utf-8",
            )
            out = root / "run.json"
            args = runner_args(out)
            args.topology_receipt = str(receipt_copy)
            args.topology_receipt_sha256 = expected
            status = run_project_runner(args)

        self.assertEqual(status, 2)
        self.assertFalse(out.exists())

    def test_qcl_capability_runtime_id_leakage_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lock_path = root / "product-lock.json"
            lock = read_json(FIXTURE_ROOT / "product-lock.json")
            lock["features"].append("qcl-100-runtime")
            write_json(lock_path, lock)
            out = root / "run.json"
            args = runner_args(out)
            args.product_lock = str(lock_path)
            args.product_lock_sha256 = sha256(lock_path)
            args.capability_id = ["qcl-100-runtime"]
            status = run_project_runner(args)

        self.assertEqual(status, 2)
        self.assertFalse(out.exists())

    def test_unselected_qcl_product_lock_id_leakage_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lock_path = root / "product-lock.json"
            lock = read_json(FIXTURE_ROOT / "product-lock.json")
            lock["module_ids"].append("module.qcl-compat-runtime")
            write_json(lock_path, lock)
            out = root / "run.json"
            args = runner_args(out)
            args.product_lock = str(lock_path)
            args.product_lock_sha256 = sha256(lock_path)
            status = run_project_runner(args)

        self.assertEqual(status, 2)
        self.assertFalse(out.exists())

    def test_missing_cleanup_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "run.json"
            args = runner_args(out)
            args.cleanup_contract = ""
            status = run_project_runner(args)

        self.assertEqual(status, 2)
        self.assertFalse(out.exists())

    def test_foreign_output_schema_is_rejected(self) -> None:
        with self.assertRaises(ProjectRunnerError):
            validate_hostess_output_document(
                {"$schema": "rusty.quest.accidental_output.v1"},
                "damaged output",
            )

    def test_execute_request_is_explicitly_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "run.json"
            args = runner_args(out)
            args.execute = True
            status = run_project_runner(args)

        self.assertEqual(status, 2)
        self.assertFalse(out.exists())

    def test_output_path_cannot_overwrite_an_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_copy = Path(tmpdir) / "project-spec.json"
            shutil.copyfile(FIXTURE_ROOT / "project-spec.json", project_copy)
            args = runner_args(project_copy)
            args.project_spec = str(project_copy)
            args.project_spec_sha256 = sha256(project_copy)
            status = run_project_runner(args)

        self.assertEqual(status, 2)

    def test_product_permission_expansion_is_not_an_exact_project_closure(self) -> None:
        status, output_exists = run_with_mutated_input(
            "product-lock",
            lambda document: document["permissions"].append("camera"),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_selected_feature_cannot_also_be_denied_by_project(self) -> None:
        status, output_exists = run_with_mutated_input(
            "project-spec",
            lambda document: document["composition"]["denied_features"].append(
                "media-session"
            ),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_profile_cannot_bind_a_stale_lock_revision(self) -> None:
        status, output_exists = run_with_mutated_input(
            "topology-profile",
            lambda document: document["product_binding"].update(
                {"product_lock_revision": 2}
            ),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_owner_receipt_must_bind_selected_profile(self) -> None:
        status, output_exists = run_with_mutated_input(
            "topology-receipt",
            lambda document: document.update({"profile_id": "topology.wrong.profile"}),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_owner_receipt_must_bind_current_authority_revision(self) -> None:
        status, output_exists = run_with_mutated_input(
            "topology-receipt",
            lambda document: document.update({"authority_revision": 6}),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_expired_owner_receipt_is_rejected(self) -> None:
        status, output_exists = run_with_mutated_input(
            "topology-receipt",
            lambda document: document.update(
                {
                    "issued_at_utc": "2026-07-11T11:00:00Z",
                    "expires_at_utc": "2026-07-11T11:30:00Z",
                }
            ),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_zero_fatals_requires_observation_and_exact_count(self) -> None:
        def damage(document: dict[str, object]) -> None:
            document["fatal_count"] = 1
            document["observations"]["zero_fatals"] = False

        status, output_exists = run_with_mutated_input("evidence-receipt", damage)
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_unknown_input_field_is_rejected_by_checked_in_schema(self) -> None:
        status, output_exists = run_with_mutated_input(
            "media-profile",
            lambda document: document.update({"ambient_permission_union": True}),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_recursive_qcl_leakage_in_topology_receipt_is_rejected(self) -> None:
        status, output_exists = run_with_mutated_owner_receipt(
            "topology",
            lambda document: document.update(
                {"topology_contract_id": "rusty.quest.qcl-100-runtime-topology.v1"}
            ),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_deep_risk_tier_rejects_standard_only_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "run.json"
            args = runner_args(out)
            args.risk_tier = "deep"
            status = run_project_runner(
                args,
                clock_func=lambda: "2026-07-11T12:00:00Z",
            )
        self.assertEqual(status, 2)

    def test_device_risk_tier_requires_device_cleanup_contract_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "run.json"
            args = runner_args(out)
            args.risk_tier = "device"
            status = run_project_runner(
                args,
                clock_func=lambda: "2026-07-11T12:00:00Z",
            )
        self.assertEqual(status, 2)

    def test_release_risk_tier_requires_release_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "run.json"
            args = runner_args(out)
            args.risk_tier = "release"
            status = run_project_runner(
                args,
                clock_func=lambda: "2026-07-11T12:00:00Z",
            )
        self.assertEqual(status, 2)

    def test_partial_generation_never_publishes_completion_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "run.json"
            args = runner_args(out)
            replacement_count = 0

            def fail_second_replace(source: Path, destination: Path) -> None:
                nonlocal replacement_count
                replacement_count += 1
                if replacement_count == 2:
                    raise OSError("injected generation publication failure")
                source.replace(destination)

            status = run_project_runner(
                args,
                clock_func=lambda: "2026-07-11T12:00:00Z",
                replace_func=fail_second_replace,
            )
            completion = out.with_name("run.complete.json")
            self.assertEqual(status, 2)
            self.assertFalse(completion.exists())

    def test_failed_refresh_preserves_previous_complete_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "run.json"
            args = runner_args(out)
            self.assertEqual(
                run_project_runner(
                    args,
                    clock_func=lambda: "2026-07-11T12:00:00Z",
                ),
                0,
            )
            completion = root / "run.complete.json"
            prior_marker = completion.read_bytes()
            replacement_count = 0

            def fail_second_replace(source: Path, destination: Path) -> None:
                nonlocal replacement_count
                replacement_count += 1
                if replacement_count == 2:
                    raise OSError("injected refresh failure")
                source.replace(destination)

            self.assertEqual(
                run_project_runner(
                    args,
                    clock_func=lambda: "2026-07-11T12:00:01Z",
                    replace_func=fail_second_replace,
                ),
                2,
            )
            self.assertEqual(completion.read_bytes(), prior_marker)
            self.assertEqual(
                run_project_runner_inspect(
                    argparse.Namespace(
                        completion=str(completion),
                        out=str(root / "projection-after-failure.json"),
                    )
                ),
                0,
            )

    def test_owner_artifact_hash_drift_is_rejected_independently_of_binding_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            shutil.copytree(FIXTURE_ROOT / "owner-receipts", root / "owner-receipts")
            binding_source = FIXTURE_ROOT / "topology-receipt.json"
            binding_path = root / binding_source.name
            shutil.copyfile(binding_source, binding_path)
            owner = root / "owner-receipts/topology-authorization.json"
            owner.write_text(owner.read_text(encoding="utf-8") + " ", encoding="utf-8")
            out = root / "run.json"
            args = runner_args(out)
            args.topology_receipt = str(binding_path)
            args.topology_receipt_sha256 = sha256(binding_path)
            status = run_project_runner(
                args,
                clock_func=lambda: "2026-07-11T12:00:00Z",
            )
        self.assertEqual(status, 2)
        self.assertFalse(out.exists())

    def test_receipt_binding_cannot_claim_a_foreign_owner_schema(self) -> None:
        status, output_exists = run_with_mutated_input(
            "topology-receipt",
            lambda document: document.update(
                {"$schema": "rusty.manifold.peer.topology_authorization.v1"}
            ),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_canonical_owner_receipt_rejects_hostess_extension_fields(self) -> None:
        status, output_exists = run_with_mutated_owner_receipt(
            "media",
            lambda document: document.update({"profile_id": "media.receiver-first.video"}),
        )
        self.assertEqual(status, 2)
        self.assertFalse(output_exists)

    def test_inspect_projects_only_a_complete_hash_valid_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "run.json"
            status = run_project_runner(
                runner_args(out),
                clock_func=lambda: "2026-07-11T12:00:00Z",
            )
            projection_out = root / "projection.json"
            inspect_status = run_project_runner_inspect(
                argparse.Namespace(
                    completion=str(root / "run.complete.json"),
                    out=str(projection_out),
                )
            )
            projection = read_json(projection_out)
        self.assertEqual(status, 0)
        self.assertEqual(inspect_status, 0)
        self.assertEqual(projection["$schema"], PROJECT_RUNNER_PROJECTION_SCHEMA)
        self.assertEqual(projection["status"], "complete")
        self.assertGreaterEqual(len(projection["rows"]), 8)

    def test_inspect_rejects_tampered_plan_from_complete_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out = root / "run.json"
            self.assertEqual(
                run_project_runner(
                    runner_args(out),
                    clock_func=lambda: "2026-07-11T12:00:00Z",
                ),
                0,
            )
            completion = read_json(root / "run.complete.json")
            plan = Path(
                next(
                    row["path"]
                    for row in completion["artifacts"]
                    if row["role"] == "hostess.plan"
                )
            )
            plan.write_text(plan.read_text(encoding="utf-8") + " ", encoding="utf-8")
            projection_out = root / "projection.json"
            status = run_project_runner_inspect(
                argparse.Namespace(
                    completion=str(root / "run.complete.json"),
                    out=str(projection_out),
                )
            )
        self.assertEqual(status, 2)
        self.assertFalse(projection_out.exists())

    def test_parser_exposes_cli_equivalent_project_runner_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "run.json"
            expected = runner_args(out)
            parsed = build_parser().parse_args(cli_args(expected))

        self.assertEqual(parsed.command, "project-runner")
        self.assertEqual(parsed.project_runner_command, "run")
        self.assertEqual(parsed.project_spec, expected.project_spec)
        self.assertEqual(parsed.product_lock_sha256, expected.product_lock_sha256)
        self.assertEqual(parsed.capability_id, expected.capability_id)
        self.assertEqual(parsed.risk_tier, "standard")
        self.assertFalse(parsed.execute)

    def test_parser_exposes_cli_equivalent_ownership_audit(self) -> None:
        parsed = build_parser().parse_args(
            [
                "project-runner",
                "ownership-audit",
                "--repo-root",
                ".",
                "--inventory",
                str(OWNERSHIP_INVENTORY),
                "--out",
                "target/schema-ownership/audit.json",
                "--fail-on-error",
            ]
        )

        self.assertEqual(parsed.command, "project-runner")
        self.assertEqual(parsed.project_runner_command, "ownership-audit")
        self.assertTrue(parsed.fail_on_error)

    def test_parser_exposes_read_only_project_runner_inspect(self) -> None:
        parsed = build_parser().parse_args(
            [
                "project-runner",
                "inspect",
                "--completion",
                "target/project-runner/run.complete.json",
                "--out",
                "target/project-runner/projection.json",
            ]
        )
        self.assertEqual(parsed.project_runner_command, "inspect")
        self.assertEqual(parsed.completion, "target/project-runner/run.complete.json")

    def test_current_schema_ownership_inventory_passes(self) -> None:
        report = build_schema_ownership_audit(REPO_ROOT, OWNERSHIP_INVENTORY)

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["unknown_foreign_schema_ids"], [])
        self.assertEqual(report["unapproved_foreign_reference_paths"], [])
        self.assertEqual(report["unknown_foreign_references"], [])
        self.assertEqual(report["stale_inventory_references"], [])
        self.assertIn(
            "rusty.quest.device_link.install_environment_suite_run.v1",
            {row["schema_id"] for row in report["foreign_schema_references"]},
        )
        self.assertEqual(report["policy"]["new_output_prefix"], "rusty.hostess.")

    def test_schema_ownership_audit_rejects_unregistered_foreign_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "tools/hostessctl"
            source_root.mkdir(parents=True)
            (source_root / "accidental.py").write_text(
                'OUTPUT_SCHEMA = "rusty.quest.unregistered_output.v1"\n',
                encoding="utf-8",
            )
            report = build_schema_ownership_audit(root, OWNERSHIP_INVENTORY)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            report["unknown_foreign_schema_ids"],
            ["rusty.quest.unregistered_output.v1"],
        )

    def test_schema_ownership_audit_rejects_known_foreign_schema_in_new_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "tools/hostessctl"
            source_root.mkdir(parents=True)
            (source_root / "new_output.py").write_text(
                'OUTPUT_SCHEMA = "rusty.quest.device_link.v1"\n',
                encoding="utf-8",
            )
            report = build_schema_ownership_audit(root, OWNERSHIP_INVENTORY)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["unknown_foreign_schema_ids"], ["rusty.quest.device_link.v1"])
        self.assertEqual(
            report["unapproved_foreign_reference_paths"],
            ["tools/hostessctl/new_output.py"],
        )
        self.assertEqual(
            report["unknown_foreign_references"],
            [
                {
                    "schema_id": "rusty.quest.device_link.v1",
                    "path": "tools/hostessctl/new_output.py",
                }
            ],
        )

    def test_schema_ownership_audit_scans_new_schema_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            schema_root = root / "schemas"
            schema_root.mkdir(parents=True)
            write_json(
                schema_root / "accidental-owner.schema.json",
                {"owner_schema": "rusty.quest.device_link.v1"},
            )
            report = build_schema_ownership_audit(root, OWNERSHIP_INVENTORY)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            report["unapproved_foreign_reference_paths"],
            ["schemas/accidental-owner.schema.json"],
        )

    def test_schema_ownership_audit_scans_all_production_languages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "apps/runtime"
            source_root.mkdir(parents=True)
            for name in (
                "surface.py",
                "Surface.cs",
                "surface.rs",
                "Surface.java",
                "Surface.kt",
                "surface.json",
            ):
                (source_root / name).write_text(
                    'SCHEMA = "rusty.manifold.command.envelope.v1"\n',
                    encoding="utf-8",
                )
            report = build_schema_ownership_audit(root, OWNERSHIP_INVENTORY)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["scanned_file_count"], 6)
        self.assertEqual(len(report["unknown_foreign_references"]), 6)


def runner_args(out: Path) -> argparse.Namespace:
    paths: dict[str, Path] = {
        name.replace("-", "_"): FIXTURE_ROOT / f"{name}.json"
        for name in (
            "project-spec",
            "product-lock",
            "topology-profile",
            "topology-receipt",
            "media-profile",
            "media-receipt",
            "evidence-profile",
            "evidence-receipt",
            "cleanup-contract",
        )
    }
    values: dict[str, object] = {
        key: str(path) for key, path in paths.items()
    }
    values.update({f"{key}_sha256": sha256(path) for key, path in paths.items()})
    values.update(
        {
            "capability_id": ["media_session", "command.media.session.start"],
            "risk_tier": "standard",
            "run_id": "hostess-network-workflow-fixture",
            "out": str(out),
            "envelope_out": None,
            "plan_out": None,
            "completion_out": None,
            "execute": False,
        }
    )
    return argparse.Namespace(**values)


def cli_args(args: argparse.Namespace) -> list[str]:
    result = ["project-runner", "run"]
    for name in (
        "project_spec",
        "project_spec_sha256",
        "product_lock",
        "product_lock_sha256",
        "topology_profile",
        "topology_profile_sha256",
        "topology_receipt",
        "topology_receipt_sha256",
        "media_profile",
        "media_profile_sha256",
        "media_receipt",
        "media_receipt_sha256",
        "evidence_profile",
        "evidence_profile_sha256",
        "evidence_receipt",
        "evidence_receipt_sha256",
        "cleanup_contract",
        "cleanup_contract_sha256",
        "risk_tier",
        "run_id",
        "out",
    ):
        result.extend([f"--{name.replace('_', '-')}", str(getattr(args, name))])
    for capability_id in args.capability_id:
        result.extend(["--capability-id", capability_id])
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_with_mutated_input(
    fixture_name: str,
    mutate: object,
) -> tuple[int, bool]:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        if fixture_name.endswith("-receipt"):
            shutil.copytree(FIXTURE_ROOT / "owner-receipts", root / "owner-receipts")
        source = FIXTURE_ROOT / f"{fixture_name}.json"
        damaged = root / source.name
        document = read_json(source)
        mutate(document)
        write_json(damaged, document)
        out = root / "run.json"
        args = runner_args(out)
        attr = fixture_name.replace("-", "_")
        setattr(args, attr, str(damaged))
        setattr(args, f"{attr}_sha256", sha256(damaged))
        status = run_project_runner(
            args,
            clock_func=lambda: "2026-07-11T12:00:00Z",
        )
        output_exists = out.exists()
    return status, output_exists


def run_with_mutated_owner_receipt(
    role: str,
    mutate: object,
) -> tuple[int, bool]:
    names = {
        "topology": "topology-authorization.json",
        "media": "media-adapter-receipt.json",
        "evidence": "quest-generic-media-evidence.json",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        owner_dir = root / "owner-receipts"
        shutil.copytree(FIXTURE_ROOT / "owner-receipts", owner_dir)
        owner_path = owner_dir / names[role]
        owner_document = read_json(owner_path)
        mutate(owner_document)
        write_json(owner_path, owner_document)

        binding_source = FIXTURE_ROOT / f"{role}-receipt.json"
        binding_path = root / binding_source.name
        binding = read_json(binding_source)
        binding["owner_receipt_ref"]["sha256"] = sha256(owner_path)
        write_json(binding_path, binding)

        out = root / "run.json"
        args = runner_args(out)
        setattr(args, f"{role}_receipt", str(binding_path))
        setattr(args, f"{role}_receipt_sha256", sha256(binding_path))
        status = run_project_runner(
            args,
            clock_func=lambda: "2026-07-11T12:00:00Z",
        )
        output_exists = out.exists()
    return status, output_exists


def build_parser() -> argparse.ArgumentParser:
    return build_hostessctl_parser(
        broker_package="broker",
        broker_port=8765,
        broker_local_forward_port=18765,
        makepad_android_package="makepad",
        makepad_android_xr_activity="makepad/.Xr",
        makepad_provider_package="makepad",
        makepad_provider_activity="makepad/.Xr",
    )


if __name__ == "__main__":
    unittest.main()
