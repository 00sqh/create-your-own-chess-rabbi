from pathlib import Path

from personal_maia.config import FilterConfig, init_project
from personal_maia.data.ingest import ingest_local_pgns


def test_ingest_multiple_pgns(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    one = tmp_path / "one.pgn"
    two = tmp_path / "two.pgn"
    one.write_text(
        """
[Event "One"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
""".strip(),
        encoding="utf-8",
    )
    two.write_text(
        """
[Event "Two"]
[White "Carol"]
[Black "Alice"]
[Result "0-1"]

1. d4 d5 2. c4 e6 0-1
""".strip(),
        encoding="utf-8",
    )

    result = ingest_local_pgns([one, two], project, FilterConfig(target_player="Alice", min_ply=4))

    assert len(result.raw_paths) == 2
    assert result.report.total_games == 2
    assert result.report.kept_games == 2
    cleaned = result.cleaned_path.read_text(encoding="utf-8")
    assert "[Event \"One\"]" in cleaned
    assert "[Event \"Two\"]" in cleaned

