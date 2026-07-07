from personal_maia.sources import (
    build_chesscom_archives_url,
    build_chesscom_month_pgn_url,
    build_lichess_export_url,
)
from personal_maia.sources.lichess import LichessDownloadOptions


def test_build_lichess_export_url():
    url = build_lichess_export_url(
        "Alice",
        LichessDownloadOptions(max_games=25, rated=True, perf_type="blitz"),
    )
    assert url.startswith("https://lichess.org/api/games/user/Alice?")
    assert "max=25" in url
    assert "rated=true" in url
    assert "perfType=blitz" in url


def test_build_chesscom_urls():
    assert build_chesscom_archives_url("Alice") == "https://api.chess.com/pub/player/Alice/games/archives"
    assert (
        build_chesscom_month_pgn_url("Alice", "2026", "07")
        == "https://api.chess.com/pub/player/Alice/games/2026/07/pgn"
    )

