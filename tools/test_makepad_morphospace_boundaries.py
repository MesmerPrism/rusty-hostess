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


if __name__ == "__main__":
    unittest.main()
