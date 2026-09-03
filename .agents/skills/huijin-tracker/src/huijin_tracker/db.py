from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Iterator

from .models import Attribution, Confidence, EventType, HoldingObservation, OperationEvent


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS source_documents (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    published_at TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    url TEXT NOT NULL,
    source_tier TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    raw_path TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(source, external_id, sha256)
);

CREATE TABLE IF NOT EXISTS holding_snapshots (
    id INTEGER PRIMARY KEY,
    entity_key TEXT NOT NULL,
    holder_name TEXT NOT NULL,
    attribution TEXT NOT NULL,
    instrument_code TEXT NOT NULL,
    instrument_name TEXT NOT NULL,
    market TEXT NOT NULL,
    scope TEXT NOT NULL,
    period_end TEXT NOT NULL,
    published_at TEXT,
    shares INTEGER,
    ratio REAL,
    rank INTEGER,
    source TEXT NOT NULL,
    source_tier TEXT NOT NULL,
    evidence_url TEXT NOT NULL,
    UNIQUE(entity_key, instrument_code, market, scope, period_end)
);

CREATE TABLE IF NOT EXISTS snapshot_runs (
    scope TEXT NOT NULL,
    period_end TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('COMPLETE', 'FAILED')),
    observed_at TEXT NOT NULL,
    total_rows INTEGER NOT NULL DEFAULT 0,
    matched_rows INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    PRIMARY KEY(scope, period_end, source)
);

CREATE TABLE IF NOT EXISTS events (
    event_key TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    holder_name TEXT NOT NULL,
    attribution TEXT NOT NULL,
    instrument_code TEXT NOT NULL,
    instrument_name TEXT NOT NULL,
    market TEXT NOT NULL,
    scope TEXT NOT NULL,
    event_date TEXT,
    published_at TEXT,
    previous_shares INTEGER,
    current_shares INTEGER,
    previous_ratio REAL,
    current_ratio REAL,
    reason TEXT NOT NULL,
    confidence TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence_url TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_watermarks (
    source TEXT PRIMARY KEY,
    last_attempt_at TEXT NOT NULL,
    last_success_at TEXT,
    last_record_at TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS notification_outbox (
    event_key TEXT PRIMARY KEY REFERENCES events(event_key) ON DELETE CASCADE,
    queued_at TEXT NOT NULL,
    delivered_at TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_holdings_period ON holding_snapshots(scope, period_end);
"""


class TrackerDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")

    def close(self) -> None:
        self.connection.close()

    def initialize(self) -> None:
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self.connection.execute("BEGIN")
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def upsert_document(
        self,
        *,
        source: str,
        external_id: str,
        title: str,
        published_at: str,
        observed_at: str,
        url: str,
        source_tier: str,
        sha256: str,
        raw_path: str | None,
        metadata: dict | None = None,
    ) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO source_documents
            (source, external_id, title, published_at, observed_at, url, source_tier, sha256, raw_path, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                external_id,
                title,
                published_at,
                observed_at,
                url,
                source_tier,
                sha256,
                raw_path,
                json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
            ),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def save_holding(self, item: HoldingObservation) -> None:
        self.connection.execute(
            """
            INSERT INTO holding_snapshots
            (entity_key, holder_name, attribution, instrument_code, instrument_name, market, scope,
             period_end, published_at, shares, ratio, rank, source, source_tier, evidence_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_key, instrument_code, market, scope, period_end) DO UPDATE SET
              holder_name=excluded.holder_name,
              attribution=excluded.attribution,
              instrument_name=excluded.instrument_name,
              published_at=excluded.published_at,
              shares=excluded.shares,
              ratio=excluded.ratio,
              rank=excluded.rank,
              source=excluded.source,
              source_tier=excluded.source_tier,
              evidence_url=excluded.evidence_url
            """,
            (
                item.entity_key,
                item.holder_name,
                item.attribution.value,
                item.instrument_code,
                item.instrument_name,
                item.market,
                item.scope,
                item.period_end,
                item.published_at,
                item.shares,
                item.ratio,
                item.rank,
                item.source,
                item.source_tier,
                item.evidence_url,
            ),
        )

    def delete_holdings(self, scope: str, period_end: str) -> None:
        self.connection.execute(
            "DELETE FROM holding_snapshots WHERE scope=? AND period_end=?",
            (scope, period_end),
        )

    def snapshot_is_complete(self, scope: str, period_end: str, source: str) -> bool:
        row = self.connection.execute(
            """
            SELECT 1 FROM snapshot_runs
            WHERE scope=? AND period_end=? AND source=? AND status='COMPLETE'
            """,
            (scope, period_end, source),
        ).fetchone()
        return row is not None

    def mark_snapshot_run(
        self,
        *,
        scope: str,
        period_end: str,
        source: str,
        status: str,
        observed_at: str,
        total_rows: int,
        matched_rows: int,
        error: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO snapshot_runs
            (scope, period_end, source, status, observed_at, total_rows, matched_rows, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope, period_end, source) DO UPDATE SET
              status=excluded.status,
              observed_at=excluded.observed_at,
              total_rows=excluded.total_rows,
              matched_rows=excluded.matched_rows,
              error=excluded.error
            """,
            (scope, period_end, source, status, observed_at, total_rows, matched_rows, error),
        )

    def latest_complete_period(self, scope: str, before: str) -> str | None:
        row = self.connection.execute(
            """
            SELECT period_end FROM snapshot_runs
            WHERE scope=? AND period_end<? AND status='COMPLETE'
            ORDER BY period_end DESC LIMIT 1
            """,
            (scope, before),
        ).fetchone()
        return str(row[0]) if row else None

    def load_holdings(self, scope: str, period_end: str) -> dict[tuple[str, str, str], HoldingObservation]:
        rows = self.connection.execute(
            "SELECT * FROM holding_snapshots WHERE scope=? AND period_end=?",
            (scope, period_end),
        ).fetchall()
        result: dict[tuple[str, str, str], HoldingObservation] = {}
        for row in rows:
            item = HoldingObservation(
                entity_key=row["entity_key"],
                holder_name=row["holder_name"],
                attribution=Attribution(row["attribution"]),
                instrument_code=row["instrument_code"],
                instrument_name=row["instrument_name"],
                market=row["market"],
                scope=row["scope"],
                period_end=row["period_end"],
                published_at=row["published_at"],
                shares=row["shares"],
                ratio=row["ratio"],
                rank=row["rank"],
                source=row["source"],
                source_tier=row["source_tier"],
                evidence_url=row["evidence_url"],
            )
            result[item.key()] = item
        return result

    def save_event(self, event: OperationEvent) -> bool:
        values = event.to_dict()
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO events
            (event_key, event_type, entity_key, holder_name, attribution, instrument_code,
             instrument_name, market, scope, event_date, published_at, previous_shares,
             current_shares, previous_ratio, current_ratio, reason, confidence, source,
             evidence_url, created_at)
            VALUES (:event_key, :event_type, :entity_key, :holder_name, :attribution, :instrument_code,
                    :instrument_name, :market, :scope, :event_date, :published_at, :previous_shares,
                    :current_shares, :previous_ratio, :current_ratio, :reason, :confidence, :source,
                    :evidence_url, :created_at)
            """,
            values,
        )
        return cursor.rowcount > 0

    def queue_notifications(self, events: Iterable[OperationEvent], queued_at: str) -> None:
        self.connection.executemany(
            """
            INSERT OR IGNORE INTO notification_outbox (event_key, queued_at)
            VALUES (?, ?)
            """,
            ((event.event_key, queued_at) for event in events),
        )
        self.connection.commit()

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> OperationEvent:
        return OperationEvent(
            event_key=row["event_key"],
            event_type=EventType(row["event_type"]),
            entity_key=row["entity_key"],
            holder_name=row["holder_name"],
            attribution=Attribution(row["attribution"]),
            instrument_code=row["instrument_code"],
            instrument_name=row["instrument_name"],
            market=row["market"],
            scope=row["scope"],
            event_date=row["event_date"],
            published_at=row["published_at"],
            previous_shares=row["previous_shares"],
            current_shares=row["current_shares"],
            previous_ratio=row["previous_ratio"],
            current_ratio=row["current_ratio"],
            reason=row["reason"],
            confidence=Confidence(row["confidence"]),
            source=row["source"],
            evidence_url=row["evidence_url"],
            created_at=row["created_at"],
        )

    def pending_notifications(self, limit: int = 100) -> list[OperationEvent]:
        rows = self.connection.execute(
            """
            SELECT events.* FROM notification_outbox
            JOIN events USING(event_key)
            WHERE delivered_at IS NULL
            ORDER BY queued_at, event_key
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def mark_notifications_delivered(self, event_keys: Iterable[str], attempted_at: str) -> None:
        self.connection.executemany(
            """
            UPDATE notification_outbox
            SET delivered_at=?, last_attempt_at=?, attempts=attempts+1, last_error=NULL
            WHERE event_key=?
            """,
            ((attempted_at, attempted_at, key) for key in event_keys),
        )
        self.connection.commit()

    def mark_notifications_failed(
        self,
        event_keys: Iterable[str],
        attempted_at: str,
        error: str,
    ) -> None:
        self.connection.executemany(
            """
            UPDATE notification_outbox
            SET last_attempt_at=?, attempts=attempts+1, last_error=?
            WHERE event_key=?
            """,
            ((attempted_at, error[:2000], key) for key in event_keys),
        )
        self.connection.commit()

    def list_events(self, limit: int = 100, *, include_related: bool = False) -> list[dict]:
        if include_related:
            sql = "SELECT * FROM events ORDER BY created_at DESC, event_key LIMIT ?"
            params = (limit,)
        else:
            sql = """
                SELECT * FROM events WHERE attribution != 'RELATED_CONTROLLED'
                ORDER BY created_at DESC, event_key LIMIT ?
            """
            params = (limit,)
        rows = self.connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def update_source_success(self, source: str, attempted_at: str, record_at: str | None = None) -> None:
        self.connection.execute(
            """
            INSERT INTO source_watermarks
            (source, last_attempt_at, last_success_at, last_record_at, consecutive_failures, last_error)
            VALUES (?, ?, ?, ?, 0, NULL)
            ON CONFLICT(source) DO UPDATE SET
              last_attempt_at=excluded.last_attempt_at,
              last_success_at=excluded.last_success_at,
              last_record_at=COALESCE(excluded.last_record_at, source_watermarks.last_record_at),
              consecutive_failures=0,
              last_error=NULL
            """,
            (source, attempted_at, attempted_at, record_at),
        )
        self.connection.commit()

    def update_source_failure(self, source: str, attempted_at: str, error: str) -> None:
        self.connection.execute(
            """
            INSERT INTO source_watermarks
            (source, last_attempt_at, consecutive_failures, last_error)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(source) DO UPDATE SET
              last_attempt_at=excluded.last_attempt_at,
              consecutive_failures=source_watermarks.consecutive_failures + 1,
              last_error=excluded.last_error
            """,
            (source, attempted_at, error[:2000]),
        )
        self.connection.commit()

    def source_status(self) -> list[dict]:
        rows = self.connection.execute(
            "SELECT * FROM source_watermarks ORDER BY source"
        ).fetchall()
        return [dict(row) for row in rows]

    def count(self, table: str) -> int:
        if table not in {
            "source_documents",
            "holding_snapshots",
            "snapshot_runs",
            "events",
            "notification_outbox",
        }:
            raise ValueError(f"unsupported table: {table}")
        row = self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])
