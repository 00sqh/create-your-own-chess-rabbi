from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from .http import download_text


@dataclass(frozen=True, slots=True)
class LichessDownloadOptions:
    max_games: int | None = None
    rated: bool | None = None
    perf_type: str | None = None
    since_ms: int | None = None
    until_ms: int | None = None


def build_lichess_export_url(username: str, options: LichessDownloadOptions | None = None) -> str:
    opts = options or LichessDownloadOptions()
    query: dict[str, str | int | bool] = {
        "pgnInJson": "false",
        "clocks": "true",
        "evals": "false",
        "opening": "true",
    }
    if opts.max_games is not None:
        query["max"] = opts.max_games
    if opts.rated is not None:
        query["rated"] = "true" if opts.rated else "false"
    if opts.perf_type:
        query["perfType"] = opts.perf_type
    if opts.since_ms is not None:
        query["since"] = opts.since_ms
    if opts.until_ms is not None:
        query["until"] = opts.until_ms
    return f"https://lichess.org/api/games/user/{username}?{urlencode(query)}"


def download_lichess_pgn(
    username: str,
    output: Path,
    options: LichessDownloadOptions | None = None,
) -> Path:
    return download_text(build_lichess_export_url(username, options), output)

