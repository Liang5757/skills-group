from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from ..http import HttpClient
from ..models import Attribution, Confidence, EventType, OperationEvent


SOURCE = "hkex_di"
BASE_URL = "https://di.hkex.com.hk/di/"
SEARCH_URL = urljoin(BASE_URL, "NSSrchPersonList.aspx")
PERSON_NAME = "Central Huijin Investment Ltd."


@dataclass(frozen=True)
class Cell:
    text: str
    links: tuple[str, ...]


@dataclass(frozen=True)
class HkexDisclosure:
    serial: str
    event_date: str
    filed_at: str | None
    corporation: str
    corporation_id: str
    shares_involved_text: str
    reason_codes: str
    price_text: str
    shares_after_text: str
    ratio_after_text: str
    form_url: str
    list_url: str


PageObserver = Callable[[str, str, str, bytes], None]


class _GridParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.table_depth = 0
        self.row: list[Cell] | None = None
        self.cell_text: list[str] | None = None
        self.cell_links: list[str] = []
        self.rows: list[list[Cell]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "table":
            if self.table_depth:
                self.table_depth += 1
            elif values.get("id") == "grdPaging":
                self.table_depth = 1
            return
        if not self.table_depth:
            return
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell_text = []
            self.cell_links = []
        elif tag == "a" and self.cell_text is not None and values.get("href"):
            self.cell_links.append(str(values["href"]))
        elif tag == "br" and self.cell_text is not None:
            self.cell_text.append(" | ")

    def handle_data(self, data: str) -> None:
        if self.cell_text is not None:
            self.cell_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.table_depth:
            return
        if tag in {"td", "th"} and self.cell_text is not None and self.row is not None:
            text = " ".join("".join(self.cell_text).split()).strip(" |")
            self.row.append(Cell(text, tuple(self.cell_links)))
            self.cell_text = None
            self.cell_links = []
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.table_depth -= 1


def parse_grid(html: str) -> list[list[Cell]]:
    parser = _GridParser()
    parser.feed(html)
    return parser.rows


def parse_company_links(html: str) -> list[tuple[str, str, str]]:
    companies: list[tuple[str, str, str]] = []
    for row in parse_grid(html):
        if len(row) < 2:
            continue
        href = next((link for link in row[0].links if "NSNoticePersonList.aspx" in link), None)
        if not href:
            continue
        query = parse_qs(urlparse(href).query)
        corporation_id = (query.get("scpid2") or [""])[0]
        companies.append((urljoin(BASE_URL, href), row[1].text, corporation_id))
    return companies


def _iso_from_hk_date(value: str) -> str:
    return datetime.strptime(value.strip(), "%d/%m/%Y").date().isoformat()


def _filed_at(serial: str) -> str | None:
    match = re.match(r"CS(\d{4})(\d{2})(\d{2})", serial)
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else None


def parse_notice_list(
    html: str,
    *,
    list_url: str,
    corporation_id: str,
) -> list[HkexDisclosure]:
    disclosures: list[HkexDisclosure] = []
    for row in parse_grid(html):
        if len(row) < 8:
            continue
        serial_match = re.search(r"CS\d{8}E\d+", row[0].text)
        href = next((link for link in row[0].links if "NSForm2.aspx" in link), None)
        if not serial_match or not href:
            continue
        try:
            event_date = _iso_from_hk_date(row[1].text)
        except ValueError:
            continue
        serial = serial_match.group(0)
        disclosures.append(
            HkexDisclosure(
                serial=serial,
                event_date=event_date,
                filed_at=_filed_at(serial),
                corporation=row[2].text,
                corporation_id=corporation_id,
                shares_involved_text=row[3].text,
                reason_codes=row[4].text,
                price_text=row[5].text,
                shares_after_text=row[6].text,
                ratio_after_text=row[7].text,
                form_url=urljoin(BASE_URL, href),
                list_url=list_url,
            )
        )
    return disclosures


def _long_value(text: str, *, ratio: bool = False) -> int | float | None:
    pattern = r"([\d,.]+)\s*\(L\)"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(1).replace(",", "")
    try:
        return float(value) if ratio else int(value)
    except ValueError:
        return None


def to_event(item: HkexDisclosure, *, observed_at: str | None = None) -> OperationEvent:
    reason = (
        "港交所权益披露表显示中央汇金申报的法定或推定权益发生变化；"
        "该申报可能源于受控法团、淡仓或其他披露原因，不能直接等同于中央汇金买卖。"
        f" 原因代码: {item.reason_codes or '—'}；涉及股份: {item.shares_involved_text or '—'}；"
        f"变动后权益: {item.shares_after_text or '—'}。"
    )
    return OperationEvent(
        event_key=hashlib.sha256(f"{SOURCE}|{item.serial}".encode("utf-8")).hexdigest(),
        event_type=EventType.DEEMED_INTEREST_CHANGE,
        entity_key="central_huijin_investment",
        holder_name="中央汇金投资有限责任公司",
        attribution=Attribution.DIRECT,
        instrument_code=f"HKEX:{item.corporation_id}",
        instrument_name=item.corporation,
        market="HK",
        scope="hkex_disclosure_of_interests",
        event_date=item.event_date,
        published_at=item.filed_at,
        previous_shares=None,
        current_shares=_long_value(item.shares_after_text),
        previous_ratio=None,
        current_ratio=_long_value(item.ratio_after_text, ratio=True),
        reason=reason,
        confidence=Confidence.CONFIRMED_OFFICIAL,
        source=SOURCE,
        evidence_url=item.form_url,
        created_at=observed_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


class HkexCollector:
    def __init__(self, client: HttpClient | None = None, *, sleep_seconds: float = 0.2):
        self.client = client or HttpClient()
        self.sleep_seconds = sleep_seconds

    def scan(
        self,
        *,
        since: str,
        until: str,
        on_page: PageObserver | None = None,
    ) -> list[HkexDisclosure]:
        start = date.fromisoformat(since)
        end = date.fromisoformat(until)
        if start > end:
            raise ValueError("since must not be later than until")
        if (end - start).days > 366:
            raise ValueError("HKEX DI search interval must not exceed 366 days")
        params = {
            "lang": "EN",
            "pn": PERSON_NAME,
            "sa1": "pl",
            "scsd": start.strftime("%d/%m/%Y"),
            "sced": end.strftime("%d/%m/%Y"),
            "src": "Main",
        }
        search_response = self.client.get(SEARCH_URL, params=params)
        search_url = f"{SEARCH_URL}?{urlencode(params)}"
        if on_page:
            on_page("search", "Central Huijin DI corporation search", search_url, search_response.body)

        results: dict[str, HkexDisclosure] = {}
        for index, (list_url, corporation, corporation_id) in enumerate(
            parse_company_links(search_response.text())
        ):
            if index and self.sleep_seconds:
                time.sleep(self.sleep_seconds)
            response = self.client.get(list_url)
            if on_page:
                on_page(
                    f"corporation-{corporation_id or index}",
                    f"Central Huijin DI notices - {corporation}",
                    list_url,
                    response.body,
                )
            for item in parse_notice_list(
                response.text(),
                list_url=list_url,
                corporation_id=corporation_id,
            ):
                results[item.serial] = item
        return list(results.values())
