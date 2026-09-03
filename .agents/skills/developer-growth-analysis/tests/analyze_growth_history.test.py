import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analyze_growth_history.py"


def millis(timestamp):
    return int(timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000)


class AnalyzeGrowthHistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.history = Path(self.tmp.name) / "history.jsonl"
        entries = [
            {
                "timestamp": millis(datetime(2026, 7, 1, 10, 0, 0)),
                "project": "frontend-app",
                "display": "Fix failing Playwright test around responsive layout overflow in React UI",
            },
            {
                "timestamp": millis(datetime(2026, 7, 1, 11, 0, 0)),
                "project": "frontend-app",
                "display": "Debug TypeScript type error for optional auth token and sanitize secret before logging",
            },
            {
                "ts": millis(datetime(2026, 7, 1, 12, 0, 0)),
                "project": "infra",
                "display": "Create automation script for release workflow and validate CI build",
            },
        ]
        self.history.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args):
        return subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--history",
                str(self.history),
                "--since",
                "2026-07-01T00:00:00Z",
                "--until",
                "2026-07-02T00:00:00Z",
                *args,
            ],
            text=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_markdown_report_contains_growth_areas(self):
        result = self.run_script()
        self.assertIn("# Developer Growth Report", result.stdout)
        self.assertIn("Frontend layout robustness", result.stdout)
        self.assertIn("Security and sensitive data handling", result.stdout)
        self.assertIn("Entries Analyzed**: 3", result.stdout)

    def test_chinese_markdown_report_contains_growth_areas(self):
        result = self.run_script("--language", "zh")
        self.assertIn("# 开发者成长报告", result.stdout)
        self.assertIn("前端布局韧性", result.stdout)
        self.assertIn("安全与敏感数据处理", result.stdout)
        self.assertIn("**分析条目数**: 3", result.stdout)

    def test_json_report_filters_project(self):
        result = self.run_script("--project", "infra", "--format", "json")
        data = json.loads(result.stdout)
        self.assertEqual(data["summary"]["entry_count"], 1)
        self.assertEqual(data["summary"]["projects"], [["infra", 1]])
        self.assertIn("Release and automation hygiene", [item["area"] for item in data["summary"]["growth_areas"]])


if __name__ == "__main__":
    unittest.main()
