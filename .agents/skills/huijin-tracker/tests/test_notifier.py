import unittest

from huijin_tracker.models import Attribution, Confidence, EventType, OperationEvent
from huijin_tracker.notifier import render_event, summarize_events


def event() -> OperationEvent:
    return OperationEvent(
        event_key="key",
        event_type=EventType.LEFT_TOP10,
        entity_key="central_huijin_asset_management",
        holder_name="中央汇金资产管理有限责任公司",
        attribution=Attribution.ASSET_MGMT,
        instrument_code="600001.SH",
        instrument_name="示例",
        market="SH",
        scope="top10_float",
        event_date="2026-03-31",
        published_at=None,
        previous_shares=100,
        current_shares=None,
        previous_ratio=1.2,
        current_ratio=None,
        reason="退出名单不等于卖出。",
        confidence=Confidence.AGGREGATED_SNAPSHOT,
        source="fixture",
        evidence_url="https://example.test/current",
        created_at="2026-05-01T00:00:00+00:00",
    )


class NotifierTests(unittest.TestCase):
    def test_missing_ratio_does_not_render_as_dash_percent(self):
        rendered = render_event(event())
        self.assertIn("比例: 1.2% → —", rendered)
        self.assertNotIn("—%", rendered)

    def test_summary_has_type_and_attribution_counts(self):
        rendered = summarize_events([event(), event()])
        self.assertIn("LEFT_TOP10=2", rendered)
        self.assertIn("ASSET_MGMT=2", rendered)


if __name__ == "__main__":
    unittest.main()
