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
            'bevy = { version = "0.19", default-features = false, '
            'features = ["3d", "ui", "audio"] }\n'
        )
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])

    def test_api_only_profile_requires_external_renderer(self) -> None:
        result = self.audit(
            'bevy = { version = "0.19", default-features = false, '
            'features = ["default_app", "3d_api"] }\n'
        )
        self.assertTrue(
            any("external/custom renderer" in note for note in result["notes"])
        )

    def test_headless_rapier_configuration_stays_renderer_independent(self) -> None:
        result = self.audit(
            'bevy = { version = "0.19", default-features = false, '
            'features = ["default_app"] }\n'
            'bevy_rapier3d = { version = "0.36", default-features = false, '
            'features = ["dim3", "headless"] }\n'
        )
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])
        self.assertTrue(any("unused legacy marker" in note for note in result["notes"]))

    def test_rapier_037_lean_profile_needs_no_headless_feature(self) -> None:
        result = self.audit(
            'bevy = { version = "0.20", default-features = false, '
            'features = ["default_app"] }\n'
            'bevy_rapier3d = { version = "0.37", default-features = false, '
            'features = ["dim3"] }\n'
        )
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])

    def test_rapier_037_rejects_removed_headless_feature(self) -> None:
        for version in ("0.37", "0.37.0", "^0.37.0", "~0.37.0", "=0.37.0"):
            with self.subTest(version=version):
                result = self.audit(
                    'bevy = "0.20"\n'
                    f'bevy_rapier3d = {{ version = "{version}", default-features = false, '
                    'features = ["dim3", "headless"] }\n'
                )
                self.assertTrue(
                    any("removed the `headless` feature" in error for error in result["errors"])
                )

    def test_known_bevy_rapier_minor_mismatches_are_errors(self) -> None:
        for bevy, rapier in (("0.19", "0.37"), ("0.20", "0.36")):
            with self.subTest(bevy=bevy, rapier=rapier):
                result = self.audit(
                    f'bevy = "{bevy}"\nbevy_rapier3d = "{rapier}"\n'
                )
                self.assertTrue(any("requires Bevy" in error for error in result["errors"]))

    def test_build_dependency_does_not_replace_runtime_bevy_for_version_pairing(self) -> None:
        result = self.audit(
            'bevy = "0.20"\nbevy_rapier3d = "0.37"\n'
            '[build-dependencies]\nbevy = "0.19"\n'
        )
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("ambiguous across dependency scopes" in warning for warning in result["warnings"]))

    def test_bevy_and_rapier_in_separate_dependency_kinds_are_not_paired(self) -> None:
        result = self.audit(
            'bevy = "0.19"\n'
            '[build-dependencies]\nbevy_rapier3d = "0.37"\n'
        )
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("compatibility was not checked" in warning for warning in result["warnings"]))

    def test_separate_target_scopes_are_not_paired(self) -> None:
        result = self.audit(
            "[target.'cfg(windows)'.dependencies]\nbevy = \"0.19\"\n"
            "[target.'cfg(unix)'.dependencies]\nbevy_rapier3d = \"0.37\"\n"
        )
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("compatibility was not checked" in warning for warning in result["warnings"]))

    def test_single_same_target_scope_can_report_a_version_mismatch(self) -> None:
        result = self.audit(
            "[target.'cfg(unix)'.dependencies]\n"
            'bevy = "0.19"\nbevy_rapier3d = "0.37"\n'
        )
        self.assertTrue(any("requires Bevy" in error for error in result["errors"]))
        self.assertFalse(any("ambiguous" in warning for warning in result["warnings"]))

    def test_unresolved_rapier_requirements_do_not_claim_headless_is_valid(self) -> None:
        requirements = (
            'version = ">=0.36, <0.38"',
            'version = "0.37.0-rc.1"',
            'workspace = true',
            'version = "0.37", git = "https://example.com/rapier.git"',
            'version = "0.37", path = "../rapier"',
        )
        for requirement in requirements:
            with self.subTest(requirement=requirement):
                result = self.audit(
                    'bevy = "0.20"\n'
                    f'bevy_rapier3d = {{ {requirement}, default-features = false, '
                    'features = ["dim3", "headless"] }\n'
                )
                self.assertEqual(result["errors"], [])
                self.assertTrue(
                    any("Cannot validate `headless`" in warning for warning in result["warnings"])
                )
                self.assertFalse(any("legacy marker" in note for note in result["notes"]))

    def test_unknown_rapier_line_warns_instead_of_asserting_compatibility(self) -> None:
        result = self.audit('bevy = "0.20"\nbevy_rapier3d = "0.38"\n')
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("version-specific checks" in warning for warning in result["warnings"]))

    def test_simple_registry_minor_recognition_is_conservative(self) -> None:
        for requirement in ("0.37", "^0.37.0", "~0.37", "=0.37.0", " 0.37.0 "):
            with self.subTest(requirement=requirement):
                self.assertEqual(MODULE.declared_minor(requirement), (0, 37))
        for requirement in ("0", "0.*", "0.37.*", ">=0.37", "0.37.0+build", "1.0", None):
            with self.subTest(requirement=requirement):
                self.assertIsNone(MODULE.declared_minor(requirement))

    def test_rapier_defaults_warn_for_trimmed_bevy(self) -> None:
        result = self.audit(
            'bevy = { version = "0.19", default-features = false, '
            'features = ["default_app"] }\n'
            'bevy_rapier3d = "0.36"\n'
        )
        self.assertTrue(
            any("Rapier defaults" in warning for warning in result["warnings"])
        )

    def test_rapier_without_dimension_is_an_error(self) -> None:
        result = self.audit(
            'bevy = { version = "0.19", default-features = false, '
            'features = ["default_app"] }\n'
            'bevy_rapier3d = { version = "0.36", default-features = false, '
            'features = ["headless"] }\n'
        )
        self.assertTrue(any("dim3" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
