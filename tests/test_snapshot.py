from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from cleta_repo_intel.analyze import analyze_release
from cleta_repo_intel.cli import main
from cleta_repo_intel.html import render_html
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
        self.assertEqual(snapshot.signals.delivery_complexity, "low")
        self.assertEqual(snapshot.signals.surfaces_touched, 3)
        self.assertEqual(snapshot.schema_version, "0.2")
        self.assertGreater(len(snapshot.intelligence.evidence), 0)

    def test_markdown_is_explanatory(self) -> None:
        rendered = render_markdown(analyze_release(self.repo, "v0.1.0", "HEAD"))
        self.assertIn("Engineering Footprint", rendered)
        self.assertIn("Release Intelligence", rendered)
        self.assertIn("Primary Themes", rendered)
        self.assertIn("not an estimate of hours worked", rendered)

    def test_cli_writes_json_markdown_and_html(self) -> None:
        output = Path(self.temp.name) / "reports"
        result = main(["snapshot", str(self.repo), "--from", "v0.1.0", "--to", "HEAD", "--output", str(output)])
        self.assertEqual(result, 0)
        payload = json.loads((output / "HEAD" / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "0.2")
        self.assertEqual(payload["activity"]["git_commits"], 2)
        self.assertIn("intelligence", payload)
        self.assertTrue((output / "HEAD" / "report.md").exists())
        self.assertTrue((output / "HEAD" / "report.html").exists())

    def test_html_is_self_contained(self) -> None:
        rendered = render_html(analyze_release(self.repo, "v0.1.0", "HEAD"))
        self.assertIn("<!doctype html>", rendered.lower())
        self.assertIn("Cleta Release Intelligence", rendered)
        self.assertNotIn("<script src=", rendered)
        self.assertNotIn("<link rel=", rendered)

    def test_squash_commit_recovers_change_items_and_complexity(self) -> None:
        (self.repo / "src" / "more.py").write_text("x = 1\n", encoding="utf-8")
        migrations = self.repo / "supabase" / "migrations"
        migrations.mkdir(parents=True)
        (migrations / "001.sql").write_text("create table demo(id int);\n", encoding="utf-8")
        (self.repo / "package.json").write_text('{"name":"demo"}\n', encoding="utf-8")
        (self.repo / "README.md").write_text("# demo\n\nupdated again\n", encoding="utf-8")
        (self.repo / "tests" / "test_more.py").write_text("def test_more():\n    assert True\n", encoding="utf-8")
        message = "feat: release wrapper\n\n* feat: add matching workflow\n\n* fix: repair RLS policy\n\n* test: cover migration\n\n* docs: update runbook\n\n* chore: bump version\n\n* perf: add index"
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", message)
        snapshot = analyze_release(self.repo, "HEAD~1", "HEAD")
        self.assertEqual(snapshot.activity.git_commits, 1)
        self.assertEqual(snapshot.activity.change_items, 6)
        self.assertEqual(snapshot.signals.history_shape, "squash_like")
        self.assertEqual(snapshot.signals.delivery_complexity, "high")
        self.assertGreaterEqual(snapshot.signals.surfaces_touched, 4)
        self.assertIn("Security & access control", [theme.name for theme in snapshot.intelligence.themes])
        self.assertIn("security-data-boundary", [finding.id for finding in snapshot.intelligence.findings])

    def test_rework_signal_detects_repeated_change_items(self) -> None:
        (self.repo / "src" / "version.py").write_text("VERSION = '0.2'\n", encoding="utf-8")
        message = "fix: wrapper\n\n* fix: use valid release version\n\n* fix: use valid release version\n\n* test: verify version"
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", message)
        snapshot = analyze_release(self.repo, "HEAD~1", "HEAD")
        self.assertEqual(snapshot.intelligence.rework_signals[0].count, 2)
        self.assertEqual(snapshot.intelligence.rework_signals[0].kind, "repeated_change_item")
        self.assertIn("repeated-correction", [finding.id for finding in snapshot.intelligence.findings])


if __name__ == "__main__":
    unittest.main()
