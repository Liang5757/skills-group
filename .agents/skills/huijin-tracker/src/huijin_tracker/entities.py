from __future__ import annotations

import re
import unicodedata
import hashlib

from .models import Attribution, EntityMatch


DIRECT_NAMES = {
    "中央汇金投资有限责任公司",
    "central huijin investment ltd.",
    "central huijin investment ltd",
    "central huijin investment limited",
}

ASSET_MGMT_NAMES = {
    "中央汇金资产管理有限责任公司",
    "central huijin asset management ltd.",
    "central huijin asset management ltd",
    "central huijin asset management limited",
}

RELATED_NAMES = {
    "中国证券金融股份有限公司",
    "china securities finance corporation limited",
    "china securities finance corporation ltd.",
}

_PLAN_MARKERS = (
    "汇金资管单一资产管理计划",
    "中央汇金资产管理有限责任公司",
    "central huijin asset management",
)


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"[\s\u3000]+", " ", value).strip()
    return value.casefold()


def match_entity(holder_name: str) -> EntityMatch:
    normalized = normalize_name(holder_name)

    if "资产管理计划" in normalized and any(
        marker.casefold() in normalized for marker in _PLAN_MARKERS
    ):
        # Different named plans are different legal accounts. Collapsing all of
        # them into one key would merge holdings when two plans own the same
        # security.
        identity = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
        return EntityMatch(f"huijin_named_plan:{identity}", holder_name.strip(), Attribution.NAMED_PLAN)

    if normalized in DIRECT_NAMES:
        return EntityMatch(
            "central_huijin_investment",
            "中央汇金投资有限责任公司",
            Attribution.DIRECT,
        )

    if normalized in ASSET_MGMT_NAMES:
        return EntityMatch(
            "central_huijin_asset_management",
            "中央汇金资产管理有限责任公司",
            Attribution.ASSET_MGMT,
        )

    if normalized in RELATED_NAMES:
        return EntityMatch(
            "china_securities_finance",
            "中国证券金融股份有限公司",
            Attribution.RELATED_CONTROLLED,
        )

    return EntityMatch("unknown", holder_name.strip(), Attribution.UNKNOWN)


def is_tracked_entity(holder_name: str, *, include_related: bool = True) -> bool:
    match = match_entity(holder_name)
    if match.attribution == Attribution.UNKNOWN:
        return False
    if match.attribution == Attribution.RELATED_CONTROLLED and not include_related:
        return False
    return True
