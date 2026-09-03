import tempfile
import unittest
from pathlib import Path

from huijin_tracker.db import TrackerDatabase
from huijin_tracker.models import Attribution, EventType, HoldingObservation
from huijin_tracker.reconcile import reconcile_snapshot


def holding(
    code: str,
    period: str,
    *,
    shares: int,
    ratio: float,
    name: str = "中央汇金资产管理有限责任公司",
) -> HoldingObservation:
    return HoldingObservation(
        entity_key="central_huijin_asset_management",
        holder_name=name,
        attribution=Attribution.ASSET_MGMT,
        instrument_code=code,
        instrument_name=f"股票{code}",
        market="SH",
        scope="top10_float",
        period_end=period,
        published_at=period,
        shares=shares,
        ratio=ratio,
        rank=5,
        source="fixture",
        source_tier="secondary",
        evidence_url="https://example.test/evidence",
    )


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = TrackerDatabase(Path(self.temp.name) / "tracker.db")
        self.db.initialize()

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_baseline_then_semantic_diff_and_idempotency(self):
        baseline = [
            holding("600001.SH", "2025-12-31", shares=100, ratio=1.0),
            holding("600002.SH", "2025-12-31", shares=200, ratio=2.0),
            holding("600003.SH", "2025-12-31", shares=300, ratio=3.0),
            holding("600004.SH", "2025-12-31", shares=400, ratio=4.0),
        ]
        self.assertEqual(
            reconcile_snapshot(
                self.db,
                scope="top10_float",
                period_end="2025-12-31",
                source="fixture",
                observations=baseline,
                coverage_complete=True,
                total_rows=4,
                observed_at="2026-04-01T00:00:00+00:00",
            ),
            [],
        )

        current = [
            holding("600001.SH", "2026-03-31", shares=150, ratio=1.5),
            holding("600002.SH", "2026-03-31", shares=180, ratio=1.8),
            holding("600003.SH", "2026-03-31", shares=300, ratio=2.9),
            holding("600005.SH", "2026-03-31", shares=500, ratio=5.0),
        ]
        events = reconcile_snapshot(
            self.db,
            scope="top10_float",
            period_end="2026-03-31",
            source="fixture",
            observations=current,
            coverage_complete=True,
            total_rows=4,
            observed_at="2026-05-01T00:00:00+00:00",
        )
        self.assertCountEqual(
            [event.event_type for event in events],
            [
                EventType.SNAPSHOT_INCREASE,
                EventType.SNAPSHOT_DECREASE,
                EventType.RATIO_ONLY_CHANGE,
                EventType.ENTERED_TOP10,
                EventType.LEFT_TOP10,
            ],
        )
        left = next(event for event in events if event.event_type == EventType.LEFT_TOP10)
        self.assertIn("不等于减持或清仓", left.reason)
        self.assertIsNone(left.published_at)

        rerun = reconcile_snapshot(
            self.db,
            scope="top10_float",
            period_end="2026-03-31",
            source="fixture",
            observations=current,
            coverage_complete=True,
            total_rows=4,
            observed_at="2026-05-02T00:00:00+00:00",
        )
        self.assertEqual(rerun, [])
        self.assertEqual(self.db.count("events"), 5)

    def test_incomplete_scan_suppresses_left_top10(self):
        reconcile_snapshot(
            self.db,
            scope="top10_float",
            period_end="2025-12-31",
            source="fixture",
            observations=[holding("600001.SH", "2025-12-31", shares=100, ratio=1)],
            coverage_complete=True,
            total_rows=1,
        )
        events = reconcile_snapshot(
            self.db,
            scope="top10_float",
            period_end="2026-03-31",
            source="fixture",
            observations=[],
            coverage_complete=False,
            total_rows=100,
        )
        self.assertEqual(events, [])

    def test_ratio_noise_below_display_precision_is_suppressed(self):
        reconcile_snapshot(
            self.db,
            scope="top10_float",
            period_end="2025-12-31",
            source="fixture",
            observations=[holding("600001.SH", "2025-12-31", shares=100, ratio=1.286207059174)],
            coverage_complete=True,
            total_rows=1,
        )
        events = reconcile_snapshot(
            self.db,
            scope="top10_float",
            period_end="2026-03-31",
            source="fixture",
            observations=[holding("600001.SH", "2026-03-31", shares=100, ratio=1.286205399175)],
            coverage_complete=True,
            total_rows=1,
        )
        self.assertEqual(events, [])

    def test_left_top10_uses_current_scan_evidence(self):
        reconcile_snapshot(
            self.db,
            scope="top10_float",
            period_end="2025-12-31",
            source="fixture",
            observations=[holding("600001.SH", "2025-12-31", shares=100, ratio=1)],
            coverage_complete=True,
            total_rows=1,
        )
        events = reconcile_snapshot(
            self.db,
            scope="top10_float",
            period_end="2026-03-31",
            source="fixture",
            observations=[],
            coverage_complete=True,
            total_rows=100,
            current_evidence_url="https://example.test/current-scan",
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].evidence_url, "https://example.test/current-scan")
        self.assertIsNone(events[0].published_at)


if __name__ == "__main__":
    unittest.main()
