from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator

from ..http import HttpClient


SOURCE = "cninfo"
QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
PDF_BASE = "https://static.cninfo.com.cn/"
BEIJING = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class CninfoAnnouncement:
    external_id: str
    security_code: str
    security_name: str
    title: str
    published_at: str
    url: str
    raw: dict


def clean_title(value: str | None) -> str:
    return re.sub(r"</?em>", "", value or "").strip()


def _date_from_epoch_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=BEIJING).date().isoformat()


class CninfoCollector:
    def __init__(self, client: HttpClient | None = None, *, sleep_seconds: float = 0.4):
        self.client = client or HttpClient()
        self.sleep_seconds = sleep_seconds

    def query(
        self,
        *,
        since: str,
        until: str,
        keyword: str,
        plate: str,
        max_pages: int = 100,
    ) -> Iterator[CninfoAnnouncement]:
        column = "sse" if plate == "sh" else "szse"
        for page in range(1, max_pages + 1):
            body = {
                "tabName": "fulltext",
                "pageSize": "30",
                "pageNum": str(page),
                "column": column,
                "category": "",
                "plate": plate,
                "searchkey": keyword,
                "secid": "",
                "trade": "",
                "seDate": f"{since}~{until}",
                "stock": "",
                "sortName": "",
                "sortType": "",
                "isHLtitle": "true",
            }
            payload = self.client.post_form(QUERY_URL, body).json()
            announcements = payload.get("announcements") or []
            if not announcements:
                return
            for item in announcements:
                title = clean_title(item.get("announcementTitle"))
                # CNINFO's searchkey behaves like a broad fuzzy matcher and may return
                # unrelated phrases such as "募集资金管理" for "汇金资管". Keep only
                # literal phrase hits before data reaches the evidence ledger.
                if keyword not in title:
                    continue
                path = str(item.get("adjunctUrl") or "")
                external_id = str(item.get("announcementId") or path)
                yield CninfoAnnouncement(
                    external_id=external_id,
                    security_code=str(item.get("secCode") or ""),
                    security_name=str(item.get("secName") or ""),
                    title=title,
                    published_at=_date_from_epoch_ms(int(item.get("announcementTime") or 0)),
                    url=PDF_BASE + path.lstrip("/"),
                    raw=item,
                )
            if not payload.get("hasMore"):
                return
            if self.sleep_seconds:
                time.sleep(self.sleep_seconds)
