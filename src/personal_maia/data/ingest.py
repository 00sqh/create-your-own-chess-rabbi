from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from personal_maia.config import FilterConfig, ProjectPaths, write_json

from .pgn import FilterReport, filter_games, games_to_pgn, parse_pgn


@dataclass(slots=True)
class IngestResult:
    raw_paths: list[Path]
    cleaned_path: Path
    report_path: Path
    report: FilterReport

    @property
    def raw_path(self) -> Path:
        return self.raw_paths[0]


def ingest_local_pgn(
    pgn_path: Path,
    project: ProjectPaths,
    filters: FilterConfig,
) -> IngestResult:
    return ingest_local_pgns([pgn_path], project, filters)


def ingest_local_pgns(
    pgn_paths: list[Path],
    project: ProjectPaths,
    filters: FilterConfig,
) -> IngestResult:
    if not pgn_paths:
        raise ValueError("At least one PGN path is required.")

    raw_outputs: list[Path] = []
    all_games = []
    for index, pgn_path in enumerate(pgn_paths, start=1):
        if not pgn_path.exists():
            raise FileNotFoundError(pgn_path)
        raw_text = pgn_path.read_text(encoding="utf-8", errors="replace")
        raw_output = _raw_output_path(project.raw_dir, pgn_path, index)
        raw_output.write_text(raw_text, encoding="utf-8")
        raw_outputs.append(raw_output)
        all_games.extend(parse_pgn(raw_text))

    kept, report = filter_games(
        all_games,
        filters.target_player,
        min_ply=filters.min_ply,
        standard_only=filters.standard_only,
        rated_only=filters.rated_only,
    )

    cleaned_path = project.cleaned_dir / "target-games.pgn"
    cleaned_path.write_text(games_to_pgn(kept), encoding="utf-8")

    report_path = project.cleaned_dir / "ingest-report.json"
    write_json(report_path, asdict(report))
    return IngestResult(
        raw_paths=raw_outputs,
        cleaned_path=cleaned_path,
        report_path=report_path,
        report=report,
    )


def _raw_output_path(raw_dir: Path, source: Path, index: int) -> Path:
    candidate = raw_dir / source.name
    if not candidate.exists():
        return candidate
    return raw_dir / f"{index:03d}-{source.name}"
