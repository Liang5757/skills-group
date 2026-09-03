from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Callable
from urllib.parse import urlencode

from ..entities import match_entity
from ..http import HttpClient
from ..models import Attribution, HoldingObservation


SOURCE = "eastmoney_holder_aggregate"
API_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"


@dataclass(frozen=True)
class HoldingScanResult:
    observations: list[HoldingObservation]
    total_rows: int
    pages_fetched: int
    coverage_complete: bool
    evidence_url: str


PageObserver = Callable[[int, str, bytes], None]


_SCOPES = {
    "top10_float": {
        "report": "RPT_F10_EH_FREEHOLDERS",
        "sort": "UPDATE_DATE,SECURITY_CODE,HOLDER_RANK",
        "rank": "HOLDER_RANK",
        "ratio": "FREE_HOLDNUM_RATIO",
        "published": "UPDATE_DATE",
    },
    "top10": {
        "report": "RPT_DMSK_HOLDERS",
        "sort": "NOTICE_DATE,SECURITY_CODE,RANK",
        "rank": "RANK",
        "ratio": "HOLD_RATIO",
        "published": "NOTICE_DATE",
    },
}


def _iso_date(value: object) -> str | None:
    if value is None or value == "":
        return None
    return str(value)[:10]


def _integer(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(round(float(value)))


def _number(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


class EastmoneyHoldingCollector:
    def __init__(self, client: HttpClient | None = None, *, sleep_seconds: float = 0.15):
        self.client = client or HttpClient()
        self.sleep_seconds = sleep_seconds

    def scan(
        self,
        *,
        period_end: str,
        scope: str,
        include_related: bool = True,
        max_pages: int | None = None,
        on_page: PageObserver | None = None,
    ) -> HoldingScanResult:
        if scope not in _SCOPES:
            raise ValueError(f"unsupported scope: {scope}")
        settings = _SCOPES[scope]
        period = date.fromisoformat(period_end).isoformat()
        base_params = {
            "sortColumns": settings["sort"],
            "sortTypes": "-1,1,1",
            "pageSize": "2000",
            "reportName": settings["report"],
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f"(END_DATE='{period}')",
        }
        scan_evidence_url = f"{API_URL}?{urlencode(base_params)}"
        observations: list[HoldingObservation] = []
        total_rows = 0
        pages_fetched = 0
        rows_fetched = 0
        expected_pages: int | None = None

        page = 1
        while expected_pages is None or page <= expected_pages:
            params = dict(base_params)
            params["pageNumber"] = str(page)
            response = self.client.get(API_URL, params=params)
            payload = response.json()
            if not payload.get("success"):
                raise RuntimeError(f"Eastmoney response failed: {payload.get('message')}")
            result = payload.get("result") or {}
            if expected_pages is None:
                expected_pages = int(result.get("pages") or 0)
                total_rows = int(result.get("count") or 0)
                if max_pages is not None:
                    expected_pages = min(expected_pages, max_pages)
            rows = result.get("data") or []
            pages_fetched += 1
            evidence_url = f"{API_URL}?{urlencode(params)}"
            rows_fetched += len(rows)
            if on_page:
                on_page(page, evidence_url, response.body)
            for row in rows:
                holder_name = str(row.get("HOLDER_NAME") or "").strip()
                entity = match_entity(holder_name)
                if entity.attribution == Attribution.UNKNOWN:
                    continue
                if entity.attribution == Attribution.RELATED_CONTROLLED and not include_related:
                    continue
                code = str(row.get("SECUCODE") or row.get("SECURITY_CODE") or "")
                market = code.rsplit(".", 1)[-1] if "." in code else "CN"
                observations.append(
                    HoldingObservation(
                        entity_key=entity.canonical_key,
                        holder_name=holder_name,
                        attribution=entity.attribution,
                        instrument_code=code,
                        instrument_name=str(row.get("SECURITY_NAME_ABBR") or ""),
                        market=market,
                        scope=scope,
                        period_end=period,
                        published_at=_iso_date(row.get(settings["published"])),
                        shares=_integer(row.get("HOLD_NUM")),
                        ratio=_number(row.get(settings["ratio"])),
                        rank=_integer(row.get(settings["rank"])),
                        source=SOURCE,
                        source_tier="secondary",
                        evidence_url=evidence_url,
                    )
                )
            page += 1
            if page <= (expected_pages or 0) and self.sleep_seconds:
                time.sleep(self.sleep_seconds)

        actual_total_pages = int(payload.get("result", {}).get("pages") or 0) if pages_fetched else 0
        coverage_complete = (
            max_pages is None
            and pages_fetched >= actual_total_pages
            and rows_fetched >= total_rows
        )
        return HoldingScanResult(
            observations,
            total_rows,
            pages_fetched,
            coverage_complete,
            scan_evidence_url,
        )
