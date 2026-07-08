from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys


@dataclass(slots=True)
class ToolCheck:
    name: str
    found: bool
    path: str | None = None
    required_for_mvp: bool = False
    detail: str | None = None


@dataclass(slots=True)
class DoctorResult:
    python_version: str
    tools: list[ToolCheck]

    @property
    def ok_for_mvp(self) -> bool:
        return all(tool.found for tool in self.tools if tool.required_for_mvp)


def run_doctor(
    *,
    extra_paths: list[Path] | None = None,
    maia_repo: Path | None = None,
    lc0_path: Path | None = None,
    base_model: Path | None = None,
    python_executable: Path | None = None,
) -> DoctorResult:
    names = [
        ("lc0", False),
        ("pgn-extract", False),
        ("trainingdata-tool", False),
        ("screen", False),
        ("python", True),
    ]
    tools: list[ToolCheck] = []
    for name, required in names:
        if name == "lc0" and lc0_path is not None:
            tools.append(
                ToolCheck(name=name, found=lc0_path.exists(), path=str(lc0_path), required_for_mvp=required)
            )
            continue
        path = shutil.which(name)
        tools.append(ToolCheck(name=name, found=path is not None, path=path, required_for_mvp=required))
    for path in extra_paths or []:
        tools.append(ToolCheck(name=str(path), found=path.exists(), path=str(path), required_for_mvp=False))
    if maia_repo is not None:
        tools.extend(_maia_repo_checks(maia_repo))
    if base_model is not None:
        tools.append(
            ToolCheck(
                name="base model",
                found=base_model.exists(),
                path=str(base_model),
                detail="Maia base model path",
            )
        )
    if python_executable is not None:
        tools.extend(_python_package_checks(python_executable))
    return DoctorResult(python_version=sys.version.split()[0], tools=tools)


def _maia_repo_checks(maia_repo: Path) -> list[ToolCheck]:
    convert_script = maia_repo / "1-data_generation" / "9-pgn_to_training_data.sh"
    train_script = maia_repo / "2-training" / "train_transfer.py"
    return [
        ToolCheck(name="maia repo", found=maia_repo.exists(), path=str(maia_repo)),
        ToolCheck(
            name="maia conversion script",
            found=convert_script.exists(),
            path=str(convert_script),
        ),
        ToolCheck(
            name="maia training script",
            found=train_script.exists(),
            path=str(train_script),
        ),
    ]


def _python_package_checks(python_executable: Path) -> list[ToolCheck]:
    checks = [
        ToolCheck(
            name="maia python",
            found=python_executable.exists(),
            path=str(python_executable),
            required_for_mvp=True,
            detail="Python used by Maia conversion/training scripts",
        )
    ]
    if not python_executable.exists():
        return checks

    conversion_modules = [
        ("chess", "python-chess"),
        ("yaml", "PyYAML"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("pytz", "pytz"),
    ]
    for import_name, package_name in conversion_modules:
        found, detail = _can_import(python_executable, import_name)
        if detail is None:
            detail = f"{package_name}; required for convert-data --run"
        else:
            detail = f"install {package_name}; required for convert-data --run ({detail})"
        checks.append(
            ToolCheck(
                name=f"python module {import_name}",
                found=found,
                path=str(python_executable),
                required_for_mvp=True,
                detail=detail,
            )
        )

    found, detail = _can_import(python_executable, "tensorflow", timeout=15)
    checks.append(
        ToolCheck(
            name="python module tensorflow",
            found=found,
            path=str(python_executable),
            required_for_mvp=False,
            detail="required for prepare-train --run" if found else f"required for prepare-train --run ({detail})",
        )
    )
    if found:
        gpu_count, gpu_detail = _tensorflow_gpu_count(python_executable)
        checks.append(
            ToolCheck(
                name="tensorflow gpu",
                found=gpu_count > 0,
                path=str(python_executable),
                required_for_mvp=False,
                detail=(
                    f"{gpu_count} GPU device(s) visible"
                    if gpu_count > 0
                    else f"no GPU visible; Maia training uses NCHW Conv2D and may not run on CPU ({gpu_detail})"
                ),
            )
        )
    return checks


def _can_import(python_executable: Path, import_name: str, *, timeout: int = 5) -> tuple[bool, str | None]:
    try:
        result = subprocess.run(
            [str(python_executable), "-c", f"import {import_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, None
    detail = (result.stderr or result.stdout).strip().splitlines()
    return False, detail[-1] if detail else f"import {import_name} failed"


def _tensorflow_gpu_count(python_executable: Path) -> tuple[int, str | None]:
    try:
        result = subprocess.run(
            [
                str(python_executable),
                "-c",
                "import tensorflow as tf; print(len(tf.config.list_physical_devices('GPU')))",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 0, str(exc)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return 0, detail[-1] if detail else "TensorFlow GPU check failed"
    lines = result.stdout.strip().splitlines()
    try:
        return int(lines[-1]), None
    except (IndexError, ValueError):
        return 0, result.stdout.strip() or "TensorFlow GPU check produced no count"
