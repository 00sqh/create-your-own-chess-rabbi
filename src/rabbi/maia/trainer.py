from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import os

from rabbi.config import ProjectPaths, sanitize_name, write_json
from rabbi.system.process import LoggedProcessResult, run_logged


@dataclass(slots=True)
class TrainerConfig:
    maia_repo: Path
    project_dir: Path
    player_name: str
    base_model: Path
    python: Path | None = None
    output_dir: Path | None = None
    dataset_root: Path | None = None
    dataset_name: str | None = None
    gpu: int | None = 0
    num_workers: int = 4
    batch_size: int = 256
    total_steps: int = 150_000
    precision: str = "single"
    shuffle_size: int = 250_000
    sampling: str = "uniform"
    num_batch_splits: int = 1
    test_steps: int = 2_000
    lr_values: list[float] = field(default_factory=lambda: [0.01, 0.001, 0.0001, 0.00001])
    lr_boundaries: list[int] = field(default_factory=lambda: [35_000, 80_000, 110_000])
    filters: int = 256
    residual_blocks: int = 6
    se_ratio: int = 8
    policy_loss_weight: float = 1.0
    value_loss_weight: float = 1.0
    moves_left_loss_weight: float = 0.0
    train_avg_report_steps: int = 100
    total_test_steps: int = 1_000
    checkpoint_steps: int = 1_000
    extra: dict[str, object] = field(default_factory=dict)

    @property
    def player_slug(self) -> str:
        return self.dataset_name or sanitize_name(self.player_name)

    @property
    def resolved_dataset_root(self) -> Path:
        if self.dataset_root is not None:
            return self.dataset_root
        return ProjectPaths(self.project_dir).training_dir

    @property
    def resolved_output_dir(self) -> Path:
        if self.output_dir is not None:
            return self.output_dir
        return self.project_dir / "models"

    @property
    def upstream_model_path(self) -> str:
        models_dir = (self.maia_repo / "models").resolve()
        try:
            return self.base_model.resolve().relative_to(models_dir).as_posix()
        except ValueError:
            return str(self.base_model)


class MaiaIndividualTrainer:
    """Adapter for the upstream Maia Individual transfer trainer."""

    def __init__(self, config: TrainerConfig) -> None:
        self.config = config

    @property
    def train_script(self) -> Path:
        return self.config.maia_repo / "2-training" / "train_transfer.py"

    def validate(self) -> None:
        if not self.config.maia_repo.exists():
            raise FileNotFoundError(f"Maia Individual repo not found: {self.config.maia_repo}")
        if not self.train_script.exists():
            raise FileNotFoundError(f"Maia Individual training script not found: {self.train_script}")
        if not self.config.base_model.exists():
            raise FileNotFoundError(f"Base Maia model path not found: {self.config.base_model}")
        dataset_dir = self.config.resolved_dataset_root / self.config.player_slug
        if not dataset_dir.exists():
            raise FileNotFoundError(f"Converted Maia dataset not found: {dataset_dir}")

    def write_config(self) -> Path:
        output = self.config.project_dir / "config" / "maia-individual.generated.json"
        write_json(output, self.to_config_dict())
        return output

    def write_yaml_config(self) -> Path:
        output = self.config.project_dir / "config" / "maia-individual.generated.yaml"
        data = self.to_config_dict()
        output.write_text(_to_simple_yaml(data), encoding="utf-8")
        return output

    def to_config_dict(self) -> dict[str, object]:
        data = asdict(self.config)
        for key in ["maia_repo", "project_dir", "base_model", "python", "output_dir", "dataset_root"]:
            value = data.get(key)
            data[key] = str(value) if value is not None else None
        data["dataset_name"] = self.config.player_slug
        data["resolved_dataset_root"] = str(self.config.resolved_dataset_root)
        data["resolved_output_dir"] = str(self.config.resolved_output_dir)
        return {
            "gpu": self.config.gpu,
            "dataset": {
                "path": str(self.config.resolved_dataset_root),
                "name": self.config.player_slug,
            },
            "precision": self.config.precision,
            "model": {
                "filters": self.config.filters,
                "residual_blocks": self.config.residual_blocks,
                "se_ratio": self.config.se_ratio,
                "path": self.config.upstream_model_path,
                "keep_weights": True,
                "back_prop_blocks": self.config.residual_blocks,
            },
            "training": {
                "precision": self.config.precision,
                "batch_size": self.config.batch_size,
                "total_steps": self.config.total_steps,
                "num_batch_splits": self.config.num_batch_splits,
                "test_steps": self.config.test_steps,
                "shuffle_size": self.config.shuffle_size,
                "sampling": self.config.sampling,
                "lr_values": self.config.lr_values,
                "lr_boundaries": self.config.lr_boundaries,
                "policy_loss_weight": self.config.policy_loss_weight,
                "value_loss_weight": self.config.value_loss_weight,
                "moves_left_loss_weight": self.config.moves_left_loss_weight,
                "train_avg_report_steps": self.config.train_avg_report_steps,
                "total_test_steps": self.config.total_test_steps,
                "checkpoint_steps": self.config.checkpoint_steps,
            },
            "output": {
                "path": str(self.config.resolved_output_dir),
            },
            "rabbi": data,
        }

    def build_command(self, config_path: Path | None = None) -> list[str]:
        cfg = config_path or (self.config.project_dir / "config" / "maia-individual.generated.yaml")
        cmd = [
            str(self.config.python.absolute()) if self.config.python is not None else "python",
            str(self.train_script.resolve()),
            str(cfg.resolve()),
            self.config.player_slug,
            "--num_workers",
            str(self.config.num_workers),
        ]
        if self.config.gpu is not None:
            cmd.extend(["--gpu", str(self.config.gpu)])
        cmd.extend(["--copy_dir", str(self.config.resolved_output_dir.resolve())])
        return cmd

    def run(
        self,
        *,
        dry_run: bool = False,
        log_path: Path | None = None,
    ) -> LoggedProcessResult | list[str]:
        self.validate()
        self.config.resolved_output_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.write_yaml_config()
        self.write_config()
        command = self.build_command(config_path)
        if dry_run:
            return command
        log = log_path or (ProjectPaths(self.config.project_dir).logs_dir / "train.log")
        return run_logged(command, cwd=self.config.maia_repo, log_path=log, env=_maia_env(self.config.maia_repo))


def _maia_env(maia_repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    repo = str(maia_repo.resolve())
    env["PYTHONPATH"] = repo if not existing else f"{repo}{os.pathsep}{existing}"
    env.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    env.setdefault("MPLCONFIGDIR", "/tmp/rabbi-matplotlib")
    return env


def _to_simple_yaml(value: object, indent: int = 0) -> str:
    spaces = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, dict):
                if item:
                    lines.append(f"{spaces}{key}:")
                    lines.append(_to_simple_yaml(item, indent + 2).rstrip())
                else:
                    lines.append(f"{spaces}{key}: {{}}")
            elif isinstance(item, list):
                if item:
                    lines.append(f"{spaces}{key}:")
                    for element in item:
                        lines.append(f"{spaces}  - {_format_yaml_scalar(element)}")
                else:
                    lines.append(f"{spaces}{key}: []")
            else:
                lines.append(f"{spaces}{key}: {_format_yaml_scalar(item)}")
        return "\n".join(lines) + "\n"
    raise TypeError("Top-level YAML value must be a dictionary.")


def _format_yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'
