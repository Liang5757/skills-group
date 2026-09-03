import unittest
import hashlib
import tempfile
from datetime import date
from pathlib import Path

from huijin_tracker.collectors.huijin import parse_information_center
from huijin_tracker.db import TrackerDatabase
from huijin_tracker.http import HttpResponse
from huijin_tracker.service import TrackerService, reporting_window_closed


FIXTURE = Path(__file__).parent / "fixtures" / "huijin_information_center.html"


class FakeHttp:
    def get(self, url, *, params=None):
        return HttpResponse(url, 200, FIXTURE.read_bytes(), {"Content-Type": "text/html; charset=utf-8"})


class ServiceTests(unittest.TestCase):
    def test_reporting_window_must_pass_before_absence_is_trusted(self):
        self.assertFalse(reporting_window_closed("2026-03-31", as_of=date(2026, 4, 30)))
        self.assertTrue(reporting_window_closed("2026-03-31", as_of=date(2026, 5, 1)))
        self.assertFalse(reporting_window_closed("2025-12-31", as_of=date(2026, 4, 30)))
        self.assertTrue(reporting_window_closed("2025-12-31", as_of=date(2026, 5, 1)))

    def test_non_quarter_end_is_rejected(self):
        with self.assertRaises(ValueError):
            reporting_window_closed("2026-03-30", as_of=date(2026, 5, 1))

    def test_existing_document_does_not_hide_missing_event_after_crash(self):
        with tempfile.TemporaryDirectory() as temp:
            db = TrackerDatabase(Path(temp) / "tracker.db")
            db.initialize()
            post = parse_information_center(FIXTURE.read_text(encoding="utf-8"))[1]
            digest = hashlib.sha256(
                f"{post.title}\n{post.body}\n{post.url}".encode("utf-8")
            ).hexdigest()
            db.upsert_document(
                source="huijin_official",
                external_id=post.external_id,
                title=post.title,
                published_at=post.published_at,
                observed_at="2026-09-02T00:00:00+00:00",
                url=post.url,
                source_tier="official",
                sha256=digest,
                raw_path=None,
                metadata={"body": post.body},
            )
            service = TrackerService(
                db,
                archive_dir=Path(temp) / "archive",
                http_client=FakeHttp(),
            )
            self.assertEqual(len(service.collect_huijin([2025])), 1)
            self.assertEqual(db.count("events"), 1)
            db.close()


if __name__ == "__main__":
    unittest.main()
