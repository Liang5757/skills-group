from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


class SourceFetchError(RuntimeError):
    pass


def _safe_url_for_error(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path
    hook_marker = "/hook/"
    if hook_marker in path:
        prefix, _, _ = path.partition(hook_marker)
        path = f"{prefix}{hook_marker}[redacted]"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status: int
    body: bytes
    headers: Mapping[str, str]

    def text(self) -> str:
        content_type = self.headers.get("Content-Type", "")
        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=", 1)[1].split(";", 1)[0].split(",", 1)[0].strip()
        try:
            return self.body.decode(charset)
        except (LookupError, UnicodeDecodeError):
            return self.body.decode("utf-8", errors="replace")

    def json(self) -> dict:
        return json.loads(self.body)


class HttpClient:
    def __init__(self, *, timeout: float = 20.0, retries: int = 2, backoff: float = 0.5):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.default_headers = {
            "User-Agent": "HuijinTracker/0.1 (+public-disclosure-monitor)",
            "Accept": "application/json,text/html,application/xhtml+xml,*/*",
        }

    def get(self, url: str, *, params: Mapping[str, object] | None = None) -> HttpResponse:
        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"
        return self._request(Request(url, headers=self.default_headers))

    def post_form(self, url: str, data: Mapping[str, object]) -> HttpResponse:
        headers = dict(self.default_headers)
        headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        body = urlencode(data).encode("utf-8")
        return self._request(Request(url, data=body, headers=headers, method="POST"))

    def post_json(self, url: str, payload: Mapping[str, object]) -> HttpResponse:
        headers = dict(self.default_headers)
        headers["Content-Type"] = "application/json; charset=UTF-8"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return self._request(Request(url, data=body, headers=headers, method="POST"))

    def _request(self, request: Request) -> HttpResponse:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return HttpResponse(
                        url=response.geturl(),
                        status=response.status,
                        body=response.read(),
                        headers=dict(response.headers.items()),
                    )
            except (HTTPError, URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt < self.retries:
                    time.sleep(self.backoff * (2**attempt))
        safe_url = _safe_url_for_error(request.full_url)
        error_text = str(last_error).replace(request.full_url, safe_url)
        raise SourceFetchError(
            f"request failed after {self.retries + 1} attempts: {safe_url}: {error_text}"
        )
