from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen


USER_AGENT = "personal-maia/0.1"


def download_text(url: str, output: Path, *, headers: dict[str, str] | None = None) -> Path:
    request_headers = {"User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8", errors="replace")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    return output

