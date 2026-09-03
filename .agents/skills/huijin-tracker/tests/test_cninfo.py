import json
import unittest

from huijin_tracker.collectors.cninfo import CninfoCollector
from huijin_tracker.http import HttpResponse


class FakeClient:
    def post_form(self, url, data):
        payload = {
            "hasMore": False,
            "announcements": [
                {
                    "announcementId": "relevant",
                    "secCode": "601988",
                    "secName": "中国银行",
                    "announcementTitle": "关于<em>中央汇金</em>投资有限责任公司增持的公告",
                    "announcementTime": 1777478400000,
                    "adjunctUrl": "finalpage/relevant.pdf",
                },
                {
                    "announcementId": "noise",
                    "secCode": "000001",
                    "secName": "噪声公司",
                    "announcementTitle": "募集资金存放与管理专项报告",
                    "announcementTime": 1777478400000,
                    "adjunctUrl": "finalpage/noise.pdf",
                },
            ],
        }
        return HttpResponse(url, 200, json.dumps(payload).encode(), {"Content-Type": "application/json"})


class CninfoTests(unittest.TestCase):
    def test_fuzzy_server_results_are_literal_filtered(self):
        rows = list(
            CninfoCollector(FakeClient()).query(
                since="2026-01-01",
                until="2026-12-31",
                keyword="中央汇金",
                plate="sh",
            )
        )
        self.assertEqual([row.external_id for row in rows], ["relevant"])
        self.assertNotIn("<em>", rows[0].title)


if __name__ == "__main__":
    unittest.main()
