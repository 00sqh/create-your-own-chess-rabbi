from pathlib import Path

from personal_maia.config import FilterConfig, init_project
from personal_maia.data.ingest import ingest_local_pgn
from personal_maia.status import collect_status


def test_collect_status(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    pgn = tmp_path / "games.pgn"
    pgn.write_text(
        """
[Event "One"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
""".strip(),
        encoding="utf-8",
    )
    ingest_local_pgn(pgn, project, FilterConfig(target_player="Alice", min_ply=4))
    (project.root / "models").mkdir()
    weights = project.root / "models" / "alice.pb.gz"
    weights.write_text("fake", encoding="utf-8")

    status = collect_status(project.root)

    assert status.has_project_config
    assert status.raw_pgn_count == 1
    assert status.cleaned_pgn is not None
    assert status.ingest_report is not None
    assert status.latest_weights == weights

