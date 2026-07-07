from pathlib import Path
import json

from personal_maia.cli import main
from personal_maia.config import init_project


def make_fake_maia_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "maia-individual"
    (repo / "1-data_generation").mkdir(parents=True)
    (repo / "2-training").mkdir(parents=True)
    (repo / "1-data_generation" / "9-pgn_to_training_data.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (repo / "2-training" / "train_transfer.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return repo


def test_build_local_pgn_dry_run(tmp_path: Path):
    maia_repo = make_fake_maia_repo(tmp_path)
    base_model = tmp_path / "maia-1900"
    base_model.mkdir()
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

    code = main(
        [
            "build",
            "--name",
            "Alice Style",
            "--workspace",
            str(tmp_path / "runs"),
            "--player",
            "Alice",
            "--source",
            str(pgn),
            "--maia-repo",
            str(maia_repo),
            "--base-model",
            str(base_model),
            "--min-ply",
            "4",
        ]
    )

    project = tmp_path / "runs" / "alice-style"
    assert code == 0
    assert (project / "data" / "cleaned" / "target-games.pgn").exists()
    assert (project / "config" / "maia-conversion.json").exists()
    assert (project / "config" / "maia-individual.generated.yaml").exists()
    assert (project / "config" / "build-summary.json").exists()


def test_prepare_train_serializes_python_path(tmp_path: Path):
    maia_repo = make_fake_maia_repo(tmp_path)
    base_model = tmp_path / "maia-1900"
    base_model.mkdir()
    project = init_project("Alice Style", tmp_path / "runs")
    (project.training_dir / "alice").mkdir(parents=True)
    python = tmp_path / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")

    code = main(
        [
            "prepare-train",
            "--project",
            str(project.root),
            "--maia-repo",
            str(maia_repo),
            "--base-model",
            str(base_model),
            "--python",
            str(python),
            "--player",
            "Alice",
            "--skip-pgn-split",
        ]
    )

    data = json.loads((project.config_dir / "training.json").read_text(encoding="utf-8"))
    assert code == 0
    assert data["python"] == str(python)
