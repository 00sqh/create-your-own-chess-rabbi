from pathlib import Path

import pytest

from rabbi.config import init_project
from rabbi.maia.converter import ConversionConfig, MaiaDataConverter
from rabbi.maia.trainer import MaiaIndividualTrainer, TrainerConfig, _to_simple_yaml


def make_fake_maia_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "maia-individual"
    (repo / "1-data_generation").mkdir(parents=True)
    (repo / "2-training").mkdir(parents=True)
    (repo / "1-data_generation" / "9-pgn_to_training_data.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (repo / "2-training" / "train_transfer.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return repo


def test_converter_builds_upstream_command(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    maia_repo = make_fake_maia_repo(tmp_path)
    pgn = project.cleaned_dir / "target-games.pgn"
    pgn.write_text("[Event \"x\"]\n\n1. e4 *\n", encoding="utf-8")
    converter = MaiaDataConverter(
        ConversionConfig(maia_repo=maia_repo, project_dir=project.root, player_name="Alice")
    )

    command = converter.build_command()

    assert command == [
        "bash",
        str((maia_repo / "1-data_generation" / "9-pgn_to_training_data.sh").resolve()),
        str((project.cleaned_dir / "target-games.pgn").resolve()),
        str((project.training_dir / "alice").resolve()),
        "Alice",
    ]


def test_converter_can_override_python_path(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    maia_repo = make_fake_maia_repo(tmp_path)
    pgn = project.cleaned_dir / "target-games.pgn"
    pgn.write_text("[Event \"x\"]\n\n1. e4 *\n", encoding="utf-8")
    python = tmp_path / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    converter = MaiaDataConverter(
        ConversionConfig(
            maia_repo=maia_repo,
            project_dir=project.root,
            player_name="Alice",
            python=python,
        )
    )

    command = converter.build_command()

    assert command[0] == "env"
    assert str(python.parent) in command[1]


def test_converter_requires_exact_pgn_header_player_name(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    maia_repo = make_fake_maia_repo(tmp_path)
    pgn = project.cleaned_dir / "target-games.pgn"
    pgn.write_text(_sample_pgn(white_games=10, black_games=10, player="Alice"), encoding="utf-8")
    converter = MaiaDataConverter(
        ConversionConfig(maia_repo=maia_repo, project_dir=project.root, player_name="alice")
    )

    with pytest.raises(ValueError, match="exact PGN header player name"):
        converter.validate()


def test_converter_requires_enough_games_per_color_for_upstream_split(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    maia_repo = make_fake_maia_repo(tmp_path)
    pgn = project.cleaned_dir / "target-games.pgn"
    pgn.write_text(_sample_pgn(white_games=10, black_games=9, player="Alice"), encoding="utf-8")
    converter = MaiaDataConverter(
        ConversionConfig(maia_repo=maia_repo, project_dir=project.root, player_name="Alice")
    )

    with pytest.raises(ValueError, match="at least 10 exact games as White"):
        converter.validate()


def test_converter_accepts_minimum_games_per_color(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    maia_repo = make_fake_maia_repo(tmp_path)
    pgn = project.cleaned_dir / "target-games.pgn"
    pgn.write_text(_sample_pgn(white_games=10, black_games=10, player="Alice"), encoding="utf-8")
    converter = MaiaDataConverter(
        ConversionConfig(maia_repo=maia_repo, project_dir=project.root, player_name="Alice")
    )

    converter.validate()


def test_trainer_uses_sanitized_dataset_and_copy_dir(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    maia_repo = make_fake_maia_repo(tmp_path)
    base_model = tmp_path / "maia-1900"
    base_model.mkdir()
    (project.training_dir / "alice").mkdir(parents=True)
    trainer = MaiaIndividualTrainer(
        TrainerConfig(
            maia_repo=maia_repo,
            project_dir=project.root,
            player_name="Alice",
            base_model=base_model,
            python=tmp_path / "python",
            output_dir=project.root / "models",
            total_steps=10,
        )
    )

    config = trainer.to_config_dict()
    command = trainer.build_command(project.config_dir / "generated.yaml")

    assert config["dataset"]["name"] == "alice"
    assert config["dataset"]["path"] == str(project.training_dir)
    assert config["model"]["path"] == str(base_model)
    assert config["training"]["lr_values"] == [0.01, 0.001, 0.0001, 0.00001]
    assert config["training"]["lr_boundaries"] == [35_000, 80_000, 110_000]
    assert config["training"]["test_steps"] == 2_000
    assert command[0] == str((tmp_path / "python").absolute())
    assert command[3] == "alice"
    assert command[-2:] == ["--copy_dir", str(project.root / "models")]


def test_trainer_uses_model_name_relative_to_maia_models(tmp_path: Path):
    project = init_project("Alice Style", tmp_path)
    maia_repo = make_fake_maia_repo(tmp_path)
    base_model = maia_repo / "models" / "maia-1900"
    base_model.mkdir(parents=True)
    trainer = MaiaIndividualTrainer(
        TrainerConfig(
            maia_repo=maia_repo,
            project_dir=project.root,
            player_name="Alice",
            base_model=base_model,
        )
    )

    config = trainer.to_config_dict()

    assert config["model"]["path"] == "maia-1900"


def test_simple_yaml_serializes_empty_dict_inline():
    yaml = _to_simple_yaml({"extra": {}, "values": [1, 2]})

    assert "extra: {}" in yaml
    assert "values:\n  - 1\n  - 2" in yaml


def _sample_pgn(*, white_games: int, black_games: int, player: str) -> str:
    games = []
    for index in range(white_games):
        games.append(
            f"""
[Event "White {index}"]
[White "{player}"]
[Black "Opponent{index}"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
""".strip()
        )
    for index in range(black_games):
        games.append(
            f"""
[Event "Black {index}"]
[White "Opponent{index}"]
[Black "{player}"]
[Result "0-1"]

1. d4 d5 2. c4 e6 3. Nc3 Nf6 0-1
""".strip()
        )
    return "\n\n".join(games) + "\n"
