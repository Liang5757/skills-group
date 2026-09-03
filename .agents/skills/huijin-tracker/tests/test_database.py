import tempfile
import unittest
from pathlib import Path

from huijin_tracker.db import TrackerDatabase
from huijin_tracker.models import Attribution, Confidence, EventType, OperationEvent


def sample_event() -> OperationEvent:
    return OperationEvent(
        event_key="event-1",
        event_type=EventType.CONFIRMED_BUY,
        entity_key="central_huijin_investment",
        holder_name="中央汇金投资有限责任公司",
        attribution=Attribution.DIRECT,
        instrument_code="",
        instrument_name="ETF",
        market="CN",
        scope="official_statement",
        event_date="2026-09-02",
        published_at="2026-09-02",
        previous_shares=None,
        current_shares=None,
        previous_ratio=None,
        current_ratio=None,
        reason="官方确认",
        confidence=Confidence.CONFIRMED_OFFICIAL,
        source="fixture",
        evidence_url="https://example.test/evidence",
        created_at="2026-09-02T00:00:00+00:00",
    )


class DatabaseTests(unittest.TestCase):
    def test_source_failure_counter_resets_after_success(self):
        with tempfile.TemporaryDirectory() as temp:
            db = TrackerDatabase(Path(temp) / "test.db")
            db.initialize()
            db.update_source_failure("source", "2026-09-02T00:00:00Z", "timeout")
            db.update_source_failure("source", "2026-09-02T00:30:00Z", "timeout")
            self.assertEqual(db.source_status()[0]["consecutive_failures"], 2)
            db.update_source_success("source", "2026-09-02T01:00:00Z", "2026-09-02")
            status = db.source_status()[0]
            self.assertEqual(status["consecutive_failures"], 0)
            self.assertIsNone(status["last_error"])
            db.close()

    def test_notification_outbox_retries_until_delivered(self):
        with tempfile.TemporaryDirectory() as temp:
            db = TrackerDatabase(Path(temp) / "test.db")
            db.initialize()
            with db.transaction():
                self.assertTrue(db.save_event(sample_event()))
            db.queue_notifications([sample_event()], "2026-09-02T00:00:01+00:00")
            self.assertEqual([item.event_key for item in db.pending_notifications()], ["event-1"])

            db.mark_notifications_failed(
                ["event-1"],
                "2026-09-02T00:00:02+00:00",
                "temporary webhook failure",
            )
            self.assertEqual(len(db.pending_notifications()), 1)

            db.mark_notifications_delivered(
                ["event-1"],
                "2026-09-02T00:00:03+00:00",
            )
            self.assertEqual(db.pending_notifications(), [])
            row = db.connection.execute(
                "SELECT attempts, delivered_at, last_error FROM notification_outbox"
            ).fetchone()
            self.assertEqual(row["attempts"], 2)
            self.assertIsNotNone(row["delivered_at"])
            self.assertIsNone(row["last_error"])
            db.close()


if __name__ == "__main__":
    unittest.main()
