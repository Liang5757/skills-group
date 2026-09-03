from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable

from .db import TrackerDatabase
from .models import Confidence, EventType, HoldingObservation, OperationEvent


# Eastmoney returns ratios with many computed decimal places. Changes below
# half of the displayed four-decimal precision are not observable disclosures.
RATIO_ABSOLUTE_TOLERANCE = 0.00005


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _event_key(*parts: object) -> str:
    raw = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _confidence_for(item: HoldingObservation) -> Confidence:
    return (
        Confidence.DISCLOSED_SNAPSHOT
        if item.source_tier == "official"
        else Confidence.AGGREGATED_SNAPSHOT
    )


def _event(
    event_type: EventType,
    current: HoldingObservation | None,
    previous: HoldingObservation | None,
    *,
    period_end: str,
    scope: str,
    source: str,
    observed_at: str,
    current_evidence_url: str | None,
) -> OperationEvent:
    item = current or previous
    assert item is not None
    reasons = {
        EventType.SNAPSHOT_INCREASE: "两个已披露期末快照之间持股数量增加；无法据此确定具体交易日。",
        EventType.SNAPSHOT_DECREASE: "两个已披露期末快照之间持股数量减少；需核验交易、股本或公司行为原因。",
        EventType.ENTERED_TOP10: "本期首次进入该前十名名单；不等于本期首次买入。",
        EventType.LEFT_TOP10: "本期不再出现于该前十名名单；不等于减持或清仓。",
        EventType.RATIO_ONLY_CHANGE: "持股数量未变但披露比例变化，可能由总股本或流通股本变化导致。",
    }
    return OperationEvent(
        event_key=_event_key(
            event_type.value,
            item.entity_key,
            item.instrument_code,
            item.market,
            scope,
            period_end,
            previous.shares if previous else None,
            current.shares if current else None,
            previous.ratio if previous else None,
            current.ratio if current else None,
        ),
        event_type=event_type,
        entity_key=item.entity_key,
        holder_name=item.holder_name,
        attribution=item.attribution,
        instrument_code=item.instrument_code,
        instrument_name=item.instrument_name,
        market=item.market,
        scope=scope,
        event_date=period_end,
        # A disappearance has no issuer row in the current snapshot. Reusing
        # the previous disclosure date would falsely date the absence signal.
        published_at=current.published_at if current else None,
        previous_shares=previous.shares if previous else None,
        current_shares=current.shares if current else None,
        previous_ratio=previous.ratio if previous else None,
        current_ratio=current.ratio if current else None,
        reason=reasons[event_type],
        confidence=_confidence_for(item),
        source=source,
        evidence_url=current.evidence_url if current else (current_evidence_url or previous.evidence_url),
        created_at=observed_at,
    )


def reconcile_snapshot(
    db: TrackerDatabase,
    *,
    scope: str,
    period_end: str,
    source: str,
    observations: Iterable[HoldingObservation],
    coverage_complete: bool,
    total_rows: int,
    observed_at: str | None = None,
    current_evidence_url: str | None = None,
) -> list[OperationEvent]:
    observed_at = observed_at or utc_now()
    items = list(observations)
    if any(item.scope != scope or item.period_end != period_end for item in items):
        raise ValueError("all observations must match scope and period_end")

    current = {item.key(): item for item in items}
    if len(current) != len(items):
        raise ValueError("duplicate entity/instrument rows in one snapshot")

    previous_period = db.latest_complete_period(scope, period_end)
    previous = db.load_holdings(scope, previous_period) if previous_period else {}
    candidates: list[OperationEvent] = []

    if previous_period:
        for key, item in current.items():
            old = previous.get(key)
            if old is None:
                candidates.append(
                    _event(EventType.ENTERED_TOP10, item, None, period_end=period_end, scope=scope, source=source, observed_at=observed_at, current_evidence_url=current_evidence_url)
                )
                continue
            if item.shares is not None and old.shares is not None and item.shares != old.shares:
                event_type = EventType.SNAPSHOT_INCREASE if item.shares > old.shares else EventType.SNAPSHOT_DECREASE
                candidates.append(
                    _event(event_type, item, old, period_end=period_end, scope=scope, source=source, observed_at=observed_at, current_evidence_url=current_evidence_url)
                )
            elif (
                item.ratio is not None
                and old.ratio is not None
                and abs(item.ratio - old.ratio) >= RATIO_ABSOLUTE_TOLERANCE
            ):
                candidates.append(
                    _event(EventType.RATIO_ONLY_CHANGE, item, old, period_end=period_end, scope=scope, source=source, observed_at=observed_at, current_evidence_url=current_evidence_url)
                )

        if coverage_complete:
            for key, old in previous.items():
                if key not in current:
                    candidates.append(
                        _event(EventType.LEFT_TOP10, None, old, period_end=period_end, scope=scope, source=source, observed_at=observed_at, current_evidence_url=current_evidence_url)
                    )

    inserted: list[OperationEvent] = []
    with db.transaction():
        existing_complete = db.snapshot_is_complete(scope, period_end, source)
        if coverage_complete:
            # A complete rerun is a replacement snapshot. Keeping rows that
            # disappeared after a source correction would contaminate the next
            # quarter's comparison.
            db.delete_holdings(scope, period_end)
            for item in items:
                db.save_holding(item)
        elif not existing_complete:
            # Partial data can aid diagnostics but must never overwrite an
            # already completed snapshot or become a future baseline.
            for item in items:
                db.save_holding(item)

        if not (existing_complete and not coverage_complete):
            db.mark_snapshot_run(
                scope=scope,
                period_end=period_end,
                source=source,
                status="COMPLETE" if coverage_complete else "FAILED",
                observed_at=observed_at,
                total_rows=total_rows,
                matched_rows=len(items),
                error=None if coverage_complete else "incomplete scan; absence events suppressed",
            )
        for event in candidates:
            if db.save_event(event):
                inserted.append(event)
    return inserted
