import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_changelog_context.py"


def run(cmd, cwd, **kwargs):
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "author@example.com",
            "GIT_COMMITTER_NAME": "Test Committer",
            "GIT_COMMITTER_EMAIL": "committer@example.com",
        }
    )
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


@unittest.skipIf(shutil.which("git") is None, "git is required")
class CollectChangelogContextTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        run(["git", "init"], self.repo)
        run(["git", "config", "commit.gpgsign", "false"], self.repo)
        (self.repo / "README.md").write_text("# Demo\n", encoding="utf-8")
        run(["git", "add", "README.md"], self.repo)
        run(["git", "commit", "-m", "docs: initial readme"], self.repo)
        run(["git", "tag", "v1.0.0"], self.repo)
        (self.repo / "feature.txt").write_text("feature\n", encoding="utf-8")
        run(["git", "add", "feature.txt"], self.repo)
        run(["git", "commit", "-m", "feat: add export workflow"], self.repo)
        (self.repo / "feature.txt").write_text("feature\nfix\n", encoding="utf-8")
        run(["git", "add", "feature.txt"], self.repo)
        run(["git", "commit", "-m", "fix: handle empty export names"], self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def test_json_range_from_tag(self):
        result = run(["python3", str(SCRIPT), "--repo", str(self.repo), "--from", "v1.0.0", "--format", "json"], self.repo)
        data = json.loads(result.stdout)
        self.assertEqual(data["range"]["from"], "v1.0.0")
        self.assertEqual(data["commit_count"], 2)
        self.assertEqual(data["commits"][0]["subject"], "fix: handle empty export names")
        self.assertIn("feature.txt", data["diffstat"])

    def test_markdown_last_tag(self):
        result = run(["python3", str(SCRIPT), "--repo", str(self.repo), "--last-tag"], self.repo)
        self.assertIn("Range: `v1.0.0..HEAD`", result.stdout)
        self.assertIn("feat: add export workflow", result.stdout)
        self.assertIn("fix: handle empty export names", result.stdout)


if __name__ == "__main__":
    unittest.main()
