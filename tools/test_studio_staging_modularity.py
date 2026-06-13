from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
STAGING_ROOT = REPO_ROOT / "tools" / "studio_staging"


class StudioStagingModularityTests(unittest.TestCase):
    def test_platform_smoke_facade_stays_split_by_phase(self) -> None:
        facade_path = STAGING_ROOT / "platform_smoke.py"
        facade = facade_path.read_text(encoding="utf-8")
        modules = {
            "platform_smoke_plan.py": "def build_platform_smoke_plan",
            "platform_smoke_execution.py": "def build_platform_smoke_execution_request",
            "platform_smoke_operator_start.py": "def build_platform_smoke_operator_start_gate",
            "platform_smoke_execution_report.py": "def build_platform_smoke_execution_report",
            "platform_smoke_evidence.py": "def build_platform_smoke_evidence_review",
        }

        self.assertLessEqual(len(facade.splitlines()), 40)
        self.assertNotIn("def build_platform_smoke_plan", facade)
        self.assertNotIn("def build_platform_smoke_evidence_review", facade)

        for filename, required_symbol in modules.items():
            module_path = STAGING_ROOT / filename
            self.assertTrue(module_path.exists(), filename)
            module = module_path.read_text(encoding="utf-8")
            self.assertIn(required_symbol, module)
            self.assertLess(
                len(module.splitlines()),
                2000,
                f"{filename} should stay reviewable as a phase module",
            )
            self.assertIn(
                f"from tools.studio_staging.{module_path.stem} import *",
                facade,
            )

    def test_staging_handoff_facade_stays_split_by_phase(self) -> None:
        facade_path = STAGING_ROOT / "staging_handoff.py"
        facade = facade_path.read_text(encoding="utf-8")
        modules = {
            "staging_handoff_acceptance.py": (
                "def build_hostess_staging_handoff_acceptance_receipt"
            ),
            "staging_handoff_file_plan.py": (
                "def build_hostess_staging_file_plan_receipt"
            ),
            "staging_handoff_file_copy.py": (
                "def build_hostess_staging_file_copy_receipt"
            ),
            "staging_handoff_payload_manifest.py": (
                "def build_hostess_staged_payload_manifest_receipt"
            ),
            "staging_handoff_downstream_shell.py": (
                "def build_hostess_downstream_shell_selection_receipt"
            ),
        }

        self.assertLessEqual(len(facade.splitlines()), 40)
        self.assertNotIn(
            "def build_hostess_staging_handoff_acceptance_receipt",
            facade,
        )
        self.assertNotIn(
            "def build_hostess_downstream_shell_selection_receipt",
            facade,
        )

        for filename, required_symbol in modules.items():
            module_path = STAGING_ROOT / filename
            self.assertTrue(module_path.exists(), filename)
            module = module_path.read_text(encoding="utf-8")
            self.assertIn(required_symbol, module)
            self.assertLess(
                len(module.splitlines()),
                2000,
                f"{filename} should stay reviewable as a phase module",
            )
            self.assertIn(
                f"from tools.studio_staging.{module_path.stem} import *",
                facade,
            )


if __name__ == "__main__":
    unittest.main()
