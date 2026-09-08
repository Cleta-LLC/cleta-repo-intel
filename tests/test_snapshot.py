from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from cleta_repo_intel.analyze import analyze_release
from cleta_repo_intel.cli import main
from cleta_repo_intel.render import render_markdown


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "demo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test User")
        (self.repo / "README.md").write_text("# demo\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "chore: initialize")
        git(self.repo, "tag", "v0.1.0")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "feat: add app")
        (self.repo / "README.md").write_text("# demo\n\nupdated\n", encoding="utf-8")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-qm", "docs: update readme")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_analyze_release(self) -> None:
        snapshot = analyze_release(self.repo, "v0.1.0", "HEAD")
        self.assertEqual(snapshot.activity.git_commits, 2)
        self.assertEqual(snapshot.activity.change_items, 2)
        self.assertEqual(snapshot.work_types["feat"], 1)
        self.assertEqual(snapshot.work_types["docs"], 1)
        self.assertTrue(snapshot.signals.tests_touched)
        self.assertTrue(snapshot.signals.docs_touched)

    def test_markdown_is_explanatory(self) -> None:
        rendered = render_markdown(analyze_release(self.repo, "v0.1.0", "HEAD"))
        self.assertIn("Engineering Footprint", rendered)
        self.assertIn("not an estimate of hours worked", rendered)

    def test_cli_writes_json_and_markdown(self) -> None:
        output = Path(self.temp.name) / "reports"
        result = main(["snapshot", str(self.repo), "--from", "v0.1.0", "--to", "HEAD", "--output", str(output)])
        self.assertEqual(result, 0)
        payload = json.loads((output / "HEAD" / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "0.1")
        self.assertEqual(payload["activity"]["git_commits"], 2)
        self.assertEqual(payload["activity"]["change_items"], 2)
        self.assertTrue((output / "HEAD" / "report.md").exists())

    def test_squash_commit_recovers_change_items(self) -> None:
        (self.repo / "src" / "more.py").write_text("x = 1\n", encoding="utf-8")
        git(self.repo, "add", ".")
        message = "feat: release wrapper\n\n* feat: add matching\n\n* fix: repair policy\n\n* test: cover migration\n\n* docs: update runbook\n\n* chore: bump version\n\n* perf: add index"
        git(self.repo, "commit", "-qm", message)
        snapshot = analyze_release(self.repo, "HEAD~1", "HEAD")
        self.assertEqual(snapshot.activity.git_commits, 1)
        self.assertEqual(snapshot.activity.change_items, 6)
        self.assertEqual(snapshot.signals.history_shape, "squash_like")
        self.assertEqual(snapshot.work_types["feat"], 1)
        self.assertEqual(snapshot.work_types["fix"], 1)
        self.assertEqual(snapshot.work_types["test"], 1)


if __name__ == "__main__":
    unittest.main()
