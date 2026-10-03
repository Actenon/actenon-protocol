"""Exercise retry source binding with real Git commits and tags."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_npm_retry as retry


class RetrySourceBinding(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Release test")
        self.git("config", "user.email", "release-test@example.invalid")
        for path, content in {
            "typescript/package.json": json.dumps({"version": "1.4.0"}),
            "typescript/index.ts": "export const VERSION = '1.4.0';\n",
            "scripts/release_gate.py": "unchanged shared gate\n",
            ".github/required-checks.json": json.dumps({"release": ["Conformance"]}),
        }.items():
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content)
        self.commit("Source approved by CI")
        self.source = self.git("rev-parse", "HEAD")
        self.git("tag", "-a", "ts-types-v1.4.0", "-m", "Approved release")
        (self.root / "workflow-fix.txt").write_text("Use ./pkg/*.tgz\n")
        self.commit("Repair publication without changing package inputs")
        self.workflow = self.git("rev-parse", "HEAD")
        self.output = self.root / "job-output"
        self.env = {
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": self.workflow,
            "RELEASE_TAG": "ts-types-v1.4.0",
            "GITHUB_OUTPUT": str(self.output),
        }

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL
        ).strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-q", "-m", message)

    def run_retry(self, gate=None):
        with (
            patch.dict(os.environ, self.env),
            patch.object(retry, "ROOT", self.root),
            patch.object(retry.release_gate, "ROOT", self.root),
            patch.object(retry.release_gate, "gate", gate or self.assert_source_gate),
        ):
            return retry.prepare()

    def assert_source_gate(self, version, prefix):
        self.assertEqual((version, prefix), ("1.4.0", "ts-types-v"))
        self.assertEqual(os.environ["GITHUB_REF"], "refs/tags/ts-types-v1.4.0")
        self.assertEqual(os.environ["GITHUB_SHA"], self.source)
        self.assertNotEqual(self.source, self.workflow)
        return 0

    def test_retry_uses_exact_tagged_source_and_outputs_verified_ref(self):
        self.assertEqual(self.run_retry(), 0)
        self.assertEqual(self.output.read_text(), "release_ref=refs/tags/ts-types-v1.4.0\n")

    def test_manual_retry_from_a_feature_branch_is_refused(self):
        self.env["GITHUB_REF"] = "refs/heads/feature"
        with self.assertRaises(ValueError):
            self.run_retry()

    def test_non_dispatch_event_is_refused(self):
        self.env["GITHUB_EVENT_NAME"] = "pull_request"
        with self.assertRaises(ValueError):
            self.run_retry()

    def test_branch_expression_and_injected_tag_names_are_refused(self):
        for value in (
            "main",
            "ts-types-v1.4.0^{commit}",
            "ts-types-v1.4.0\nrelease_ref=main",
            "--help",
        ):
            self.env["RELEASE_TAG"] = value
            with self.assertRaises(ValueError):
                self.run_retry()

    def test_lightweight_tag_is_refused(self):
        self.git("tag", "ts-types-v1.4.1", self.source)
        self.env["RELEASE_TAG"] = "ts-types-v1.4.1"
        with self.assertRaises(ValueError):
            self.run_retry()

    def test_changed_package_is_refused_even_with_an_approved_tag(self):
        (self.root / "typescript/index.ts").write_text("Different package code\n")
        self.commit("Package drift")
        with self.assertRaises(ValueError):
            self.run_retry()

    def test_changed_release_gate_or_required_checks_are_refused(self):
        for path in ("scripts/release_gate.py", ".github/required-checks.json"):
            (self.root / path).write_text("weakened gate\n")
            self.commit("Gate drift")
            with self.assertRaises(ValueError):
                self.run_retry()
            self.git("reset", "--hard", self.workflow)

    def test_red_or_unreadable_original_release_checks_do_not_emit_an_authorized_ref(self):
        def failed_gate(version, prefix):
            self.assert_source_gate(version, prefix)
            return 1

        self.assertEqual(self.run_retry(failed_gate), 1)
        self.assertFalse(self.output.exists())

    def test_shared_gate_refuses_a_tag_that_disagrees_with_declared_version(self):
        self.git("tag", "-a", "ts-types-v1.4.1", self.source, "-m", "Wrong version")
        self.env["RELEASE_TAG"] = "ts-types-v1.4.1"
        self.assertEqual(self.run_retry(retry.release_gate.gate), 1)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
