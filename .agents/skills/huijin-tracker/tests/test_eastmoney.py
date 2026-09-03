import json
import unittest

from huijin_tracker.collectors.eastmoney import EastmoneyHoldingCollector
from huijin_tracker.http import HttpResponse
from huijin_tracker.models import Attribution


class FakeClient:
    def get(self, url, *, params=None):
        page = int(params["pageNumber"])
        rows = {
            1: [
                {
                    "SECUCODE": "601318.SH",
                    "SECURITY_NAME_ABBR": "中国平安",
                    "HOLDER_NAME": "中央汇金资产管理有限责任公司",
                    "HOLD_NUM": 470302300,
                    "FREE_HOLDNUM_RATIO": 2.6,
                    "HOLDER_RANK": 5,
                    "UPDATE_DATE": "2026-04-30 00:00:00",
                },
                {"SECUCODE": "000001.SZ", "HOLDER_NAME": "普通股东"},
            ],
            2: [
                {
                    "SECUCODE": "000166.SZ",
                    "SECURITY_NAME_ABBR": "申万宏源",
                    "HOLDER_NAME": "中国证券金融股份有限公司",
                    "HOLD_NUM": 635215426,
                    "FREE_HOLDNUM_RATIO": 2.54,
                    "HOLDER_RANK": 6,
                    "UPDATE_DATE": "2026-03-31 00:00:00",
                }
            ],
        }[page]
        payload = {"success": True, "result": {"pages": 2, "count": 3, "data": rows}}
        return HttpResponse(url, 200, json.dumps(payload).encode(), {"Content-Type": "application/json"})


class ShortPageClient(FakeClient):
    def get(self, url, *, params=None):
        response = super().get(url, params=params)
        payload = response.json()
        if int(params["pageNumber"]) == 2:
            payload["result"]["data"] = []
        return HttpResponse(url, 200, json.dumps(payload).encode(), {"Content-Type": "application/json"})


class EastmoneyCollectorTests(unittest.TestCase):
    def test_paginated_full_market_scan_and_related_label(self):
        result = EastmoneyHoldingCollector(FakeClient(), sleep_seconds=0).scan(
            period_end="2026-03-31", scope="top10_float"
        )
        self.assertTrue(result.coverage_complete)
        self.assertEqual(result.total_rows, 3)
        self.assertEqual(len(result.observations), 2)
        self.assertEqual(result.observations[0].attribution, Attribution.ASSET_MGMT)
        self.assertEqual(result.observations[1].attribution, Attribution.RELATED_CONTROLLED)
        self.assertIn("END_DATE", result.evidence_url)
        self.assertNotIn("pageNumber", result.evidence_url)

    def test_page_limit_marks_scan_incomplete(self):
        result = EastmoneyHoldingCollector(FakeClient(), sleep_seconds=0).scan(
            period_end="2026-03-31", scope="top10_float", max_pages=1
        )
        self.assertFalse(result.coverage_complete)

    def test_row_count_mismatch_marks_scan_incomplete(self):
        result = EastmoneyHoldingCollector(ShortPageClient(), sleep_seconds=0).scan(
            period_end="2026-03-31", scope="top10_float"
        )
        self.assertFalse(result.coverage_complete)

    def test_page_observer_receives_raw_evidence(self):
        pages = []
        EastmoneyHoldingCollector(FakeClient(), sleep_seconds=0).scan(
            period_end="2026-03-31",
            scope="top10_float",
            on_page=lambda page, url, body: pages.append((page, url, body)),
        )
        self.assertEqual([page[0] for page in pages], [1, 2])
        self.assertTrue(all(page[2].startswith(b"{") for page in pages))


if __name__ == "__main__":
    unittest.main()
