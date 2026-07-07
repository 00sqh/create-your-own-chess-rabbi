from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from personal_maia.config import ProjectPaths, read_json
from personal_maia.maia.weights import find_latest_weights


@dataclass(slots=True)
class ProjectStatus:
    project: Path
    has_project_config: bool
    raw_pgn_count: int
    cleaned_pgn: Path | None
    cleaned_pgn_bytes: int
    ingest_report: dict[str, object] | None
    has_conversion_config: bool
    has_training_config: bool
    latest_weights: Path | None
    log_files: list[Path]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        for key in ["project", "cleaned_pgn", "latest_weights"]:
            value = data[key]
            data[key] = str(value) if value is not None else None
        data["log_files"] = [str(path) for path in self.log_files]
        return data


def collect_status(project_root: Path) -> ProjectStatus:
    paths = ProjectPaths(project_root)
    cleaned = paths.cleaned_dir / "target-games.pgn"
    report_path = paths.cleaned_dir / "ingest-report.json"
    ingest_report = read_json(report_path) if report_path.exists() else None
    try:
        latest_weights = find_latest_weights(paths.root / "models")
    except FileNotFoundError:
        latest_weights = None

    return ProjectStatus(
        project=paths.root,
        has_project_config=paths.project_config.exists(),
        raw_pgn_count=len(list(paths.raw_dir.glob("*.pgn"))) if paths.raw_dir.exists() else 0,
        cleaned_pgn=cleaned if cleaned.exists() else None,
        cleaned_pgn_bytes=cleaned.stat().st_size if cleaned.exists() else 0,
        ingest_report=ingest_report,
        has_conversion_config=(paths.config_dir / "maia-conversion.json").exists(),
        has_training_config=paths.training_config.exists()
        or (paths.config_dir / "maia-individual.generated.yaml").exists(),
        latest_weights=latest_weights,
        log_files=sorted(paths.logs_dir.glob("*.log")) if paths.logs_dir.exists() else [],
    )

