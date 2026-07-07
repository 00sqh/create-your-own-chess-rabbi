from pathlib import Path

from personal_maia.config import FilterConfig, init_project
from personal_maia.data.ingest import ingest_local_pgn
from personal_maia.data.split import prepare_training_split


def test_prepare_training_split(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    pgn = tmp_path / "games.pgn"
    pgn.write_text(
        """
[Event "One"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0

[Event "Two"]
[White "Alice"]
[Black "Carol"]
[Result "1-0"]

1. d4 d5 2. c4 e6 3. Nc3 Nf6 1-0

[Event "Three"]
[White "Dan"]
[Black "Alice"]
[Result "0-1"]

1. c4 e5 2. Nc3 Nf6 3. g3 d5 0-1
""".strip(),
        encoding="utf-8",
    )
    ingest_local_pgn(pgn, project, FilterConfig(target_player="Alice", min_ply=4))
    report = prepare_training_split(project, "Alice", validation_ratio=0.34)
    assert report.total_games == 3
    assert report.train_games == 2
    assert report.validate_games == 1
    assert report.train_path.exists()
    assert report.validate_path.exists()

