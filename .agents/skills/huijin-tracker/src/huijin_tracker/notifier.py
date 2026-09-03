from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections import Counter
from typing import Iterable

from .http import HttpClient
from .models import OperationEvent


def _format_value(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _format_percent(value: float | None) -> str:
    return "—" if value is None else f"{_format_value(value)}%"


def render_event(event: OperationEvent) -> str:
    lines = [
        f"[{event.event_type.value}] {event.holder_name} · {event.instrument_name or event.instrument_code}",
        f"归因: {event.attribution.value} | 置信度: {event.confidence.value}",
        f"事件/报告期: {_format_value(event.event_date)} | 披露日: {_format_value(event.published_at)}",
    ]
    if event.previous_shares is not None or event.current_shares is not None:
        lines.append(
            f"持股数: {_format_value(event.previous_shares)} → {_format_value(event.current_shares)}"
        )
    if event.previous_ratio is not None or event.current_ratio is not None:
        lines.append(
            f"比例: {_format_percent(event.previous_ratio)} → {_format_percent(event.current_ratio)}"
        )
    lines.extend([f"说明: {event.reason}", f"证据: {event.evidence_url}"])
    return "\n".join(lines)


def render_events(events: Iterable[OperationEvent]) -> str:
    return "\n\n".join(render_event(event) for event in events)


def summarize_events(events: Iterable[OperationEvent]) -> str:
    items = list(events)
    by_type = Counter(item.event_type.value for item in items)
    by_attribution = Counter(item.attribution.value for item in items)
    types = ", ".join(f"{key}={value}" for key, value in sorted(by_type.items())) or "无"
    attributions = ", ".join(
        f"{key}={value}" for key, value in sorted(by_attribution.items())
    ) or "无"
    return f"事件类型: {types}\n主体归因: {attributions}"


def _feishu_sign(timestamp: int, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(string_to_sign, digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


class FeishuNotifier:
    def __init__(
        self,
        webhook_url: str | None = None,
        *,
        secret: str | None = None,
        client: HttpClient | None = None,
    ):
        self.webhook_url = webhook_url or os.getenv("HUJIN_FEISHU_WEBHOOK")
        self.secret = secret or os.getenv("HUJIN_FEISHU_SECRET")
        self.client = client or HttpClient()

    @property
    def configured(self) -> bool:
        return bool(self.webhook_url)

    def send(self, events: list[OperationEvent]) -> bool:
        if not events or not self.webhook_url:
            return False
        visible = events[:20]
        omitted = len(events) - len(visible)
        content = summarize_events(events) + "\n\n" + render_events(visible)
        if omitted:
            content += f"\n\n另有 {omitted} 条已入账，未在本消息展开。"
        payload: dict[str, object] = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "template": "red" if any(event.event_type.value.startswith("CONFIRMED") for event in events) else "blue",
                    "title": {"tag": "plain_text", "content": f"中央汇金公开信息更新（{len(events)}）"},
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": content[:28000]}}
                ],
            },
        }
        if self.secret:
            timestamp = int(time.time())
            payload["timestamp"] = str(timestamp)
            payload["sign"] = _feishu_sign(timestamp, self.secret)
        response = self.client.post_json(self.webhook_url, payload).json()
        code = response.get("code", response.get("StatusCode", 0))
        if code not in (0, "0", None):
            raise RuntimeError(f"Feishu webhook rejected message: {json.dumps(response, ensure_ascii=False)}")
        return True
