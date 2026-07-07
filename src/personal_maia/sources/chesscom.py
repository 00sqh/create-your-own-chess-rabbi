from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen
import json

from .http import USER_AGENT, download_text


@dataclass(frozen=True, slots=True)
class ChessComArchive:
    year: str
    month: str
    url: str


def build_chesscom_archives_url(username: str) -> str:
    return f"https://api.chess.com/pub/player/{username}/games/archives"


def build_chesscom_month_pgn_url(username: str, year: str, month: str) -> str:
    return f"https://api.chess.com/pub/player/{username}/games/{year}/{month}/pgn"


def list_chesscom_archives(username: str) -> list[ChessComArchive]:
    request = Request(build_chesscom_archives_url(username), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    archives: list[ChessComArchive] = []
    for url in data.get("archives", []):
        parts = str(url).rstrip("/").split("/")
        if len(parts) >= 2:
            archives.append(ChessComArchive(year=parts[-2], month=parts[-1], url=str(url)))
    return archives


def download_chesscom_pgn(username: str, output: Path, *, max_archives: int | None = None) -> Path:
    archives = list_chesscom_archives(username)
    if max_archives is not None:
        archives = archives[-max_archives:]
    pgn_parts: list[str] = []
    for archive in archives:
        month_output = output.parent / f"chesscom-{username}-{archive.year}-{archive.month}.pgn"
        download_text(build_chesscom_month_pgn_url(username, archive.year, archive.month), month_output)
        pgn_parts.append(month_output.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(part.strip() for part in pgn_parts if part.strip()) + "\n", encoding="utf-8")
    return output

