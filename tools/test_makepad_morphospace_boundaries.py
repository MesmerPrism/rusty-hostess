import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOSTESS_MAKEPAD_SRC = REPO_ROOT / "apps" / "hostess-t-makepad" / "src"


def rust_sources():
    return sorted(HOSTESS_MAKEPAD_SRC.rglob("*.rs"))


class MakepadMorphospaceBoundaryTests(unittest.TestCase):
    def test_legacy_rusty_xr_schema_constants_are_explicitly_quarantined(self):
        const_pattern = re.compile(
            r"pub\s+const\s+([A-Z0-9_]+)\s*:\s*&str\s*=\s*(?:\r?\n\s*)?\"([^\"]+)\"\s*;",
            re.MULTILINE,
        )
        violations = []

        for source in rust_sources():
            text = source.read_text(encoding="utf-8")
            for match in const_pattern.finditer(text):
                name, value = match.groups()
                if value.startswith("rusty.xr") and not name.startswith("LEGACY_RUSTY_XR_"):
                    rel = source.relative_to(REPO_ROOT)
                    violations.append(f"{rel}:{name}={value}")

        self.assertEqual([], violations)

    def test_active_markers_do_not_emit_rusty_xr_schema_lane(self):
        violations = []

        for source in rust_sources():
            for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
                if "schema=rusty.xr" in line:
                    rel = source.relative_to(REPO_ROOT)
                    violations.append(f"{rel}:{line_number}:{line.strip()}")

        self.assertEqual([], violations)

    def test_hostess_uses_quest_makepad_billboard_renderer_boundary(self):
        main = (HOSTESS_MAKEPAD_SRC / "main.rs").read_text(encoding="utf-8")
        runtime = (HOSTESS_MAKEPAD_SRC / "matter_surface_runtime.rs").read_text(
            encoding="utf-8"
        )
        widget = (HOSTESS_MAKEPAD_SRC / "matter_world_particle_billboard.rs").read_text(
            encoding="utf-8"
        )

        self.assertIn("mod matter_world_particle_billboard;", main)
        self.assertIn("mod matter_surface_runtime;", main)
        self.assertIn("matter_world_particle_billboard::script_mod(vm)", main)
        self.assertIn("MatterWorldParticleBillboardCloud", widget)
        self.assertIn("QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_RENDERER_ID", runtime)
        self.assertIn("QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_ANIMATION_SOURCE", runtime)
        self.assertIn("QUEST_MAKEPAD_WORLD_PARTICLE_BILLBOARD_REFERENCE", runtime)
        self.assertIn("DEFAULT_PARTICLE_RENDER_ANIMATION_MODE", main)
        self.assertNotIn('"makepad-xr-procedural-ring-billboard"', main)
        self.assertNotIn('"procedural-morph-ring"', main)
        self.assertNotIn('"rusty-viscereality-billboard-ring"', main)
        self.assertNotIn('"makepad-xr-procedural-ring-billboard"', runtime)
        self.assertNotIn('"procedural-morph-ring"', runtime)
        self.assertNotIn('"rusty-viscereality-billboard-ring"', runtime)
        self.assertIn("Hostess-local Makepad smoke renderer", widget)
        self.assertIn("reusable renderer should move", widget)

    def test_runtime_config_manifest_formatter_stays_split_from_core_parser(self):
        root = (HOSTESS_MAKEPAD_SRC / "makepad_runtime_config.rs").read_text(
            encoding="utf-8"
        )
        manifest_path = HOSTESS_MAKEPAD_SRC / "makepad_runtime_config" / "manifest.rs"
        self.assertTrue(manifest_path.exists())
        manifest = manifest_path.read_text(encoding="utf-8")

        self.assertIn("mod manifest;", root)
        self.assertIn("pub use manifest::projection_runtime_manifest_marker_lines;", root)
        self.assertIn("pub fn projection_runtime_manifest_marker_lines", manifest)
        self.assertIn("section=aliases", manifest)
        self.assertNotIn("fn projection_runtime_alias_tokens", root)
        self.assertNotIn("fn sanitize_marker_token", root)

    def test_runtime_config_projection_registry_stays_split_from_core_parser(self):
        root = (HOSTESS_MAKEPAD_SRC / "makepad_runtime_config.rs").read_text(
            encoding="utf-8"
        )
        alias_model_path = HOSTESS_MAKEPAD_SRC / "makepad_runtime_config" / "alias_model.rs"
        registry_path = HOSTESS_MAKEPAD_SRC / "makepad_runtime_config" / "projection_keys.rs"
        tests_path = HOSTESS_MAKEPAD_SRC / "makepad_runtime_config" / "tests.rs"
        self.assertTrue(alias_model_path.exists())
        self.assertTrue(registry_path.exists())
        self.assertTrue(tests_path.exists())
        alias_model = alias_model_path.read_text(encoding="utf-8")
        registry = registry_path.read_text(encoding="utf-8")
        tests = tests_path.read_text(encoding="utf-8")

        self.assertIn("mod alias_model;", root)
        self.assertIn("mod projection_keys;", root)
        self.assertIn("RuntimeKeyAliasStatus", alias_model)
        self.assertIn("LegacyRuntimeKey", alias_model)
        self.assertIn("pub use projection_keys::*;", root)
        self.assertIn("PROJECTION_RUNTIME_KEY_DEFINITIONS", registry)
        self.assertIn("pub fn projection_runtime_key_definition", registry)
        self.assertIn("mod tests;", root)
        self.assertIn("projection_runtime_golden_matrix_is_backend_neutral", tests)
        self.assertNotIn("LegacyRuntimeKey", root)
        self.assertNotIn("Deprecated,", root)
        self.assertNotIn("pub const KEY_CAMERA_PROJECTION_MODE", root)
        self.assertNotIn("PROJECTION_RUNTIME_KEY_DEFINITIONS", root)
        self.assertNotIn("projection_runtime_golden_matrix_is_backend_neutral", root)

    def test_camera_projection_flow_stays_split_from_app_root(self):
        main = (HOSTESS_MAKEPAD_SRC / "main.rs").read_text(encoding="utf-8")
        flow_path = HOSTESS_MAKEPAD_SRC / "camera_projection_flow.rs"
        self.assertTrue(flow_path.exists())
        flow = flow_path.read_text(encoding="utf-8")

        self.assertIn("mod camera_projection_flow;", main)
        self.assertIn("pub(super) fn handle_paired_import_event", flow)
        self.assertIn("pub(super) fn bind_camera_projection_panel", flow)
        self.assertIn("pub(super) fn emit_cadence_sample", flow)
        self.assertIn("pub(super) fn try_adopt_pending_stereo_camera_frame", flow)
        self.assertIn("pub(super) fn complete_paired_import_if_ready", flow)
        self.assertNotIn("fn bind_camera_projection_panel", main)
        self.assertNotIn("fn record_pending_camera_frame", main)
        self.assertNotIn("fn emit_stereo_frame_adoption_marker", main)


if __name__ == "__main__":
    unittest.main()
