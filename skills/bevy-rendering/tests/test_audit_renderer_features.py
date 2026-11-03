from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_renderer_features.py"
SPEC = importlib.util.spec_from_file_location("audit_renderer_features", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RendererFeatureAuditTests(unittest.TestCase):
    def audit(self, dependency_text: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "Cargo.toml"
            manifest.write_text(
                "[package]\nname = \"fixture\"\nversion = \"0.1.0\"\n"
                "edition = \"2024\"\n\n[dependencies]\n"
                + dependency_text,
                encoding="utf-8",
            )
            return MODULE.audit(manifest)

    def test_builtin_profile_does_not_report_renderer_mismatch(self) -> None:
        result = self.audit(
            'bevy = { version = "0.20", default-features = false, '
            'features = ["3d", "ui", "audio"] }\n'
        )
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])

    def test_api_only_profile_requires_external_renderer(self) -> None:
        result = self.audit(
            'bevy = { version = "0.20", default-features = false, '
            'features = ["default_app", "3d_api"] }\n'
        )
        self.assertTrue(
            any("external/custom renderer" in note for note in result["notes"])
        )

    def test_headless_rapier_configuration_stays_renderer_independent(self) -> None:
        result = self.audit(
            'bevy = { version = "0.20", default-features = false, '
            'features = ["default_app"] }\n'
            'bevy_rapier3d = { version = "0.37", default-features = false, '
            'features = ["dim3"] }\n'
        )
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])
        self.assertTrue(any("headless profile" in note for note in result["notes"]))

    def test_removed_headless_feature_is_an_error(self) -> None:
        result = self.audit(
            'bevy = { version = "0.20", default-features = false, '
            'features = ["default_app"] }\n'
            'bevy_rapier3d = { version = "0.37", default-features = false, '
            'features = ["dim3", "headless"] }\n'
        )
        self.assertTrue(any("removed the `headless`" in error for error in result["errors"]))

    def test_rapier_defaults_warn_for_trimmed_bevy(self) -> None:
        result = self.audit(
            'bevy = { version = "0.20", default-features = false, '
            'features = ["default_app"] }\n'
            'bevy_rapier3d = "0.37"\n'
        )
        self.assertTrue(
            any("Rapier defaults" in warning for warning in result["warnings"])
        )

    def test_rapier_without_dimension_is_an_error(self) -> None:
        result = self.audit(
            'bevy = { version = "0.20", default-features = false, '
            'features = ["default_app"] }\n'
            'bevy_rapier3d = { version = "0.37", default-features = false, '
            'features = ["headless"] }\n'
        )
        self.assertTrue(any("dim3" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
