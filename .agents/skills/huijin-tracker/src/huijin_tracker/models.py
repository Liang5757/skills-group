from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Attribution(str, Enum):
    DIRECT = "DIRECT"
    ASSET_MGMT = "ASSET_MGMT"
    NAMED_PLAN = "NAMED_PLAN"
    RELATED_CONTROLLED = "RELATED_CONTROLLED"
    UNKNOWN = "UNKNOWN"


class EventType(str, Enum):
    CONFIRMED_BUY = "CONFIRMED_BUY"
    CONFIRMED_SELL = "CONFIRMED_SELL"
    CONFIRMED_TRANSFER = "CONFIRMED_TRANSFER"
    SNAPSHOT_INCREASE = "SNAPSHOT_INCREASE"
    SNAPSHOT_DECREASE = "SNAPSHOT_DECREASE"
    ENTERED_TOP10 = "ENTERED_TOP10"
    LEFT_TOP10 = "LEFT_TOP10"
    RATIO_ONLY_CHANGE = "RATIO_ONLY_CHANGE"
    DEEMED_INTEREST_CHANGE = "DEEMED_INTEREST_CHANGE"
    DISCLOSURE = "DISCLOSURE"
    UNVERIFIED_SIGNAL = "UNVERIFIED_SIGNAL"


class Confidence(str, Enum):
    CONFIRMED_OFFICIAL = "CONFIRMED_OFFICIAL"
    DISCLOSED_SNAPSHOT = "DISCLOSED_SNAPSHOT"
    AGGREGATED_SNAPSHOT = "AGGREGATED_SNAPSHOT"
    INFERRED = "INFERRED"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class EntityMatch:
    canonical_key: str
    display_name: str
    attribution: Attribution


@dataclass(frozen=True)
class DisclosureRecord:
    source: str
    external_id: str
    title: str
    body: str
    published_at: str
    observed_at: str
    url: str
    source_tier: str = "official"


@dataclass(frozen=True)
class HoldingObservation:
    entity_key: str
    holder_name: str
    attribution: Attribution
    instrument_code: str
    instrument_name: str
    market: str
    scope: str
    period_end: str
    published_at: str | None
    shares: int | None
    ratio: float | None
    rank: int | None
    source: str
    source_tier: str
    evidence_url: str

    def key(self) -> tuple[str, str, str]:
        return self.entity_key, self.instrument_code, self.market


@dataclass(frozen=True)
class OperationEvent:
    event_key: str
    event_type: EventType
    entity_key: str
    holder_name: str
    attribution: Attribution
    instrument_code: str
    instrument_name: str
    market: str
    scope: str
    event_date: str | None
    published_at: str | None
    previous_shares: int | None
    current_shares: int | None
    previous_ratio: float | None
    current_ratio: float | None
    reason: str
    confidence: Confidence
    source: str
    evidence_url: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["event_type"] = self.event_type.value
        result["attribution"] = self.attribution.value
        result["confidence"] = self.confidence.value
        return result
