from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os

from personal_maia.config import ProjectPaths, sanitize_name, write_json
from personal_maia.data.pgn import normalize_player, parse_pgn
from personal_maia.system.process import LoggedProcessResult, run_logged


MIN_GAMES_PER_COLOR_FOR_MAIA_SPLIT = 10


@dataclass(slots=True)
class ConversionInputSummary:
    total_games: int
    exact_white_games: int
    exact_black_games: int
    normalized_white_games: int
    normalized_black_games: int
    normalized_header_names: list[str]


@dataclass(slots=True)
class ConversionConfig:
    maia_repo: Path
    project_dir: Path
    player_name: str
    input_pgn: Path | None = None
    output_dir: Path | None = None
    python: Path | None = None

    @property
    def player_slug(self) -> str:
        return sanitize_name(self.player_name)

    @property
    def resolved_input_pgn(self) -> Path:
        if self.input_pgn is not None:
            return self.input_pgn
        return ProjectPaths(self.project_dir).cleaned_dir / "target-games.pgn"

    @property
    def resolved_output_dir(self) -> Path:
        if self.output_dir is not None:
            return self.output_dir
        return ProjectPaths(self.project_dir).training_dir / self.player_slug


class MaiaDataConverter:
    """Adapter for Maia Individual's PGN-to-training-data script."""

    def __init__(self, config: ConversionConfig) -> None:
        self.config = config

    @property
    def script(self) -> Path:
        return self.config.maia_repo / "1-data_generation" / "9-pgn_to_training_data.sh"

    def validate(self) -> None:
        if not self.config.maia_repo.exists():
            raise FileNotFoundError(f"Maia Individual repo not found: {self.config.maia_repo}")
        if not self.script.exists():
            raise FileNotFoundError(f"Maia Individual conversion script not found: {self.script}")
        if not self.config.resolved_input_pgn.exists():
            raise FileNotFoundError(f"Input PGN not found: {self.config.resolved_input_pgn}")
        summary = self.inspect_input()
        if summary.total_games == 0:
            raise ValueError(f"Input PGN has no parseable games: {self.config.resolved_input_pgn}")
        exact_total = summary.exact_white_games + summary.exact_black_games
        if exact_total == 0:
            normalized_total = summary.normalized_white_games + summary.normalized_black_games
            if normalized_total:
                names = ", ".join(repr(name) for name in summary.normalized_header_names)
                raise ValueError(
                    "Maia Individual requires the exact PGN header player name. "
                    f"Found {normalized_total} case-insensitive match(es) for "
                    f"{self.config.player_name!r}, but no exact match. "
                    f"Use the header spelling: {names}."
                )
            raise ValueError(
                f"Player {self.config.player_name!r} was not found in PGN headers: "
                f"{self.config.resolved_input_pgn}"
            )
        if (
            summary.exact_white_games < MIN_GAMES_PER_COLOR_FOR_MAIA_SPLIT
            or summary.exact_black_games < MIN_GAMES_PER_COLOR_FOR_MAIA_SPLIT
        ):
            raise ValueError(
                "Maia Individual's converter uses a fixed 90/10 split for each color. "
                f"It needs at least {MIN_GAMES_PER_COLOR_FOR_MAIA_SPLIT} exact games as White "
                f"and {MIN_GAMES_PER_COLOR_FOR_MAIA_SPLIT} as Black so validation chunks are not empty. "
                f"Found {self.config.player_name!r}: "
                f"{summary.exact_white_games} as White, {summary.exact_black_games} as Black."
            )

    def inspect_input(self) -> ConversionInputSummary:
        text = self.config.resolved_input_pgn.read_text(encoding="utf-8", errors="replace")
        games = parse_pgn(text)
        exact_white_games = 0
        exact_black_games = 0
        normalized_white_games = 0
        normalized_black_games = 0
        normalized_header_names: set[str] = set()
        normalized_target = normalize_player(self.config.player_name)
        for game in games:
            if game.white == self.config.player_name:
                exact_white_games += 1
            if game.black == self.config.player_name:
                exact_black_games += 1
            if normalize_player(game.white) == normalized_target:
                normalized_white_games += 1
                normalized_header_names.add(game.white)
            if normalize_player(game.black) == normalized_target:
                normalized_black_games += 1
                normalized_header_names.add(game.black)
        return ConversionInputSummary(
            total_games=len(games),
            exact_white_games=exact_white_games,
            exact_black_games=exact_black_games,
            normalized_white_games=normalized_white_games,
            normalized_black_games=normalized_black_games,
            normalized_header_names=sorted(normalized_header_names),
        )

    def write_config(self) -> Path:
        path = ProjectPaths(self.config.project_dir).config_dir / "maia-conversion.json"
        data = asdict(self.config)
        for key in ["maia_repo", "project_dir", "input_pgn", "output_dir", "python"]:
            value = data.get(key)
            data[key] = str(value) if value is not None else None
        data["resolved_input_pgn"] = str(self.config.resolved_input_pgn)
        data["resolved_output_dir"] = str(self.config.resolved_output_dir)
        data["player_slug"] = self.config.player_slug
        write_json(path, data)
        return path

    def build_command(self) -> list[str]:
        command = [
            "bash",
            str(self.script.resolve()),
            str(self.config.resolved_input_pgn.resolve()),
            str(self.config.resolved_output_dir.resolve()),
            self.config.player_name,
        ]
        if self.config.python is None:
            return command
        return [
            "env",
            f"PATH={self.config.python.absolute().parent}:{os.environ.get('PATH', '')}",
            *command,
        ]

    def run(
        self,
        *,
        dry_run: bool = False,
        log_path: Path | None = None,
    ) -> LoggedProcessResult | list[str]:
        self.validate()
        self.config.resolved_output_dir.mkdir(parents=True, exist_ok=True)
        self.write_config()
        command = self.build_command()
        if dry_run:
            return command
        log = log_path or (ProjectPaths(self.config.project_dir).logs_dir / "convert-data.log")
        return run_logged(command, cwd=self.script.parent, log_path=log, env=_maia_env(self.config.maia_repo))


def _maia_env(maia_repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    repo = str(maia_repo.resolve())
    env["PYTHONPATH"] = repo if not existing else f"{repo}{os.pathsep}{existing}"
    return env
