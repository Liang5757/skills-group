import unittest

from huijin_tracker.collectors.hkex import (
    HkexCollector,
    parse_company_links,
    parse_notice_list,
    to_event,
)
from huijin_tracker.http import HttpResponse
from huijin_tracker.models import EventType


SEARCH_HTML = b"""
<table id="grdPaging">
<tr><th>Name</th><th>Corporation</th></tr>
<tr><td><a href="NSNoticePersonList.aspx?scpid2=53980&amp;pn=Central+Huijin">Central Huijin Investment Ltd.</a></td>
<td>China Modern Dairy Holdings Ltd.</td></tr>
</table>
"""

NOTICE_HTML = b"""
<table id="grdPaging">
<tr><th>Form</th><th>Date</th><th>Corporation</th><th>Involved</th><th>Reason</th><th>Price</th><th>After</th><th>Ratio</th></tr>
<tr>
<td><a href="NSForm2.aspx?fn=CS20260319E00173">CS20260319E00173</a></td>
<td>16/03/2026</td><td>China Modern Dairy Holdings Ltd.</td>
<td>42,636,336(L)<br>42,636,336(S)</td><td>1213(L)<br>1502(S)</td><td>&nbsp;</td>
<td>507,780,342(L)<br>507,780,343(S)</td><td>6.41(L)<br>6.41(S)</td>
</tr>
</table>
"""


class FakeClient:
    def get(self, url, *, params=None):
        body = SEARCH_HTML if "NSSrchPersonList" in url else NOTICE_HTML
        return HttpResponse(url, 200, body, {"Content-Type": "text/html; charset=utf-8"})


class HkexTests(unittest.TestCase):
    def test_parses_company_and_notice_grids(self):
        companies = parse_company_links(SEARCH_HTML.decode())
        self.assertEqual(companies[0][1:], ("China Modern Dairy Holdings Ltd.", "53980"))
        notices = parse_notice_list(
            NOTICE_HTML.decode(),
            list_url=companies[0][0],
            corporation_id=companies[0][2],
        )
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].event_date, "2026-03-16")
        self.assertEqual(notices[0].filed_at, "2026-03-19")

        event = to_event(notices[0], observed_at="2026-09-02T00:00:00+00:00")
        self.assertEqual(event.event_type, EventType.DEEMED_INTEREST_CHANGE)
        self.assertEqual(event.current_shares, 507780342)
        self.assertEqual(event.current_ratio, 6.41)
        self.assertIn("不能直接等同于中央汇金买卖", event.reason)
        self.assertNotIn("|；", event.reason)

    def test_collector_archives_both_search_and_notice_pages(self):
        pages = []
        rows = HkexCollector(FakeClient(), sleep_seconds=0).scan(
            since="2026-03-01",
            until="2026-03-31",
            on_page=lambda external_id, title, url, body: pages.append((external_id, body)),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual([page[0] for page in pages], ["search", "corporation-53980"])

    def test_search_interval_is_bounded(self):
        with self.assertRaises(ValueError):
            HkexCollector(FakeClient(), sleep_seconds=0).scan(
                since="2024-01-01",
                until="2026-01-01",
            )


if __name__ == "__main__":
    unittest.main()
