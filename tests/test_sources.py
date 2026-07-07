from pathlib import Path

from personal_maia.sources import parse_source


def test_parse_lichess_profile_url():
    ref = parse_source("https://lichess.org/@/SomeUser/perf/blitz")
    assert ref.kind == "lichess"
    assert ref.username == "SomeUser"


def test_parse_chesscom_profile_url():
    ref = parse_source("https://www.chess.com/member/SomeUser")
    assert ref.kind == "chesscom"
    assert ref.username == "SomeUser"


def test_parse_local_pgn(tmp_path: Path):
    pgn = tmp_path / "games.pgn"
    pgn.write_text("", encoding="utf-8")
    ref = parse_source(str(pgn))
    assert ref.kind == "pgn"

