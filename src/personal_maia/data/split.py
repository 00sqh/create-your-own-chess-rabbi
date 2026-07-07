from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from personal_maia.config import ProjectPaths, sanitize_name, write_json

from .pgn import games_to_pgn, parse_pgn


@dataclass(slots=True)
class TrainingSplitReport:
    player_slug: str
    total_games: int
    train_games: int
    validate_games: int
    train_path: Path
    validate_path: Path
    report_path: Path


def prepare_training_split(
    project: ProjectPaths,
    player_name: str,
    *,
    validation_ratio: float = 0.1,
) -> TrainingSplitReport:
    if not 0 < validation_ratio < 0.5:
        raise ValueError("validation_ratio must be between 0 and 0.5.")

    cleaned_path = project.cleaned_dir / "target-games.pgn"
    if not cleaned_path.exists():
        raise FileNotFoundError(f"Cleaned PGN not found: {cleaned_path}")

    games = parse_pgn(cleaned_path.read_text(encoding="utf-8", errors="replace"))
    player_slug = sanitize_name(player_name)
    output_dir = project.training_dir / player_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    validate_every = max(2, round(1 / validation_ratio))
    train = []
    validate = []
    for index, game in enumerate(games):
        if index % validate_every == 0:
            validate.append(game)
        else:
            train.append(game)

    if games and not train:
        train, validate = validate, []

    train_path = output_dir / "train.pgn"
    validate_path = output_dir / "validate.pgn"
    report_path = output_dir / "split-report.json"
    train_path.write_text(games_to_pgn(train), encoding="utf-8")
    validate_path.write_text(games_to_pgn(validate), encoding="utf-8")

    report = TrainingSplitReport(
        player_slug=player_slug,
        total_games=len(games),
        train_games=len(train),
        validate_games=len(validate),
        train_path=train_path,
        validate_path=validate_path,
        report_path=report_path,
    )
    write_json(report_path, _report_dict(report))
    return report


def _report_dict(report: TrainingSplitReport) -> dict[str, object]:
    data = asdict(report)
    for key in ["train_path", "validate_path", "report_path"]:
        data[key] = str(data[key])
    return data

