#!/usr/bin/env python3
"""Smoke tests for the bundled accessibility audit scripts."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


class AccessibilityScriptTests(unittest.TestCase):
    def run_script(self, name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_input_manifest_passes(self) -> None:
        result = self.run_script("audit_input_map.py", str(FIXTURES / "input-map.json"), "--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_input_manifest_rejects_missing_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input-map.json"
            path.write_text('{"version": 1, "settings": {}, "actions": []}', encoding="utf-8")
            result = self.run_script("audit_input_map.py", str(path), "--strict")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("actions", result.stdout)

    def test_contrast_manifest_passes(self) -> None:
        result = self.run_script("check_contrast.py", str(FIXTURES / "contrast.json"), "--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_contrast_manifest_rejects_low_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contrast.json"
            path.write_text(
                '{"pairs":[{"id":"bad","foreground":"#777777",'
                '"background":"#888888","kind":"text","target":"AAA"}]}',
                encoding="utf-8",
            )
            result = self.run_script("check_contrast.py", str(path), "--strict")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL bad", result.stdout)

    def test_caption_locales_pass(self) -> None:
        result = self.run_script(
            "validate_captions.py",
            str(FIXTURES / "en-US.vtt"),
            str(FIXTURES / "fr-FR.vtt"),
            "--strict",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_caption_validator_rejects_bad_timing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.vtt"
            path.write_text(
                "WEBVTT\n\n00:00:02.000 --> 00:00:01.000\nToo late\n",
                encoding="utf-8",
            )
            result = self.run_script("validate_captions.py", str(path), "--strict")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ERROR duration", result.stdout)


if __name__ == "__main__":
    unittest.main()
