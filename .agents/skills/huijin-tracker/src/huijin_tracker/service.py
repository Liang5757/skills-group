from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from .archive import archive_bytes
from .collectors.cninfo import SOURCE as CNINFO_SOURCE
from .collectors.cninfo import CninfoCollector
from .collectors.eastmoney import SOURCE as EASTMONEY_SOURCE
from .collectors.eastmoney import EastmoneyHoldingCollector
from .collectors.huijin import SOURCE as HUIJIN_SOURCE
from .collectors.huijin import classify_post, information_center_url, parse_information_center
from .collectors.hkex import SOURCE as HKEX_SOURCE
from .collectors.hkex import HkexCollector, to_event as hkex_to_event
from .db import TrackerDatabase
from .http import HttpClient
from .models import OperationEvent
from .notifier import FeishuNotifier
from .reconcile import reconcile_snapshot


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def reporting_window_closed(period_end: str, *, as_of: date | None = None) -> bool:
    period = date.fromisoformat(period_end)
    deadlines = {
        (3, 31): date(period.year, 4, 30),
        (6, 30): date(period.year, 8, 31),
        (9, 30): date(period.year, 10, 31),
        (12, 31): date(period.year + 1, 4, 30),
    }
    try:
        deadline = deadlines[(period.month, period.day)]
    except KeyError as error:
        raise ValueError("period_end must be a calendar quarter end") from error
    return (as_of or date.today()) > deadline


class TrackerService:
    def __init__(
        self,
        db: TrackerDatabase,
        *,
        archive_dir: str | Path,
        http_client: HttpClient | None = None,
        notifier: FeishuNotifier | None = None,
    ):
        self.db = db
        self.archive_dir = Path(archive_dir)
        self.http = http_client or HttpClient()
        self.notifier = notifier or FeishuNotifier(client=self.http)

    def _notify_events(self, new_events: list[OperationEvent]) -> None:
        if not self.notifier.configured:
            return
        attempted_at = now_utc()
        self.db.queue_notifications(new_events, attempted_at)
        pending = self.db.pending_notifications()
        if not pending:
            return
        keys = [event.event_key for event in pending]
        try:
            self.notifier.send(pending)
        except Exception as error:
            self.db.mark_notifications_failed(keys, attempted_at, str(error))
            raise
        self.db.mark_notifications_delivered(keys, attempted_at)

    def retry_notifications(self) -> None:
        self._notify_events([])

    def collect_huijin(self, years: Iterable[int]) -> list[OperationEvent]:
        new_events: list[OperationEvent] = []
        attempted_at = now_utc()
        try:
            latest_record_at: str | None = None
            for year in years:
                url = information_center_url(year)
                response = self.http.get(url)
                html = response.text()
                page_id = f"information-center-{year}"
                digest, raw_path = archive_bytes(
                    self.archive_dir,
                    source=HUIJIN_SOURCE,
                    external_id=page_id,
                    content=response.body,
                    suffix="html",
                )
                self.db.upsert_document(
                    source=HUIJIN_SOURCE,
                    external_id=page_id,
                    title=f"中央汇金资讯中心 {year}",
                    published_at=f"{year}-01-01",
                    observed_at=attempted_at,
                    url=url,
                    source_tier="official",
                    sha256=digest,
                    raw_path=raw_path,
                )
                for post in parse_information_center(html):
                    post_digest = hashlib.sha256(
                        f"{post.title}\n{post.body}\n{post.url}".encode("utf-8")
                    ).hexdigest()
                    self.db.upsert_document(
                        source=HUIJIN_SOURCE,
                        external_id=post.external_id,
                        title=post.title,
                        published_at=post.published_at,
                        observed_at=attempted_at,
                        url=post.url,
                        source_tier="official",
                        sha256=post_digest,
                        raw_path=raw_path,
                        metadata={"body": post.body},
                    )
                    latest_record_at = max(latest_record_at or post.published_at, post.published_at)
                    event = classify_post(post, observed_at=attempted_at)
                    # Event idempotency is independent from document-version
                    # idempotency. Always retry event insertion so a process
                    # crash between the two commits cannot permanently lose it.
                    if event and self.db.save_event(event):
                        self.db.connection.commit()
                        new_events.append(event)
            self.db.update_source_success(HUIJIN_SOURCE, attempted_at, latest_record_at)
        except Exception as error:
            self.db.update_source_failure(HUIJIN_SOURCE, attempted_at, str(error))
            raise
        self._notify_events(new_events)
        return new_events

    def collect_cninfo(
        self,
        *,
        since: str,
        until: str,
        keywords: Iterable[str],
        plates: Iterable[str] = ("sh", "sz", "bj"),
    ) -> int:
        attempted_at = now_utc()
        collector = CninfoCollector(self.http)
        inserted_count = 0
        latest_record_at: str | None = None
        try:
            for keyword in keywords:
                for plate in plates:
                    for item in collector.query(since=since, until=until, keyword=keyword, plate=plate):
                        raw_bytes = json.dumps(item.raw, ensure_ascii=False, sort_keys=True).encode("utf-8")
                        digest, raw_path = archive_bytes(
                            self.archive_dir,
                            source=CNINFO_SOURCE,
                            external_id=item.external_id,
                            content=raw_bytes,
                            suffix="json",
                        )
                        if self.db.upsert_document(
                            source=CNINFO_SOURCE,
                            external_id=item.external_id,
                            title=item.title,
                            published_at=item.published_at,
                            observed_at=attempted_at,
                            url=item.url,
                            source_tier="official",
                            sha256=digest,
                            raw_path=raw_path,
                            metadata={
                                "security_code": item.security_code,
                                "security_name": item.security_name,
                                "query_keyword": keyword,
                            },
                        ):
                            inserted_count += 1
                        latest_record_at = max(latest_record_at or item.published_at, item.published_at)
            self.db.update_source_success(CNINFO_SOURCE, attempted_at, latest_record_at)
        except Exception as error:
            self.db.update_source_failure(CNINFO_SOURCE, attempted_at, str(error))
            raise
        return inserted_count

    def collect_hkex(self, *, since: str, until: str) -> list[OperationEvent]:
        attempted_at = now_utc()
        collector = HkexCollector(self.http)
        page_paths: dict[str, str] = {}

        def archive_page(external_id: str, title: str, url: str, content: bytes) -> None:
            digest, raw_path = archive_bytes(
                self.archive_dir,
                source=HKEX_SOURCE,
                external_id=f"{since}-{until}-{external_id}",
                content=content,
                suffix="html",
            )
            page_paths[url] = raw_path
            self.db.upsert_document(
                source=HKEX_SOURCE,
                external_id=f"page:{since}:{until}:{external_id}",
                title=title,
                published_at=until,
                observed_at=attempted_at,
                url=url,
                source_tier="official",
                sha256=digest,
                raw_path=raw_path,
                metadata={"kind": "search_result_page", "since": since, "until": until},
            )

        new_events: list[OperationEvent] = []
        latest_record_at: str | None = None
        try:
            items = collector.scan(since=since, until=until, on_page=archive_page)
            for item in items:
                structured = json.dumps(asdict(item), ensure_ascii=False, sort_keys=True).encode("utf-8")
                digest = hashlib.sha256(structured).hexdigest()
                published_at = item.filed_at or item.event_date
                self.db.upsert_document(
                    source=HKEX_SOURCE,
                    external_id=item.serial,
                    title=f"{item.serial} {item.corporation}",
                    published_at=published_at,
                    observed_at=attempted_at,
                    url=item.form_url,
                    source_tier="official",
                    sha256=digest,
                    raw_path=page_paths.get(item.list_url),
                    metadata=asdict(item),
                )
                latest_record_at = max(latest_record_at or published_at, published_at)
                event = hkex_to_event(item, observed_at=attempted_at)
                if self.db.save_event(event):
                    self.db.connection.commit()
                    new_events.append(event)
            self.db.update_source_success(HKEX_SOURCE, attempted_at, latest_record_at)
        except Exception as error:
            self.db.update_source_failure(HKEX_SOURCE, attempted_at, str(error))
            raise
        self._notify_events(new_events)
        return new_events

    def sync_eastmoney_holdings(
        self,
        *,
        period_end: str,
        scope: str,
        notify_related: bool = False,
        max_pages: int | None = None,
        force_complete: bool = False,
    ) -> list[OperationEvent]:
        attempted_at = now_utc()
        collector = EastmoneyHoldingCollector(self.http)
        try:
            def archive_page(page: int, url: str, content: bytes) -> None:
                external_id = f"{scope}-{period_end}-page-{page}"
                digest, raw_path = archive_bytes(
                    self.archive_dir,
                    source=EASTMONEY_SOURCE,
                    external_id=external_id,
                    content=content,
                    suffix="json",
                )
                self.db.upsert_document(
                    source=EASTMONEY_SOURCE,
                    external_id=external_id,
                    title=f"{scope} {period_end} page {page}",
                    published_at=period_end,
                    observed_at=attempted_at,
                    url=url,
                    source_tier="secondary",
                    sha256=digest,
                    raw_path=raw_path,
                    metadata={"scope": scope, "period_end": period_end, "page": page},
                )

            result = collector.scan(
                period_end=period_end,
                scope=scope,
                # Always store related-controlled holdings so consecutive
                # snapshots have a stable universe. They are separated at the
                # notification/output layer instead of disappearing as fake
                # LEFT_TOP10 events when a flag changes.
                include_related=True,
                max_pages=max_pages,
                on_page=archive_page,
            )
            effective_complete = result.coverage_complete and (
                force_complete or reporting_window_closed(period_end)
            )
            events = reconcile_snapshot(
                self.db,
                scope=scope,
                period_end=period_end,
                source=EASTMONEY_SOURCE,
                observations=result.observations,
                coverage_complete=effective_complete,
                total_rows=result.total_rows,
                observed_at=attempted_at,
                current_evidence_url=result.evidence_url,
            )
            self.db.update_source_success(EASTMONEY_SOURCE, attempted_at, period_end)
        except Exception as error:
            self.db.update_source_failure(EASTMONEY_SOURCE, attempted_at, str(error))
            raise
        notification_events = [
            event
            for event in events
            if notify_related or event.attribution.value != "RELATED_CONTROLLED"
        ]
        self._notify_events(notification_events)
        return events
