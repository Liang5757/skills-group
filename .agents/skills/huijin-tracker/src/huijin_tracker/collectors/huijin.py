from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin

from ..models import Attribution, Confidence, EventType, OperationEvent


SOURCE = "huijin_official"
BASE_URL = "https://www.huijin-inv.cn/huijin-inv/"


@dataclass(frozen=True)
class HuijinPost:
    external_id: str
    title: str
    body: str
    published_at: str
    url: str


class _InformationCenterParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.posts: list[HuijinPost] = []
        self.current: dict[str, object] | None = None
        self.div_depth = 0
        self.capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "div" and "infor-list-item" in classes and self.current is None:
            self.current = {"title": [], "body": [], "day": [], "year": [], "href": ""}
            self.div_depth = 1
            return
        if self.current is None:
            return
        if tag == "div":
            self.div_depth += 1
        if tag == "h1":
            self.capture = "title"
        elif tag == "p":
            self.capture = "body"
        elif tag == "span" and "day" in classes:
            self.capture = "day"
        elif tag == "span" and "year" in classes:
            self.capture = "year"
        elif tag == "a" and values.get("href"):
            self.current["href"] = values["href"]

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if tag in {"h1", "p", "span"}:
            self.capture = None
        if tag == "div":
            self.div_depth -= 1
            if self.div_depth == 0:
                self._finish_post()

    def handle_data(self, data: str) -> None:
        if self.current is not None and self.capture:
            parts = self.current[self.capture]
            assert isinstance(parts, list)
            parts.append(data)

    @staticmethod
    def _text(parts: object) -> str:
        assert isinstance(parts, list)
        return " ".join("".join(parts).split())

    def _finish_post(self) -> None:
        assert self.current is not None
        title = self._text(self.current["title"])
        body = self._text(self.current["body"])
        day = self._text(self.current["day"])
        year_month = self._text(self.current["year"])
        href = str(self.current["href"])
        if title and href and re.fullmatch(r"\d{4}\.\d{2}", year_month) and day.isdigit():
            published_at = f"{year_month.replace('.', '-')}-{int(day):02d}"
            url = urljoin(self.base_url, href)
            external_id = href.rstrip("/").rsplit("/", 1)[-1].removesuffix(".shtml")
            self.posts.append(HuijinPost(external_id, title, body, published_at, url))
        self.current = None
        self.capture = None


def parse_information_center(html: str, *, base_url: str = BASE_URL) -> list[HuijinPost]:
    parser = _InformationCenterParser(base_url)
    parser.feed(html)
    return parser.posts


def information_center_url(year: int) -> str:
    if year >= 2025:
        return f"{BASE_URL}SC{year}2/Information_Center.shtml"
    if year == 2024:
        return f"{BASE_URL}c100077/Information_Center.shtml"
    if year == 2023:
        return f"{BASE_URL}c100074/Information_Center.shtml"
    return f"{BASE_URL}Corporate_History/{year}.shtml"


def _completed_action(text: str, terms: str) -> bool:
    patterns = (
        rf"(?:已|已经|本次|累计|完成|于[^。；，]{{0,20}})[^。；]{{0,24}}(?:{terms})",
        rf"(?:{terms})[^。；]{{0,12}}(?:了|完成|完毕)",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def classify_post(post: HuijinPost, *, observed_at: str | None = None) -> OperationEvent | None:
    text = f"{post.title}\n{post.body}"
    event_type: EventType | None = None
    reason = ""
    # Classify only completed actions. Forward-looking wording such as
    # “拟增持/增持计划/未来将增持” is evidence of intent, not a transaction.
    # Transfers take precedence because their explanatory text may also say
    # that the transferee's holding increases.
    if _completed_action(text, r"协议转让|无偿划转|股份划转|受让"):
        event_type = EventType.CONFIRMED_TRANSFER
        reason = "中央汇金官方网站明确披露已完成股权转让、划转或受让。"
    elif _completed_action(text, r"增持|买入|认购"):
        event_type = EventType.CONFIRMED_BUY
        reason = "中央汇金官方网站明确披露已完成增持、买入或认购。"
    elif _completed_action(text, r"减持|出售"):
        event_type = EventType.CONFIRMED_SELL
        reason = "中央汇金官方网站明确披露已完成减持或出售。"
    if event_type is None:
        return None

    instrument_name = "ETF" if re.search(r"ETF|交易型开放式指数基金", text, re.I) else "未披露具体标的"
    event_key = hashlib.sha256(
        f"{SOURCE}|{post.external_id}|{event_type.value}|{instrument_name}".encode("utf-8")
    ).hexdigest()
    return OperationEvent(
        event_key=event_key,
        event_type=event_type,
        entity_key="central_huijin_investment",
        holder_name="中央汇金投资有限责任公司",
        attribution=Attribution.DIRECT,
        instrument_code="",
        instrument_name=instrument_name,
        market="CN",
        scope="official_statement",
        event_date=post.published_at,
        published_at=post.published_at,
        previous_shares=None,
        current_shares=None,
        previous_ratio=None,
        current_ratio=None,
        reason=reason + (" 公告未给出具体规模或成交明细。" if instrument_name == "ETF" else ""),
        confidence=Confidence.CONFIRMED_OFFICIAL,
        source=SOURCE,
        evidence_url=post.url,
        created_at=observed_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
