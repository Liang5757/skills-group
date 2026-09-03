import unittest
from pathlib import Path

from huijin_tracker.collectors.huijin import HuijinPost, classify_post, parse_information_center
from huijin_tracker.models import EventType


FIXTURE = Path(__file__).parent / "fixtures" / "huijin_information_center.html"


class HuijinCollectorTests(unittest.TestCase):
    def test_parse_and_classify_only_actionable_post(self):
        posts = parse_information_center(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[1].published_at, "2025-04-07")
        self.assertIsNone(classify_post(posts[0]))
        event = classify_post(posts[1], observed_at="2026-09-02T00:00:00+00:00")
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.event_type, EventType.CONFIRMED_BUY)
        self.assertEqual(event.instrument_name, "ETF")
        self.assertIn("未给出具体规模", event.reason)

    def test_plan_or_future_intent_is_not_a_confirmed_trade(self):
        post = HuijinPost(
            "plan",
            "增持计划",
            "中央汇金公司拟增持ETF，未来将继续增持。",
            "2026-09-02",
            "https://example.test/plan",
        )
        self.assertIsNone(classify_post(post))

    def test_completed_transfer_takes_precedence_over_holding_increase_wording(self):
        post = HuijinPost(
            "transfer",
            "股份划转公告",
            "中央汇金公司已完成股份划转，受让方持股相应增加。",
            "2026-09-02",
            "https://example.test/transfer",
        )
        event = classify_post(post)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.event_type, EventType.CONFIRMED_TRANSFER)


if __name__ == "__main__":
    unittest.main()
