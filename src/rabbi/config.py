from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json


CONFIG_DIR = "config"
DATA_DIR = "data"
LOGS_DIR = "logs"


@dataclass(slots=True)
class FilterConfig:
    target_player: str
    min_ply: int = 10
    standard_only: bool = True
    rated_only: bool = False


@dataclass(slots=True)
class SourceSpec:
    kind: str
    value: str
    username: str | None = None


@dataclass(slots=True)
class ProjectConfig:
    name: str
    created_by: str = "rabbi"
    sources: list[SourceSpec] = field(default_factory=list)
    filters: FilterConfig | None = None


@dataclass(slots=True)
class ProjectPaths:
    root: Path

    @property
    def config_dir(self) -> Path:
        return self.root / CONFIG_DIR

    @property
    def data_dir(self) -> Path:
        return self.root / DATA_DIR

    @property
    def logs_dir(self) -> Path:
        return self.root / LOGS_DIR

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def cleaned_dir(self) -> Path:
        return self.data_dir / "cleaned"

    @property
    def training_dir(self) -> Path:
        return self.data_dir / "training"

    @property
    def project_config(self) -> Path:
        return self.config_dir / "project.json"

    @property
    def sources_config(self) -> Path:
        return self.config_dir / "sources.json"

    @property
    def training_config(self) -> Path:
        return self.config_dir / "training.json"


def ensure_workspace(root: Path) -> ProjectPaths:
    paths = ProjectPaths(root)
    for directory in [
        paths.root,
        paths.config_dir,
        paths.raw_dir,
        paths.cleaned_dir,
        paths.training_dir,
        paths.logs_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
    return paths


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_project(paths: ProjectPaths, config: ProjectConfig) -> None:
    data = asdict(config)
    write_json(paths.project_config, data)


def load_project(root: Path) -> ProjectConfig:
    paths = ProjectPaths(root)
    data = read_json(paths.project_config)
    sources = [SourceSpec(**source) for source in data.get("sources", [])]
    filters_data = data.get("filters")
    filters = FilterConfig(**filters_data) if filters_data else None
    return ProjectConfig(
        name=data["name"],
        created_by=data.get("created_by", "rabbi"),
        sources=sources,
        filters=filters,
    )


def init_project(name: str, workspace: Path) -> ProjectPaths:
    root = workspace / sanitize_name(name)
    paths = ensure_workspace(root)
    if not paths.project_config.exists():
        save_project(paths, ProjectConfig(name=name))
    return paths


def sanitize_name(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in name.strip())
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    if not cleaned:
        raise ValueError("Project name must contain at least one letter or number.")
    return cleaned

