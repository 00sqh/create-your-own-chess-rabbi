from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class SourceRef:
    kind: str
    value: str
    username: str | None = None


def parse_source(value: str) -> SourceRef:
    raw = value.strip()
    if not raw:
        raise ValueError("Source cannot be empty.")

    path = Path(raw).expanduser()
    if path.exists():
        if path.is_dir():
            return SourceRef(kind="pgn_dir", value=str(path))
        if path.suffix.lower() == ".pgn":
            return SourceRef(kind="pgn", value=str(path))

    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if host.endswith("lichess.org"):
        username = _lichess_username(path_parts)
        if username:
            return SourceRef(kind="lichess", value=raw, username=username)
        return SourceRef(kind="lichess_url", value=raw)

    if host.endswith("chess.com"):
        username = _chesscom_username(path_parts)
        if username:
            return SourceRef(kind="chesscom", value=raw, username=username)
        return SourceRef(kind="chesscom_url", value=raw)

    if _looks_like_username(raw):
        return SourceRef(kind="lichess", value=raw, username=raw)

    return SourceRef(kind="unknown", value=raw)


def _lichess_username(path_parts: list[str]) -> str | None:
    if len(path_parts) >= 2 and path_parts[0] == "@":
        return path_parts[1]
    if path_parts and path_parts[0].startswith("@"):
        return path_parts[0][1:]
    return None


def _chesscom_username(path_parts: list[str]) -> str | None:
    if len(path_parts) >= 2 and path_parts[0].lower() in {"member", "players"}:
        return path_parts[1]
    return None


def _looks_like_username(value: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    return all(ch in allowed for ch in value) and any(ch.isalnum() for ch in value)

